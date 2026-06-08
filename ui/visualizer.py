"""
================================================================================
ARCHIVO: ui/visualizer.py
================================================================================
ROL DEL MÓDULO
--------------
Este widget es el motor visual del reproductor. Ocupa toda la columna derecha
de la interfaz y traduce los valores espectrales (floats 0-1) producidos por el
generador psicoacústico nativo del backend en una representación gráfica de
barras en la terminal usando caracteres Unicode de bloque.

PALETA DE COLORES – "Gradiente Discoteca"
------------------------------------------
  • Magenta  (#FF00FF) – zona superior de cada barra (frecuencias altas).
  • Morado   (#8A2BE2) – zona media (transición armónica).
  • Cian     (#00FFFF) – zona inferior (frecuencias graves, sub-bass).

Esta distribución crea la ilusión de un gradiente de calor invertido: los picos
energéticos vibran en magenta y la base grave en cian frío.

TASA DE REFRESCO
----------------
Temporizador configurado a 0.03 s → ~33 FPS reales.
Se eligió este valor como equilibrio óptimo entre fluidez visual y coste de CPU
en la terminal (Textual redirige todo el renderizado a través de Rich).

DISEÑO ESTÉTICO – FOCO RÍTMICO
-----------------------------------------------
La interpolación visual asegura colores nítidos usando caracteres en 3D
y adaptando el escalado horizontal dinámicamente mediante la capa
matemática inferior.

FÍSICA "ANTIGRAVITY PEAKS" (Picos Flotantes)
---------------------------------------------
Cada barra mantiene un pico de altura máxima (self.peaks[x]) con las siguientes
reglas de mecánica:

  1. SUBIDA INSTANTÁNEA: si el valor actual supera el pico, el pico sube de
     forma inmediata (sin interpolación) para capturar el ataque del transitorio.

  2. RETARDO DE CAÍDA (antigravedad): cuando la barra baja, el pico permanece
     suspendido durante PEAK_HOLD_FRAMES frames sin moverse. Esto imita la
     inercia aparente que exhiben los LEDs de pico en los VU-meters analógicos.

  3. ACELERACIÓN GRAVITATORIA: tras el retardo, el pico cae aplicando una
     aceleración creciente (v = v + a), simulando caída libre con roce mínimo.

  4. RENDERIZADO: el pico flotante se dibuja con el carácter "▔" en color
     blanco brillante (#FFFFFF bold) para máximo contraste contra el fondo.

EFECTO DE ILUMINACIÓN AMBIENTAL DINÁMICA (Ambient Glow)
---------------------------------------------------------
El color de fondo del widget cambia reactivamente según la energía del bajo:
  - Impacto de bass → fondo morado profundo (#0f001a) o cian abisal (#001212).
  - Sin impacto → decaimiento exponencial frame a frame hacia negro (#000000).
Esto simula un pulso de luz ambiental orgánico acoplado al ritmo.

OPTIMIZACIÓN O(1) POR FRAME
-----------------------------
Al inicio de cada frame se construye un diccionario particle_map indexado por
coordenadas de terminal (x, y). La consulta durante el renderizado fila×columna
es O(1) en lugar del O(n×m) del bucle anidado original.
================================================================================
"""

import math
import random
from textual.widgets import Static
from textual.color import Color
from rich.text import Text
from core.logger import get_logger

logger = get_logger("Visualizer")


# ── CONSTANTES GLOBALES DEL VISUALIZADOR ────────────────────────────────────

# Caracteres de bloque Unicode para representar fracciones de altura de barra.
# Índice 0 = vacío, índice 7 = bloque completo.
BAR_CHARS = [' ', '▂', '▃', '▄', '▅', '▆', '▇', '█']

# ── CONSTANTES DE ATAQUE Y DECAIMIENTO ───────────────────────────────────────
# Factor de decaimiento exponencial para la caída de barras.
# Cuando la barra actual es MENOR que la anterior, el valor exhibido se
# calcula como: val = max(nuevo, viejo × DECAY). Esto crea una caída suave
# y orgánica en lugar de un descenso abrupto frame-a-frame.
#
# 0.82 fue elegido empíricamente: lo suficientemente bajo para que las barras
# respondan rápido a los silencios (~6 frames para caer 50%), pero lo
# suficientemente alto para que el movimiento se sienta fluido y no nervioso.
DECAY = 0.82

# Amplitud mínima de la señal para activar el autoganancia.
# Si el pico global está por debajo de este umbral, se amplifica todo.
AUTO_GAIN_CEILING = 0.20

# ── CONSTANTES DE ILUMINACIÓN AMBIENTAL ──────────────────────────────────────
# Umbral bass para activar color ambiental del ADN.
AMBIENT_BASS_THRESHOLD = 0.45

