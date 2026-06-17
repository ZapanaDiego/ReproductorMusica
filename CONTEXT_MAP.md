# [DOCUMENTO] CONTEXT_MAP.md — ARQUITECTURA INTEGRAL DEL REPRODUCTOR

Este documento empaqueta la lógica existente, flujos de datos y contratos de la arquitectura TUI (Terminal User Interface) del reproductor de música. Actúa como memoria a largo plazo y establece fronteras arquitectónicas para futuras migraciones (como la inyección de motores C++).

---

## 1. MAPA DE COMPONENTES ACTUAL (Caja Blanca)

La arquitectura sigue un patrón estricto de separación de responsabilidades a través de una **Fachada (Facade Pattern)** entre el front-end en Textual y el núcleo de estado/audio de Python.

- **Frontend (`main.py`, `ui/`)**: Contiene la aplicación principal (`MusicPlayerApp`), el visualizador del espectro (`ui/visualizer.py`), el reproductor base (`ui/player.py`), el panel lateral (`ui/info_panel.py`) y las diferentes vistas tabulares (`ui/views.py`). Carece totalmente de estado propio sobre la música o acceso al disco.
- **Puente (`core/bridge.py`)**: Clase `MusicBridge` que encapsula la instancia de backend. Recibe todas las órdenes de la UI y devuelve estructuras de datos limpias.
- **Backend (`core/backend.py`)**: Contiene la clase `MockBackend` (motor lógico asíncrono con `pygame`), el modelo de datos `Track`, el control del `CavaSubprocess` y el acceso/serialización al `library.json`. Mantiene su propio bucle en un hilo demonio (`_thread = threading.Thread(target=self._playback_loop, daemon=True)`).
- **Controlador de Entrada (`core/input.py`)**: `InputController` es el mediador exclusivo de eventos de teclado.

### Ciclo de vida de un evento (De la Tecla al Sistema):
1. **Captura:** El usuario presiona una tecla. Textual emite un evento captado por `MusicPlayerApp.on_key(event)`.
2. **Delegación Absoluta:** `main.py` no procesa el evento; lo pasa íntegro a `self.input_manager.handle_key(event.key)`.
3. **Enrutamiento (InputController):** Analiza la tecla.
   - Si concierne a UI pura (ej. 'u', 'i', 'o' para cambiar vistas o '1', '2', '3', 'enter' para interactuar con tablas), se invoca métodos expuestos en `MusicPlayerApp` (`switch_tab`, `rate_current_selection`, `play_current_selection`).
   - Si afecta a reproducción (ej. 'space', flechas de dirección), invoca métodos puros del bridge (`toggle_play`, `next`, `prev`).
4. **Ejecución y Modificación de Estado:** El `MusicBridge` invoca las rutinas correspondientes de `MockBackend`. Para operaciones de salto o estado, el backend toma un Lock (`self._lock`) protegiendo las listas de reproducción asíncronas y el control sobre Pygame.

---

## 2. MECANISMOS DE OPTIMIZACIÓN Y RENDERIZADO

La terminal es lenta para repintados de área completa. El sistema evita sobrecargar el bucle de eventos de Textual utilizando estrategias avanzadas:

### Renderizado Diferido por Versiones
En `main.py`, el método `update_ui()` se ejecuta mediante un `set_interval(0.1)`. Repintar componentes `DataTable` por cada frame colapsaría el rendimiento de CPU.
Para evitarlo, `MockBackend` implementa un sistema discreto de cacheo de versiones (`queue_version` y `library_version`). Cada vez que la cola se altera (shuffle, final de pista, calificación de estrella), el backend incrementa estas variables enteras. `update_ui()` solo invoca `_repaint_table()` si detecta que la versión solicitada a través de `bridge.get_queue_version()` difiere de la local.

### Modelo "Zero-Backpressure" (`ui/visualizer.py`)
El visualizador espectral no usa un bucle "ciego" de Textual (como `set_interval`), el cual puede acumular tareas pendientes y generar colapso (backpressure) si la terminal no logra renderizar los FPS deseados.
En su versión 6, implementa un modelo **Render Pull**:
1. El widget sobreescribe el método nativo `render()`.
2. La recolección del vector numérico del espectro (`bridge.get_audio_bars()`) y la conversión a caracteres sub-pixel de Unicode (bloques de un octavo) se ejecutan dentro del método `_tick()`.
3. Al finalizar la compilación visual de `_tick()`, llama explícitamente a `self.refresh(repaint=True, layout=False)`. Este flag obliga a Textual a redibujar solo los píxeles *sin* recalcular la estructura DOM de pantalla completa.
4. **Programación recursiva:** Como último paso en `_tick()`, se usa `self.set_timer(_FRAME_INTERVAL, self._tick)` para solicitar el siguiente cuadro. Al hacerlo solo al finalizar el proceso, se garantiza un retraso de 0 frames pendientes, descartando el temido "efecto acordeón". Adicionalmente, implementa "throttling" de 15 FPS para los colores reactivos del entorno general.

