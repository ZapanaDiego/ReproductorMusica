# README.md

## 1. 🎵 DESCRIPCIÓN GENERAL Y FLUJO DE EJECUCIÓN

Este proyecto es un **reproductor de música optimizado para terminal** construido sobre **Textual** y **Rich**, con una arquitectura preparada para separar estrictamente la interfaz de usuario del núcleo lógico de reproducción. La aplicación combina una TUI reactiva, tablas navegables, barra de progreso, panel de metadatos y un visualizador espectral estilo ecualizador, manteniendo la lógica crítica concentrada en `core/backend.py`.

El diseño actual busca dos objetivos principales:

1. **Reducir consumo de CPU** durante reproducción, pausa, renderizado visual y actualización de tablas.
2. **Preparar una migración futura del backend Python hacia C++**, manteniendo estable la capa de frontend Python mediante `core/bridge.py`.

La interfaz gráfica corre en Python, pero la lógica real de estado, cola, reproducción, saltos, progreso, calificación y análisis espectral debe permanecer centralizada detrás del bridge. Esto permite que, en una fase posterior, `backend.py` sea reemplazado por un módulo nativo compilado sin reescribir la UI.

### Ejecuciòn del programa
Primero tienes que asegurate que tienes descargado python la verciòn màs reciente y ejecutar en la terminal esto:

```bash
chmod +x main.py                                          
./main.py
```

### Ciclo de vida de ejecución

El ciclo completo empieza cuando se ejecuta:

```bash
python main.py
```

El archivo `main.py` instancia `MusicPlayerApp`, una aplicación de Textual. Durante la inicialización se crean dos objetos principales:

```python
self.bridge = MusicBridge()
self.input_manager = InputController(self.bridge, self)
```

`MusicBridge` inicializa internamente el backend actual:

```python
self.backend = MockBackend()
```

A partir de ese punto, la aplicación queda organizada en tres capas:

```text
Usuario
  ↓
UI Textual / Rich
  ↓
InputController
  ↓
MusicBridge
  ↓
MockBackend
  ↓
Pygame / CAVA / library.json / hilo de progreso
  ↓
MusicBridge
  ↓
UI Textual / Rich
```

La dirección del control es intencionalmente estricta:

```text
UI -> Input -> Bridge -> Backend -> Bridge -> UI
```

La UI **no debe decidir** qué pista es la actual, cómo se salta entre pistas, cómo se genera la cola, cómo se calcula el progreso, cómo se califica una canción o cómo se procesa el espectro. Su función es capturar eventos, pedir datos y pintar.

### Montaje visual

Durante `compose()`, `main.py` construye el layout principal:

```text
main-layout
├── top-section
│   ├── panel-left
│   │   ├── top-tabs
│   │   └── views-switcher
│   │       ├── LibraryView
│   │       ├── RandomQueueView
│   │       └── DirectoriesView
│   └── panel-right
│       └── InfoPanel
└── panel-bottom
    ├── CavaVisualizer
    └── PlayerBottomBar
```

La parte superior contiene las tablas de biblioteca, cola y directorios. La parte lateral derecha contiene metadatos de la pista actual y atajos. La parte inferior contiene el visualizador espectral y la barra de reproducción.

En `on_mount()`, la aplicación añade columnas a los `DataTable`, carga las tablas una única vez mediante `_populate_initial()`, cachea versiones de biblioteca y cola, configura el temporizador de actualización general y arranca la reproducción inicial con:

```python
self.bridge.play()
```

El temporizador principal corre cada `0.1` segundos:

```python
self.set_interval(0.1, self.update_ui)
```

Este timer no reconstruye todo de forma ciega. En su lugar, consulta versiones:

```python
qv = bridge.get_queue_version()
lv = bridge.get_library_version()
```

Solo si esas versiones cambian se repintan las tablas pesadas. Esto evita que `DataTable.clear()` y `DataTable.add_row()` se ejecuten continuamente en el bucle general.

### Flujo de control de teclado

Cuando el usuario presiona una tecla, Textual llama:

```python
MusicPlayerApp.on_key(event)
```

Luego la UI delega la tecla a:

```python
self.input_manager.handle_key(event.key.lower())
```

`InputController` traduce teclas concretas a comandos abstractos:

