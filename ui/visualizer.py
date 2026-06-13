"""
================================================================================
ARCHIVO: ui/visualizer.py — v6 "Zero-Backpressure" (render pull model)
================================================================================

🎨 PALETA CROMÁTICA (intacta desde v4)
  Fondos (oscuros, reactivos):
    #0a0a0f  Negro abismal   → Silencio / pausa
    #0d1f3c  Azul medianoche → Bass dominante
    #1a0a2e  Púrpura abismal → Medios / melodía
    #2a0a1a  Carmín oscuro   → Agudos / drop

  Barras (brillantes, saturadas):
    #00d4ff  Cian eléctrico  → Zona grave (base)
    #7b2fff  Violeta neón    → Zona media
    #ff2d78  Rosa eléctrico  → Zona alta (cima)
    #ffb700  Ámbar dorado    → Pico flotante

⚡ CAMBIOS ARQUITECTÓNICOS v5 → v6  «Zero-Backpressure»
---------------------------------------------------------

PROBLEMA RAÍZ RESUELTO:
  set_interval(1/60) agenda tasks de forma ciega en la cola de Textual.
  Si el fotograma anterior aún no ha terminado de dibujarse cuando el
  intervalo dispara, los mensajes se acumulan ("backpressure"), el event
  loop se atasca y los FPS colapsan con tirones de acordeón.

  Adicionalmente, llamar a Static.update() 60 veces/segundo sustituye
  todo el renderable interno, invalidando el widget en cada frame y
  forzando un ciclo completo de recomposición de Rich.

1. MODELO PULL: render() + _schedule_next_frame()
   El widget sobreescribe render() — el método nativo que Textual invoca
   CUANDO EL COMPOSITOR LO NECESITA. render() construye y devuelve el
   Text de las barras directamente, sin pasar por update().

   _schedule_next_frame() usa set_timer(INTERVAL, ...) de forma RECURSIVA:
   el siguiente frame SOLO se agenda cuando el actual ya terminó de
   procesarse. Esto garantiza exactamente 1 frame pendiente en la cola
   en todo momento — backpressure = 0.

2. SEPARACIÓN DE ESTADO Y RENDERIZADO
   El método _tick() acumula estado (datos espectrales, color de fondo).
   El método render() lo consume sin efectos secundarios.
   Esta separación permite que Textual llame a render() en cualquier
   momento (e.g., resize) sin romper la sincronización.

3. THROTTLE DEL FONDO PRESERVADO
   La actualización de screen.styles.background se limita a 15 FPS
   (cada 4 ticks) y solo si el color RGB cambió, evitando las
   invalidaciones globales de layout que fueron el cuello de botella anterior.

4. REFRESH CON REPAINT=True, LAYOUT=False
   self.refresh(repaint=True, layout=False) redibuja SOLO los píxeles
   del widget sin recalcular el árbol de layout del DOM — la operación
   más barata posible en Textual para contenido animado.

5. SUB-PIXEL VERTICAL PRESERVADO (bloques Unicode de octavo ▁▂▃▄▅▆▇█)
   El mapeo fraccionario de v5 se conserva intacto.

================================================================================
"""

from textual.widgets import Static
from textual.color import Color
from rich.console import RenderableType
from rich.text import Text
from core.logger import get_logger

logger = get_logger("Visualizer")

# ── INTERVALO DE FRAME (segundos) ─────────────────────────────────────────────
# 60 FPS → 16.6 ms. El set_timer recursivo garantiza que este intervalo sea
# el tiempo MÍNIMO entre frames, no un disparo ciego de cola.
_FRAME_INTERVAL = 1.0 / 60.0

# ── BLOQUES UNICODE DE OCTAVO (sub-pixel vertical) ───────────────────────────
# Índice 0 = vacío (espacio), 1..8 = ▁▂▃▄▅▆▇█
_EIGHTH_BLOCKS = (' ', '▁', '▂', '▃', '▄', '▅', '▆', '▇', '█')