### Flujos Continuos vs Eventos Discretos (`ui/player.py`)
En el diseño UI, hay metadatos volátiles y constantes.
- **Flujo Continuo:** El progreso de reproducción avanza al instante (precisión temporal basada en iteraciones del demonio y del `update_ui` a 0.1s). El método `update_progress` empuja el nuevo valor de la variable `progress` de punto flotante a una barra nativa.
- **Evento Discreto:** El parseo de texto con *Rich* (tags markup de formato y color) es sumamente pesado. Para evitarlo, la variable que muestra el "título" y "estado actual de reproducción" mediante `update_track()` *solo* se repinta si el `bridge.get_current_track().id` difiere del caché privado `self._last_track_id` o si cambia `self._last_playing`.

---

## 3. CONTRATOS DE DATOS DE LA FACHADA (`core/bridge.py`)

La UI interactúa **solo** mediante la API de `MusicBridge`. Las entradas y salidas nativas para garantizar el 100% de desacoplamiento son:

#### Comandos de Reproducción
- `play()`, `pause()`, `toggle_play()`, `next()`, `prev()`: Sin argumentos, sin retorno (mutaciones de sistema).
- `jump_to_index(index: int)`: Salto a canción en índice numérico.

#### Consultas de Estado Continuo
- `get_current_track() -> Track | None`: Retorna un objeto modelo `Track` (el cual será compatible sin importar cómo se gestione en C++).
- `get_progress() -> float`: Segundos actuales de canción en curso.
- `is_playing() -> bool`: Flag del estatus general.
- `get_current_index() -> int`: Posición entera de la cola actual.

#### Vistas y Configuración
- `get_library() -> list[Track]` / `get_queue() -> list[Track]`: Arreglos planos listos para tabular.
- `get_queue_version() -> int` / `get_library_version() -> int`: Marcas de cacheo.
- `get_directories() -> list[dict]`: Arreglo estandarizado de diccionarios (claves `"Directorio"` y `"Existe"`).
- `toggle_random() -> bool`: Alterna flag de sistema.
- `is_random_mode() -> bool`.
- `play_selection(tab: str, row: int)` / `rate_selection(tab: str, row: int, stars: int)`: Acciones de evento (interfaz provee pestaña como cadena de texto, `row` como entero y estrellas como entero).

#### Renderizado Especial
- `get_audio_bars(num_bars: int) -> list[float]`: Entrega un arreglo normalizado entre 0.0 y 1.0. El Bridge aísla el manejo de CAVA; de encontrarse la pista en pausa, el motor regresa un arreglo de ceros y cancela todo consumo de CPU matemático.
- `get_acoustic_dna() -> dict`: Retorna metadata cromática pre-procesada (`seed`, `profile`, `ambient_hex`, `bass_mult`, `mid_mult`, `treble_mult`).

---

## 4. ESQUEMA DE PERSISTENCIA ACTUAL (`library.json`)

La información base de metadatos se lee e inyecta mediante un array JSON crudo (`list[dict]`).
El formato de cada objeto esperado es:

```json
[
  {
    "id": 1,
    "title": "Nombre de la cancion",
    "artist": "Artista Local",
    "album": "Local",
    "duration": 216,
    "path": "/home/user/Música/archivo.mp3",
    "stars": 1
  }
]
```
`MockBackend` absorbe este archivo a través de la función de clase `@classmethod Track.from_dict()`. Todo sistema futuro que extienda esto (como listas doblemente enlazadas o gestor en C++) debe poder exportar e importar esta misma serialización base para ser retro-compatible.

---

## 5. RESTRICCIONES DE EXPANSIÓN Y LÍNEAS ROJAS ARQUITECTÓNICAS

Para no socavar el estado altamente desacoplado, **CUALQUIER automatización futura debe respetar los siguientes dogmas**:

1. **Aislamiento Total del UI:**
   La interfaz gráfica (`ui/` y `main.py`) **jamás** debe abrir un archivo, escanear el OS o consultar rutas. Ninguna variable del `MockBackend` se accede de forma directa (`bridge.backend.xxx` está proscrito). Solo se usa la Fachada de `MusicBridge`.
2. **Iniciativa Pre-Textual (Pre-Bucle):**
   Textual intercepta el bucle de eventos general y se apodera de los streams `stdout` y `stdin`. Si se planea agregar un módulo CLI (como un Login de Usuario con animaciones ANSI o impresiones secuenciales), debe ejecutarse y terminar su ciclo vital *limpiamente* **antes** de que ocurra `MusicPlayerApp().run()`.
3. **Cascarón de Inyección Nativo C++:**
   La arquitectura está pre-modelada para recibir un motor en C++. Existen dos carpetas (`core/engine/include/` y `core/engine/src/`) que se mantienen **vacías a propósito** y protegidas.
   Cualquier inyección a este espacio (sea para la creación de Tablas Hash, Listas Enlazadas de la cola, o el cálculo espectral puro sobre punteros) debe estar empaquetada tras `ctypes`, `pybind11` o una DLL, de tal modo que el `MockBackend` de Python (o una derivación futura, `CppBackend`) pueda engancharse al `MusicBridge` sin que la fachada rompa sus contratos descritos en el apartado 3.