```text
space -> bridge.toggle_play()
left  -> bridge.prev()
right -> bridge.next()
r     -> bridge.toggle_random()
u/i/o -> ui_app.switch_tab(...)
1/2/3 -> ui_app.rate_current_selection(...)
enter -> ui_app.play_current_selection()
q     -> ui_app.exit()
```

La reproducción se controla desde el backend. Por ejemplo, el flujo de pausa es:

```text
Usuario presiona Space
  ↓
main.py captura event.key
  ↓
InputController.handle_key("space")
  ↓
MusicBridge.toggle_play()
  ↓
MockBackend.toggle_play()
  ↓
MockBackend.pause() o MockBackend.play()
  ↓
Backend muta is_playing y llama pygame.mixer si está disponible
  ↓
main.py.update_ui() consulta bridge.is_playing()
  ↓
PlayerBottomBar actualiza símbolo visual
```

La UI no decide si debe pausar o reproducir. Solo envía la señal.

### Flujo de renderizado pasivo

`update_ui()` hace lectura pasiva del estado:

```python
track = bridge.get_current_track()
playing = bridge.is_playing()
progress = bridge.get_progress()
```

Luego actualiza componentes visuales:

- `PlayerBottomBar.update_progress()` se llama cada tick porque el progreso cambia continuamente.
- `PlayerBottomBar.update_track()` solo se llama cuando cambia la pista o el estado de reproducción.
- `InfoPanel.update_info()` solo se llama cuando cambia la pista o el estado cacheado.
- Las tablas solo se reconstruyen cuando cambian `queue_version` o `library_version`.

Este patrón reduce la presión sobre CPU y memoria porque evita reparsear markup Rich y reconstruir widgets pesados innecesariamente.

---

## 2. 🗂️ DIRECTORIO TÉCNICO DE ARCHIVOS (ANÁLISIS DE RESPONSABILIDADES)

### `main.py`

`main.py` es el punto de entrada de la TUI. Define `MusicPlayerApp`, una clase que hereda de `textual.app.App`.

Responsabilidades principales:

- Crear la instancia global del bridge.
- Crear el controlador de input.
- Componer el layout visual.
- Montar tablas y widgets.
- Ejecutar repaints condicionales.
- Delegar eventos de teclado.
- Consultar pasivamente el estado del backend.
- Mantener caches visuales para reducir trabajo repetido.

Componentes clave:

```python
self.bridge = MusicBridge()
self.input_manager = InputController(self.bridge, self)
```

El bridge es la única entrada hacia el backend. El input manager traduce teclas en comandos.

`main.py` mantiene variables de cache:

```python
self.last_queue_version = -1
self.last_library_version = -1
self._last_track_id = -999
self._last_playing = None
```

Estas variables evitan reconstrucciones innecesarias.

El método `_populate_initial()` carga por primera vez:

- Biblioteca.
- Cola.
- Directorios detectados.

El método `_repaint_table()` reconstruye una tabla preservando la fila del cursor:

```python
cursor = table.cursor_row
table.clear()
for t in tracks:
    table.add_row(*self._format_row(t))
if cursor is not None and 0 <= cursor < len(table.rows):
    table.move_cursor(row=cursor)
```

Este patrón evita repintados destructivos frecuentes y mantiene continuidad de navegación.

`update_ui()` es el núcleo del render pasivo. No toma decisiones de negocio. Consulta estado y pinta:

```python
track = bridge.get_current_track()
playing = bridge.is_playing()
bar.update_progress(track, bridge.get_progress())
```

La decisión de qué pista está activa, qué cola existe o qué canción debe reproducirse no vive aquí.

### `core/input.py`

`core/input.py` define `InputController`.

Su responsabilidad es actuar como **mapper abstracto de eventos de teclado**. Recibe una tecla textual y decide qué señal enviar al bridge o qué acción visual mínima pedir a la UI.

Ejemplo:

```python
if key == "space":
    self.bridge.toggle_play()
elif key == "left":
    self.bridge.prev()
elif key == "right":
    self.bridge.next()
```

El controlador no sabe cómo se pausa una canción. Tampoco sabe cómo se carga audio, cómo se cambia de pista o cómo se guarda el rating. Solo traduce eventos.

Para navegación visual, sí llama a la UI:

```python
self.ui_app.switch_tab(tab_map[key])
```

Esto es aceptable porque cambiar de pestaña es una operación de presentación, no de negocio.

Para reproducción y rating, delega en métodos de `main.py` que a su vez mandan la selección al bridge:

```python
self.ui_app.rate_current_selection(int(key))
self.ui_app.play_current_selection()
```

La selección se expresa como `(tab, row)`, y el backend resuelve qué pista corresponde.

### `core/bridge.py`

`core/bridge.py` define `MusicBridge`.

Es una fachada pura bajo el patrón **Facade Pattern**. Su función es aislar a la UI del backend real.

Responsabilidades:

- Traducir comandos de UI hacia métodos del backend.
- Exponer consultas de estado.
- Entregar listas y estructuras crudas.
- Mantener estable el contrato de integración.
- Evitar que la UI importe `MockBackend`.
- Evitar que la UI conozca CAVA, Pygame, hilos o detalles de persistencia.

El bridge actual instancia:

```python
self.backend = MockBackend()
```

En la migración futura, este punto será reemplazable por:

```python
self.backend = NativeBackend()
```

o por un módulo nativo generado con Pybind11:

```python
self.backend = native_engine.Engine()
```

La UI no tendría que cambiar si se conserva la interfaz.

Métodos de control:

```python
play()
pause()
toggle_play()
next()
prev()
```

Métodos de consulta:

```python
get_current_track()
get_progress()
is_playing()
get_current_index()
```

Métodos de biblioteca y cola:

```python
get_library()
get_queue()
get_queue_version()
get_library_version()
get_directories()
```

Métodos de alto nivel:

```python
play_selection(tab, row)
rate_selection(tab, row, stars)
```

Estos métodos son importantes porque impiden que la UI resuelva lógica de selección. La UI manda coordenadas visuales; el backend interpreta.

### `core/backend.py`

`core/backend.py` contiene el núcleo lógico actual. Define:

- `Track`
- `MockBackend`

Aunque el nombre `MockBackend` sugiere simulación, actualmente es el backend funcional de la aplicación.

Responsabilidades principales:

- Cargar biblioteca desde `library.json`.
- Escanear carpetas de música si no hay biblioteca.
- Crear canciones dummy si hay pocas pistas.
- Guardar biblioteca.
- Generar cola normal o aleatoria ponderada por rating.
- Controlar reproducción con `pygame.mixer`.
- Mantener estado de reproducción.
- Mantener progreso.
- Ejecutar hilo de progreso.
- Controlar saltos.
- Resolver selección desde biblioteca o cola.
- Aplicar ratings.
- Exponer ADN acústico.
- Poseer el analizador CAVA.
- Entregar barras espectrales al visualizador.

#### Modelo `Track`

```python
class Track:
    def __init__(self, id, title, artist, album, duration, path, stars=1)
```

Atributos:

- `id`: identificador numérico.
- `title`: título de pista.
- `artist`: artista.
- `album`: álbum.
- `duration`: duración en segundos.
- `path`: ruta del archivo.
- `stars`: calificación entre 1 y 3.

Incluye serialización:

```python
to_dict()
from_dict()
```

Esto permite persistir la biblioteca en JSON.

#### Estado interno de `MockBackend`

Atributos principales:

```python
self.library = []
self.queue = []
self.current_index = -1
self.is_playing = False
self.progress = 0.0
self.queue_version = 0
self.library_version = 0
self._lock = threading.Lock()
self.db_path = "library.json"
self._cava = CavaSubprocess()
```

`queue_version` y `library_version` son fundamentales para repintados inteligentes. La UI no necesita inspeccionar diferencias internas; solo compara versiones.

#### Reproducción

Si `pygame` está disponible, se inicializa:

```python
pygame.mixer.init()
```

El backend controla:

```python
play()
pause()
toggle_play()
next_track()
prev_track()
jump_to_queue_index(index)
```

`play()` activa `is_playing` y reproduce o reanuda con Pygame.

`pause()` cambia `is_playing` a `False` y pausa Pygame.

`next_track()` y `prev_track()` actualizan `current_index`, reinician `progress` y cargan la pista real.

#### Hilo de progreso

El backend levanta un hilo daemon:

```python
self._thread = threading.Thread(target=self._playback_loop, daemon=True)
self._thread.start()
```

El bucle corre cada `0.05` segundos:

```python
time.sleep(0.05)
dt = now - self._last_tick
self.progress += dt
```

Cuando el progreso supera la duración de la pista actual, llama a `_next_track_locked()`.

El lock protege mutaciones concurrentes sobre:

- `current_index`
- `progress`
- `is_playing`
- `queue`

#### Cola aleatoria ponderada

Cuando `is_random_mode` está activo, `generate_queue()` crea una cola ponderada:

```python
pool.extend([t] * (1 if t.stars == 1 else 3 if t.stars == 2 else 6))
```

Esto significa:

```text
1 estrella -> peso 1
2 estrellas -> peso 3
3 estrellas -> peso 6
```

Luego se aplica `random.shuffle(pool)`.

#### Selección de pista

`play_selection(tab, row)` centraliza la lógica:

- Si `tab == "queue"`, salta directamente a ese índice.
- Si `tab == "library"`, busca el `track_id` de la biblioteca y luego busca ese id dentro de la cola activa.

Esto evita que `main.py` tenga que conocer cómo se relacionan biblioteca y cola.

#### Rating

`rate_selection(tab, row, stars)` identifica la pista seleccionada según la pestaña y llama a:

```python
set_rating(track.id, stars)
```

`set_rating()` actualiza biblioteca, guarda JSON, incrementa versiones y sincroniza objetos en la cola.

#### ADN acústico

`get_acoustic_dna()` retorna una huella determinista basada en pista:

```python
seed = Σ ord(c_i) × (i + 1)
```

La cadena fuente es:

```text
"{title}-{artist}-{id}"
```

El resultado define:

- `seed`
- `profile`
- `ambient_hex`
- multiplicadores de graves, medios y agudos

Esto permite asociar una identidad visual estable a cada canción.

#### Espectro

El estado actual del código delega el espectro a CAVA:

```python
return self._cava.get_data(num_bars)
```

Si no hay reproducción o no hay pista activa, devuelve ceros:

```python
return [0.0] * num_bars
```

Esto habilita el cortocircuito de silencio en el visualizador.

Aunque algunos comentarios históricos del archivo mencionan un generador matemático nativo, la implementación actual usa `CavaSubprocess`. Para la migración C++ se recomienda mover el análisis espectral real a un módulo nativo con FFT y ventana de Hanning.

### `core/cava.py`

`core/cava.py` define `CavaSubprocess`.

Su responsabilidad es levantar CAVA Linux como subproceso y leer datos binarios del espectro.

Configuración generada:

```ini
[general]
framerate = 30
bars = 128
autosens = 1

[smoothing]
monstercat = 1
gravity = 150
ignore = 0

[output]
method = raw
raw_target = /dev/stdout
data_format = binary
bit_format = 8bit
```

La optimización más importante está en `_read_loop()`:

```python
chunk = os.read(fd, 4096)
```

La lectura es bloqueante. Esto significa que el hilo duerme a nivel kernel hasta que CAVA emite datos. Es mucho más eficiente que un polling activo con sleeps cortos.

El buffer descarta frames viejos:

```python
frames_available = len(buffer) // bars
last_frame = buffer[last_frame_start : last_frame_start + bars]
del buffer[: frames_available * bars]
```

Así se evita acumulación de latencia visual.

Cada byte `0..255` se normaliza a `0.0..1.0`:

```python
parsed = [b / 255.0 for b in last_frame]
```

Luego se aplica autoganancia limitada:

```python
gain = min(1.0 / max_val, 5.0)
```

`get_data(num_bars)` adapta los 128 valores crudos a la cantidad de columnas del visualizador mediante interpolación lineal. Para optimizar, precalcula mapas de interpolación:

```python
self._interp_cache = {}
```

La clave es:

```python
(num_bars, n_raw)
```

Esto evita recalcular divisiones por barra en cada frame.

### `core/logger.py`

`core/logger.py` configura logging global hacia `app.log`.

Configuración:

```python
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
```

Cada módulo obtiene un logger nombrado:

```python
get_logger("Backend")
get_logger("InputManager")
get_logger("Visualizer")
get_logger("CavaBridge")
```

Esto permite auditar:

- Inicialización de backend.
- Inicio de Pygame.
- Fallos de CAVA.
- Teclas presionadas.
- Cambios de reproducción.
- Cambios de rating.
- Telemetría del visualizador.

### `ui/visualizer.py`

`ui/visualizer.py` define `CavaVisualizer`, un widget `Static` de Textual encargado de renderizar el ecualizador espectral.

Responsabilidades:

- Consultar barras de audio vía `self.app.bridge.get_audio_bars(w)`.
- Suavizar magnitudes.
- Mantener picos flotantes.
- Calcular geometría de barras.
- Calcular energía por bandas.
- Ajustar fondo reactivo.
- Renderizar texto Rich optimizado.
- Evitar render completo en silencio.

El visualizador usa constantes:

```python
DECAY = 0.82
AUTO_GAIN_CEILING = 0.20
PEAK_HOLD_FRAMES = 18
PEAK_GRAVITY = 0.0035
PEAK_FALL_START = 0.001
```

#### Cortocircuito de silencio

Al inicio de `update_visualizer()`:

```python
playing = self.app.bridge.is_playing()
if not playing:
    if self._silent:
        return
else:
    self._silent = False
```

Cuando ya se pintó el último frame de silencio y todos los picos decayeron, se evita completamente el render W×H. Esto ahorra el coste principal del visualizador durante pausa.

#### Adaptación a resize

Si cambia el ancho:

```python
self.previous_bars = [0.0] * w
self.peaks = [0.0] * w
self.peak_hold = [0] * w
self.peak_vel = [0.0] * w
```

Si cambia la altura:

```python
self._row_styles = self._build_row_styles(h)
```

Los estilos por fila se precalculan para evitar comparaciones y construcción de strings por frame.

#### Suavizado

El suavizado tiene ataque rápido y caída exponencial:

```python
if raw > prev:
    val = raw
else:
    decayed = prev * DECAY
    val = raw if raw > decayed else decayed
```

Esto hace que los incrementos sean inmediatos y las caídas visualmente suaves.

#### Física de picos

Cada columna mantiene:

- `peaks[x]`
- `peak_hold[x]`
- `peak_vel[x]`

Cuando la barra supera el pico, el pico se actualiza y se mantiene durante `PEAK_HOLD_FRAMES`. Luego cae con velocidad creciente:

```python
pvel = peak_vel[x] + PEAK_GRAVITY
pv2 = pv - pvel
```

Esto produce picos flotantes visuales.

#### Energía por bandas

El ancho se divide en:

```text
0%  - 30% -> graves
30% - 65% -> medios
65% - 100% -> agudos
```

Se calculan promedios:

```python
bass_avg
mid_avg
high_avg
```

Estos alimentan el fondo reactivo.

#### Render con run-length batching

En lugar de hacer `Text.append()` por celda, agrupa caracteres consecutivos con el mismo estilo.

El coste original sería aproximadamente:

```text
w × h append calls
```

En una pantalla de 220 × 50:

```text
11.000 append/frame
```

Con batching, cada fila suele tener pocas zonas:

```text
vacío | barra | pico
```

Esto reduce drásticamente las llamadas a Rich.

### `ui/views.py`

`ui/views.py` define tres contenedores:

- `LibraryView`
- `RandomQueueView`
- `DirectoriesView`

Cada vista compone un `DataTable`.

`LibraryView` muestra la biblioteca completa.

`RandomQueueView` muestra la cola actual.

`DirectoriesView` muestra directorios inspeccionados:

- `~/Música`
- `~/Music`

Aunque cada clase tiene métodos `populate()`, el flujo actual de `main.py` repinta directamente con `_repaint_table()` para centralizar preservación de cursor y lógica de actualización por versión.

### `ui/player.py`

`ui/player.py` define `PlayerBottomBar`.

Responsabilidades:

- Mostrar estado de reproducción.
- Mostrar título y artista.
- Mostrar barra de progreso.
- Mostrar tiempo actual y duración total.

Está optimizado en dos rutas:

```python
update_track(track, is_playing)
update_progress(track, progress)
```

`update_track()` solo debe llamarse cuando cambia pista o estado. Actualiza:

- Label de play/pause.
- Título.
- Artista.

`update_progress()` se llama cada tick y actualiza:

- `ProgressBar`
- tiempo textual

Esto evita reparsear texto Rich pesado continuamente.

### `ui/info_panel.py`

`ui/info_panel.py` define `InfoPanel`.

Responsabilidades:

- Mostrar metadatos de pista.
- Mostrar artista.
- Mostrar rating.
- Mostrar atajos.

`update_info(track)` actualiza:

```python
#info-title
#info-artist
#info-rating
```

Esta actualización se llama desde `main.py` solo cuando cambia la pista o el estado cacheado, no en cada tick visual.

---