# ── PALETA — FONDOS (RGB floats, oscuros) ────────────────────────────────────
_BG_SILENCE = (10.0,  10.0,  15.0)
_BG_BASS    = (13.0,  31.0,  60.0)
_BG_MIDS    = (26.0,  10.0,  46.0)
_BG_HIGHS   = (42.0,  10.0,  26.0)
_BG_PEAK    = (60.0,  30.0,   8.0)

# ── PALETA — BARRAS (estilos Rich preconstruidos, sin f-strings en hot-loop) ─
_STYLE_BOTTOM = 'bold #00d4ff'   # Cian eléctrico  → zona grave
_STYLE_MID    = 'bold #7b2fff'   # Violeta neón    → zona media
_STYLE_TOP    = 'bold #ff2d78'   # Rosa eléctrico  → zona alta
_STYLE_EMPTY  = ''               # Sin estilo      → celda vacía


# ── HELPERS DE COLOR ─────────────────────────────────────────────────────────

def _clamp255(v: float) -> float:
    return 0.0 if v < 0.0 else (255.0 if v > 255.0 else v)


def _add_weighted(
    base: tuple[float, float, float],
    color: tuple[float, float, float],
    weight: float,
) -> tuple[float, float, float]:
    return (
        _clamp255(base[0] + color[0] * weight),
        _clamp255(base[1] + color[1] * weight),
        _clamp255(base[2] + color[2] * weight),
    )


# ── WIDGET PRINCIPAL ─────────────────────────────────────────────────────────