# ── CONSTANTES DE FÍSICA "ANTIGRAVITY PEAKS" ─────────────────────────────────

# Frames que el pico permanece suspendido antes de comenzar a caer.
PEAK_HOLD_FRAMES = 18

# Aceleración gravitatoria aplicada al pico por frame (en unidades de altura
# normalizada). Se acumula progresivamente para simular caída libre: v = v + a.
# Aumentado para un rebote más reactivo.
PEAK_GRAVITY = 0.0035

# Velocidad inicial de caída cuando el retardo termina.
PEAK_FALL_START = 0.001

# Factor de suavizado del lerp cromático del fondo (15 % de la diferencia/frame).
AMBIENT_LERP = 0.15

# Colores incandescentes de fase de impacto (alta velocidad + bass > 0.85).
IMPACT_COLORS = ("#FFFFFF", "#00FFFF", "#FF00FF")

# Colores neón fríos de fase de flotación (estela camaleónica).
FLOAT_COLORS = ("#8A2BE2", "#00FFFF", "#FF00FF")


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convierte '#RRGGBB' a tupla RGB float para interpolación."""
    h = hex_color.lstrip("#")
    return (float(int(h[0:2], 16)), float(int(h[2:4], 16)), float(int(h[4:6], 16)))


def _rgb_to_hex(r: float, g: float, b: float) -> str:
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _lerp_rgb(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    t: float,
) -> tuple[float, float, float]:
    """
    Interpolación lineal de color (lerp):
        C(t) = A + t × (B − A),  t ∈ [0, 1]
    """
    t = max(0.0, min(1.0, t))
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )

class CavaVisualizer(Static):
    """
    Widget de ecualizador espectral a pantalla completa.

    Renderiza barras de frecuencia psicoacústicas con gradiente de color,
    partículas rítmicas focalizadas en la Zona Bass, picos flotantes con
    física de antigravedad, e iluminación ambiental dinámica acoplada
    al ritmo de los graves.
    """

    DEFAULT_CSS = """
    CavaVisualizer {
        width: 100%;
        height: 1fr;
        color: auto;
        background: transparent;
    }
    """

    # ── INICIALIZACIÓN DEL WIDGET ────────────────────────────────────────────

    def on_mount(self) -> None:
        """
        on_mount: llamado por Textual una vez que el widget está en pantalla.

        Inicializamos aquí (y no en __init__) porque el tamaño del widget
        (self.size) no está disponible hasta que el widget se monta en el DOM.

        Estado persistente entre frames:
        - self.previous_bars:  valores de barra del frame anterior (para decay).
        - self.peaks:          altura máxima alcanzada por cada barra.
        - self.peak_hold:      contador de frames de retardo por barra.
        - self.peak_vel:       velocidad de caída acumulada por barra.
        - self.current_bg_color: RGB flotante para lerp del fondo global.
        - self.frame_count:    contador de frames para telemetría periódica.
        """
        # Valores de barra suavizados del frame anterior (decaimiento).
        self.previous_bars: list[float] = []

        # Picos flotantes: un float por columna de barra.
        self.peaks: list[float] = []

        # Contadores de retardo antes de que el pico comience a caer.
        self.peak_hold: list[int] = []

        # Velocidad de caída actual del pico (se acumula con gravedad).
        self.peak_vel: list[float] = []

        # RGB actual del fondo (lerp hacia objetivo o púrpura base).
        self.current_bg_color: tuple[float, float, float] = (8.0, 0.0, 13.0) # Base #08000d
        self.frame_count = 0

        self.set_interval(0.03, self.update_visualizer)

    # ── BUCLE PRINCIPAL DE ACTUALIZACIÓN (llamado ~33 veces/segundo) ─────────

    def update_visualizer(self) -> None:
        """
        Punto de entrada del bucle de renderizado.

        Orden de operaciones por frame:
          1.  Obtener dimensiones del viewport.
          2.  Pedir barras espectrales al bridge.
          3.  Aplicar autoganancia global.
          4.  Aplicar ataque instantáneo y decaimiento exponencial.
          5.  Calcular energía de Zona Bass (para partículas y ambient).
          6.  Actualizar iluminación ambiental dinámica.
          7.  Inicializar/redimensionar arrays de picos si cambia el ancho.
          8.  Actualizar física de picos (Antigravity Peaks).
          9.  Renderizar cada celda de la terminal.
         10.  Enviar el Text compuesto a Textual.
        """

        # ── 1. DIMENSIONES ───────────────────────────────────────────────────
        w, h = self.size.width, self.size.height
        if w <= 0 or h <= 0:
            return

        # ── 2. DATOS ESPECTRALES ─────────────────────────────────────────────
        # Consultamos al bridge el espectro con num_bars = anchura de pantalla.
        # El bridge retorna ceros si está pausado → el display se vacía solo.
        bridge = self.app.bridge
        bars: list[float] = list(bridge.get_audio_bars(w))

        # ── 3. AUTOGANANCIA GLOBAL ────────────────────────────────────────────
        # Si la señal global es muy débil, la amplificamos para aprovechar
        # toda la altura del visualizador. Esto mantiene la animación activa
        # incluso en pasajes musicales suaves.
        peak_global = max(bars) if bars else 0.0
        if 0.0 < peak_global < AUTO_GAIN_CEILING:
            gain = 1.0 / peak_global
            bars = [min(1.0, b * gain) for b in bars]

        # ── 4. ATAQUE INSTANTÁNEO Y DECAIMIENTO EXPONENCIAL ──────────────────
        # Modelo de dinámica de barras inspirado en envolventes ADSR de
        # sintetizadores analógicos:
        #
        #   ATAQUE (Attack): si el nuevo valor > anterior → subida INSTANTÁNEA.
        #     No hay interpolación ni suavizado al subir. Esto captura los
        #     transitorios de kick/snare con fidelidad máxima, tal como el
        #     oído humano percibe los ataques de percusión (<10ms).
        #
        #   CAÍDA (Decay/Release): si el nuevo valor < anterior → decaimiento
        #     exponencial. El valor exhibido se calcula como:
        #       val_display = max(val_nuevo, val_anterior × DECAY)
        #
        #     La función max() garantiza que si la señal vuelve a subir
        #     antes de que el decay termine, el ataque se impone de inmediato.
        #
        #   Resultado perceptual: las barras "saltan" con los beats y
        #   "caen" suavemente, emulando la respuesta de un VU-meter
        #   analógico con aguja balística.
        if len(self.previous_bars) != w:
            self.previous_bars = [0.0] * w

        smoothed: list[float] = []
        for i, raw in enumerate(bars):
            prev = self.previous_bars[i]
            # Ataque instantáneo (raw > prev) o decay exponencial (prev × DECAY).
            smoothed.append(raw if raw > prev else max(raw, prev * DECAY))
        self.previous_bars = smoothed
        bars = smoothed

        # ── 5. ENERGÍA BASS (primer 30 % del espectro) ───────────────────────
        bass_end = max(1, int(w * 0.30))
        bass_zone = bars[:bass_end]
        bass_avg = sum(bass_zone) / len(bass_zone) if bass_zone else 0.0

        # ── 6. FONDO AMBIENTAL GLOBAL (EMA) ──────────────────────────────────
        if bass_avg > AMBIENT_BASS_THRESHOLD:
            # Color azulado/cálido reactivo al bajo (ej #140022 o ADN derivado si lo deseas)
            target_r, target_g, target_b = _hex_to_rgb("#140022")
            target_bg = "#140022"
        else:
            # Púrpura abisal oscuro
            target_r, target_g, target_b = _hex_to_rgb("#08000d")
            target_bg = "#08000d"

        curr_r, curr_g, curr_b = self.current_bg_color
        # Suavizado Exponencial/EMA con alpha = 0.15
        curr_r = curr_r * 0.85 + target_r * 0.15
        curr_g = curr_g * 0.85 + target_g * 0.15
        curr_b = curr_b * 0.85 + target_b * 0.15
        
        self.current_bg_color = (curr_r, curr_g, curr_b)
        
        # Aplicamos el ambient glow al FONDO GLOBAL de la pantalla
        try:
            self.app.screen.styles.background = Color(int(curr_r), int(curr_g), int(curr_b))
        except Exception:
            pass

        # ── 7. REDIMENSIONAR ARRAYS DE PICOS ─────────────────────────────────
        # Si el ancho cambia (resize de terminal), reiniciamos los picos.
        if len(self.peaks) != w:
            self.peaks     = [0.0] * w
            self.peak_hold = [0]   * w
            self.peak_vel  = [0.0] * w

        # ── 8. FÍSICA "ANTIGRAVITY PEAKS" ─────────────────────────────────────
        # Procesamos cada barra para actualizar la posición de su pico flotante.
        #
        # El pico simula la mecánica de un LED de pico en un VU-meter analógico:
        #   - Sube instantáneamente al nuevo máximo (captura del transitorio).
        #   - Permanece suspendido PEAK_HOLD_FRAMES frames (antigravedad).
        #   - Cae con aceleración gravitatoria: v = v + PEAK_GRAVITY (caída libre).
        #
        # La ecuación v = v + a es la integración de Euler de primer orden
        # de la aceleración constante de la gravedad, donde cada frame es
        # un paso de tiempo dt=1. Esto produce caída cuadrática (s = ½at²).
        for x in range(w):
            bar_val = bars[x]

            if bar_val >= self.peaks[x]:
                # SUBIDA INSTANTÁNEA: la barra supera el pico → el pico sube.
                # Reiniciamos el contador de hold y la velocidad de caída.
                self.peaks[x]     = bar_val
                self.peak_hold[x] = PEAK_HOLD_FRAMES
                self.peak_vel[x]  = PEAK_FALL_START

            else:
                # La barra está por debajo del pico: aplicamos antigravedad.
                if self.peak_hold[x] > 0:
                    # RETARDO (antigravedad): el pico flota sin moverse.
                    self.peak_hold[x] -= 1
                else:
                    # CAÍDA CON ACELERACIÓN GRAVITATORIA: v = v + a.
                    # La velocidad crece cada frame → caída libre realista.
                    self.peak_vel[x]  += PEAK_GRAVITY
                    self.peaks[x]      = max(0.0, self.peaks[x] - self.peak_vel[x])

        self.frame_count += 1
        if self.frame_count % 30 == 0:
            logger.info(
                f"Bass Avg: {bass_avg:.2f} | "
                f"Fondo Objetivo: {target_bg} | Pico: {max(bars):.2f}"
            )

        # ── 9. RENDERIZADO CELDA A CELDA ───────────────────────────────────────
        # Recorremos la matriz de la terminal fila por fila (y) y columna por
        # columna (x). Para cada celda decidimos qué carácter y color mostrar.
        lines: list[Text] = []

        for y in range(h):
            # GRADIENTE DE COLOR por fila:
            # La ratio y/h indica la posición vertical relativa de la fila.
            #   [0.00 – 0.35] → Magenta (zona superior, frecuencias altas).
            #   [0.35 – 0.70] → Morado  (zona media, armónicos intermedios).
            #   [0.70 – 1.00] → Cian    (zona inferior, graves y sub-bass).
            ratio = y / max(h, 1)
            if ratio < 0.35:
                bar_color = '#FF00FF'   # Magenta
            elif ratio < 0.70:
                bar_color = '#8A2BE2'   # Morado (BlueViolet)
            else:
                bar_color = '#00FFFF'   # Cian

            line_text = Text()

            for x in range(w):
                val     = bars[x]
                # bar_top: fila a partir de la cual la barra está "llena".
                # (h-1) - (val * h) convierte [0,1] a coordenadas de terminal
                # donde 0 es arriba y h-1 es abajo.
                bar_top = h - 1 - int(val * h)

                # CÁLCULO DEL CARÁCTER DE BARRA 3D BEVELED
                char_to_draw = ' '
                if y >= bar_top:
                    dist_from_floor = h - 1 - y
                    bar_span        = max(1, h - bar_top)
                    rel = dist_from_floor / bar_span
                    
                    if y == bar_top:
                        # Borde superior de la barra: Textura de relieve/sombreado
                        char_to_draw = '▓'
                    else:
                        # Cuerpo interno sólido
                        char_to_draw = '█'

                # RENDERIZADO DE PICO FLOTANTE (Antigravity Peak)
                # Calculamos la fila de pantalla donde debe dibujarse el pico.
                # Color: blanco brillante (#FFFFFF bold) para máximo contraste
                # contra el fondo oscuro/negro y las barras coloreadas.
                peak_val = self.peaks[x]
                if peak_val > 0.01:
                    peak_row = h - 1 - int(peak_val * h)
                    peak_draw_row = max(0, peak_row - 1)
                else:
                    peak_draw_row = -1   # Sin pico activo

                # PRIORIDAD DE RENDERIZADO:
                #   1. Pico flotante     (indicador de máximo histórico).
                #   2. Barra espectral   (contenido principal).
                #   3. Espacio vacío.
                if y == peak_draw_row and peak_val > 0.01:
                    # Pico flotante: carácter "▔" en BLANCO BRILLANTE.
                    # Se usa bold + #FFFFFF para máximo contraste visual
                    # contra cualquier fondo.
                    line_text.append('▔', style='bold #FFFFFF')

                elif char_to_draw != ' ':
                    # Barra espectral con gradiente de color por fila.
                    line_text.append(char_to_draw, style=f'bold {bar_color}')

                else:
                    # Celda vacía.
                    line_text.append(' ')

            lines.append(line_text)

        # ── 10. ENVIAR A TEXTUAL ──────────────────────────────────────────────
        # Unimos las líneas con saltos de línea y actualizamos el widget.
        # Textual solo redibuja los caracteres que cambiaron (diff interno),
        # por lo que el coste real de render es proporcional al área activa.
        self.update(Text('\n').join(lines))