class CavaVisualizer(Static):
    """
    Ecualizador espectral — motor v6 «Zero-Backpressure».

    Arquitectura de renderizado pull (render override):
      • render() devuelve el Text con bloques sub-pixel directamente al
        compositor de Textual — sin update(), sin recomposición del widget.
      • _schedule_next_frame() agenda frames de forma recursiva, garantizando
        que solo haya 1 frame en la cola en todo momento.
      • Fondo reactivo con throttle a 15 FPS para evitar invalidaciones
        globales de layout del DOM.
    """

    DEFAULT_CSS = """
    CavaVisualizer {
        width: 100%;
        height: 1fr;
        color: auto;
        background: transparent;
        padding: 0;
        margin: 0;
    }
    """

    # ── INICIALIZACIÓN ────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        """
        Inicializa el estado persistente y arranca el primer frame.
        """
        w, h = self.size.width, self.size.height

        # Fondo reactivo: EMA en espacio RGB float
        self.current_bg: list[float] = list(_BG_SILENCE)
        self._last_bg_color: tuple | None = None

        # Tabla de estilos de barra por fila — precalculada, reconstruida solo en resize
        self._row_styles: list[str] = self._build_row_styles(max(h, 1))
        self._cached_h: int = h
        self._cached_w: int = w

        # Renderable interno: empieza en silencio (Text vacío)
        self._renderable: Text = Text()

        # Cortocircuito de silencio: evita el hot-loop W×H cuando no hay música
        self._silent: bool = False

        # Datos de telemetría
        self.frame_count: int = 0

        # Arrancar el bucle recursivo de frames
        self._schedule_next_frame()

    @staticmethod
    def _build_row_styles(h: int) -> list[str]:
        """
        Precalcula el estilo de barra para cada fila.

        Gradiente top→bottom:
          [0.00 – 0.33]  Rosa eléctrico  → cima energética
          [0.33 – 0.66]  Violeta neón    → cuerpo
          [0.66 – 1.00]  Cian eléctrico  → base grave
        """
        styles = []
        h1 = max(h - 1, 1)
        for y in range(h):
            ratio = y / h1
            if ratio < 0.33:
                styles.append(_STYLE_TOP)
            elif ratio < 0.66:
                styles.append(_STYLE_MID)
            else:
                styles.append(_STYLE_BOTTOM)
        return styles

    # ── MOTOR DE FRAMES RECURSIVO ─────────────────────────────────────────────

    def _schedule_next_frame(self) -> None:
        """
        Agenda el siguiente tick usando set_timer.

        GARANTÍA DE BACKPRESSURE CERO:
        set_timer se llama al FINAL de _tick(), es decir, solo DESPUÉS de
        que el procesamiento actual terminó. Esto significa que el event loop
        de Textual jamás acumula más de 1 mensaje pendiente de este widget.
        No hay efecto acordeón, no hay tirones de cola.
        """
        self.set_timer(_FRAME_INTERVAL, self._tick)

    def _tick(self) -> None:
        """
        Ciclo de trabajo de un frame:
          1. Detecta silencio → cortocircuito.
          2. Recoge datos espectrales del bridge.
          3. Actualiza geometría sub-pixel (top_row, frac_eighth).
          4. Construye el Text con run-length batching.
          5. Lo almacena en self._renderable.
          6. Actualiza el fondo reactivo (throttled a 15 FPS).
          7. Dispara self.refresh(repaint=True, layout=False).
          8. Agenda el siguiente frame vía _schedule_next_frame().
        """
        # ── 1. CORTOCIRCUITO DE SILENCIO ─────────────────────────────────────
        playing = self.app.bridge.is_playing()
        if not playing and self._silent:
            self._schedule_next_frame()
            return
        if playing:
            self._silent = False

        # ── 2. DIMENSIONES ───────────────────────────────────────────────────
        w, h = self.size.width, self.size.height
        if w <= 0 or h <= 0:
            self._schedule_next_frame()
            return

        if h != self._cached_h:
            self._row_styles = self._build_row_styles(h)
            self._cached_h = h
        if w != self._cached_w:
            self._cached_w = w

        # ── 3. DATOS ESPECTRALES PUROS ───────────────────────────────────────
        # CAVA ya entrega el espectro con Monstercat + Gravity + autoganancia.
        bars: list[float] = self.app.bridge.get_audio_bars(w)

        # ── 4. PRE-CÁLCULO GEOMÉTRICO SUB-PIXEL ─────────────────────────────
        frac_eighth: list[int] = [0] * w
        top_row:     list[int] = [0] * w

        for x in range(w):
            val = bars[x]
            if val < 0.0:
                val = 0.0
            elif val > 1.0:
                val = 1.0

            bar_height_f = val * h
            full = int(bar_height_f)
            frac = bar_height_f - full

            eighth = int(frac * 8.0 + 0.5)
            if eighth >= 8:
                full += 1
                eighth = 0
            if full > h:
                full = h
                eighth = 0

            frac_eighth[x] = eighth
            top_row[x] = (h - full - 1) if eighth > 0 else (h - full)

        # ── 5. FONDO REACTIVO (cálculo EMA, throttle 15 FPS) ─────────────────
        bass_end = max(1, int(w * 0.30))
        mid_end  = max(bass_end + 1, int(w * 0.65))

        bass_zone = bars[:bass_end]
        mid_zone  = bars[bass_end:mid_end]
        high_zone = bars[mid_end:]

        bass_avg = sum(bass_zone) / len(bass_zone) if bass_zone else 0.0
        mid_avg  = sum(mid_zone)  / len(mid_zone)  if mid_zone  else 0.0
        high_avg = sum(high_zone) / len(high_zone) if high_zone else 0.0
        total_energy = bass_avg + mid_avg + high_avg
        peak_global  = max(bars) if bars else 0.0

        target = _BG_SILENCE
        target = _add_weighted(target, _BG_BASS,  bass_avg * 0.60)
        target = _add_weighted(target, _BG_MIDS,  mid_avg  * 0.55)
        target = _add_weighted(target, _BG_HIGHS, high_avg * 0.45)
        peak_excess = max(0.0, peak_global - 0.85) / 0.15
        if peak_excess > 0.0:
            target = _add_weighted(target, _BG_PEAK, peak_excess * 0.35)

        alpha = 0.04 + min(0.18, total_energy * 0.2)
        bg = self.current_bg
        bg[0] += alpha * (target[0] - bg[0])
        bg[1] += alpha * (target[1] - bg[1])
        bg[2] += alpha * (target[2] - bg[2])

        r    = int(_clamp255(bg[0]))
        g    = int(_clamp255(bg[1]))
        b_ch = int(_clamp255(bg[2]))

        # Throttle: screen.styles.background solo a 15 FPS y si el color cambió
        if self.frame_count % 4 == 0:
            new_bg = (r, g, b_ch)
            if self._last_bg_color != new_bg:
                self._last_bg_color = new_bg
                try:
                    self.app.screen.styles.background = Color(r, g, b_ch)
                except Exception:
                    pass

        # ── 6. BUILD TEXT CON RUN-LENGTH BATCHING ────────────────────────────
        row_styles    = self._row_styles
        _style_empty  = _STYLE_EMPTY
        eighth_blocks = _EIGHTH_BLOCKS

        lines: list[Text] = []

        for y in range(h):
            bar_style = row_styles[y]
            line_text = Text()
            buf_chars: list[str] = []
            buf_style = _style_empty

            for x in range(w):
                tr = top_row[x]

                if y < tr:
                    ch  = ' '
                    sty = _style_empty
                elif y == tr and frac_eighth[x] > 0:
                    ch  = eighth_blocks[frac_eighth[x]]
                    sty = bar_style
                else:
                    ch  = '█'
                    sty = bar_style

                if sty is buf_style:
                    buf_chars.append(ch)
                else:
                    if buf_chars:
                        line_text.append(''.join(buf_chars), style=buf_style)
                    buf_chars = [ch]
                    buf_style = sty

            if buf_chars:
                line_text.append(''.join(buf_chars), style=buf_style)

            lines.append(line_text)

        # ── 7. ALMACENAR RENDERABLE ───────────────────────────────────────────
        self._renderable = Text('\n').join(lines)

        # ── 8. DISPARAR REPAINT (sin recalcular layout) ───────────────────────
        # layout=False es crítico: redibuja solo los píxeles del widget sin
        # tocar el árbol de layout del DOM — la operación más ligera posible.
        self.refresh(repaint=True, layout=False)

        # ── CORTOCIRCUITO DE SILENCIO: armar para el próximo tick ────────────
        if not playing and peak_global < 0.002:
            self._silent = True

        # ── TELEMETRÍA (cada 180 frames ≈ 3 s) ───────────────────────────────
        self.frame_count += 1
        if self.frame_count % 180 == 0:
            logger.info(
                f"Bass={bass_avg:.2f} Mid={mid_avg:.2f} High={high_avg:.2f} "
                f"α={alpha:.3f} BG=#{r:02x}{g:02x}{b_ch:02x} Peak={peak_global:.2f}"
            )

        # ── 9. AGENDAR EL PRÓXIMO FRAME (SIEMPRE AL FINAL) ───────────────────
        # Al colocar esta llamada aquí, garantizamos que el intervalo de
        # _FRAME_INTERVAL se mide desde el fin del frame actual, no desde
        # el inicio, eliminando completamente la acumulación de backpressure.
        self._schedule_next_frame()

    # ── MÉTODO PULL — INTERFAZ NATIVA DE TEXTUAL ─────────────────────────────

    def render(self) -> RenderableType:
        """
        Textual llama a este método cada vez que necesita redibujar el widget.

        Devuelve el renderable pre-construido por _tick() sin ningún efecto
        secundario. La separación estado/_tick()/render() garantiza que Textual
        puede invocar render() en cualquier momento (resize, focus, etc.) de
        forma segura y sin coste de reconstrucción.
        """
        return self._renderable