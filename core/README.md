
# 🚀 BLUEPRINT DE MIGRACIÓN A C++ Y ARQUITECTURA DE ESTRUCTURA DE DATOS (MÁXIMA PRIORIDAD)

La estrategia recomendada es mantener Python como capa de presentación y migrar progresivamente el núcleo a C++.

El objetivo final es:

```text
Textual UI Python
  ↓
core/bridge.py
  ↓
Módulo nativo C++ compilado
  ↓
Motor de audio / cola / biblioteca / espectro / timeline
```

`bridge.py` debe conservar su API pública. El frontend no debe saber si el backend es Python o C++.

### A) Nueva Estructura del Directorio `core/` (Árbol de Directorios Propuesto)

Estructura recomendada:

```text
core/
├── __init__.py
├── bridge.py
├── backend.py
├── backend_native.py
├── native_engine.cpp
├── engine/
│   ├── include/
│   │   ├── Track.hpp
│   │   ├── DoublyLinkedList.hpp
│   │   ├── QueueManager.hpp
│   │   ├── LibraryManager.hpp
│   │   ├── AudioPlayer.hpp
│   │   ├── SpectrumAnalyzer.hpp
│   │   ├── PlaybackState.hpp
│   │   ├── Engine.hpp
│   │   └── CApi.hpp
│   ├── src/
│   │   ├── Track.cpp
│   │   ├── DoublyLinkedList.cpp
│   │   ├── QueueManager.cpp
│   │   ├── LibraryManager.cpp
│   │   ├── AudioPlayer.cpp
│   │   ├── SpectrumAnalyzer.cpp
│   │   ├── PlaybackState.cpp
│   │   ├── Engine.cpp
│   │   └── CApi.cpp
│   ├── third_party/
│   │   └── miniaudio.h
│   ├── CMakeLists.txt
│   └── README_ENGINE.md
└── logger.py
```

Archivos clave:

- `core/bridge.py`: permanece como fachada Python.
- `core/backend.py`: backend Python legado durante transición.
- `core/backend_native.py`: adaptador Python que carga el motor C++.
- `core/native_engine.cpp`: entrada Pybind11, si se elige módulo Python nativo.
- `core/engine/include/`: headers C++.
- `core/engine/src/`: implementaciones C++.
- `core/engine/third_party/`: librerías header-only como `miniaudio.h`.

Modo Pybind11 esperado:

```text
core/native_engine.cpp -> compila a native_engine.so
```

Modo ctypes esperado:

```text
core/engine/src/CApi.cpp -> compila a libmusic_engine.so
```

### B) Recomendación y Diseño de Clases en C++

#### `Track.hpp` / `Track.cpp`

Clase:

```cpp
class Track
```

Atributos privados recomendados:

```cpp
int id_;
std::string title_;
std::string artist_;
std::string album_;
double duration_;
std::string path_;
int stars_;
```

Métodos públicos:

```cpp
Track();
Track(int id, std::string title, std::string artist, std::string album,
      double duration, std::string path, int stars);

int id() const;
const std::string& title() const;
const std::string& artist() const;
const std::string& album() const;
double duration() const;
const std::string& path() const;
int stars() const;

void setStars(int stars);
```

Responsabilidad:

Representar una pista de audio con metadatos inmutables salvo rating. Debe ser barato de mover y seguro para almacenar dentro de nodos o vectores.

#### `DoublyLinkedList.hpp` / `DoublyLinkedList.cpp`

Clase:

```cpp
template <typename T>
class DoublyLinkedList
```

Nodo interno:

```cpp
struct Node {
    T data;
    Node* next;
    Node* prev;
};
```

Atributos privados:

```cpp
Node* head_;
Node* tail_;
std::size_t size_;
```

Métodos públicos:

```cpp
Node* pushBack(const T& value);
Node* pushFront(const T& value);
void remove(Node* node);
void clear();

Node* head() const;
Node* tail() const;
std::size_t size() const;
bool empty() const;
```

Responsabilidad:

Gestionar la cola de reproducción como lista doblemente enlazada. Permite avance y retroceso en O(1) desde el nodo actual.

#### `QueueManager.hpp` / `QueueManager.cpp`

Clase:

```cpp
class QueueManager
```

Atributos privados:

```cpp
DoublyLinkedList<Track> queue_;
DoublyLinkedList<Track>::Node* current_;
std::unordered_map<int, DoublyLinkedList<Track>::Node*> nodeByTrackId_;
std::uint64_t version_;
bool randomMode_;
```

Métodos públicos:

```cpp
void buildLinearQueue(const std::vector<Track>& library);
void buildWeightedRandomQueue(const std::vector<Track>& library);

const Track* currentTrack() const;
const Track* next();
const Track* previous();
const Track* jumpToIndex(std::size_t index);
const Track* jumpToTrackId(int trackId);

std::size_t currentIndex() const;
std::vector<Track> snapshot() const;

std::uint64_t version() const;
bool randomMode() const;
void setRandomMode(bool enabled);
```

Responsabilidad:

Gestionar la cola real de reproducción. Debe mantener un puntero al nodo actual para navegación O(1) entre canciones vecinas.

#### `LibraryManager.hpp` / `LibraryManager.cpp`

Clase:

```cpp
class LibraryManager
```

Atributos privados:

```cpp
std::vector<Track> tracks_;
std::unordered_map<int, std::size_t> indexById_;
std::unordered_map<int, Track*> trackById_;
std::uint64_t version_;
```

Métodos públicos:

```cpp
void loadFromJson(const std::string& path);
void saveToJson(const std::string& path) const;
void scanDirectories(const std::vector<std::string>& directories);

const Track* findById(int id) const;
Track* mutableFindById(int id);

const std::vector<Track>& tracks() const;
void setRating(int trackId, int stars);

std::uint64_t version() const;
```

Responsabilidad:

Cargar, indexar, consultar y persistir biblioteca. La tabla hash permite acceso directo por `TrackID`.

#### `AudioPlayer.hpp` / `AudioPlayer.cpp`

Clase:

```cpp
class AudioPlayer
```

Atributos privados:

```cpp
std::atomic<bool> initialized_;
std::atomic<bool> playing_;
std::mutex audioMutex_;
double volume_;
std::string loadedPath_;
```

Si se usa `miniaudio`:

```cpp
ma_engine engine_;
ma_sound currentSound_;
```

Métodos públicos:

```cpp
bool initialize();
void shutdown();

bool load(const Track& track);
void play();
void pause();
void stop();
void seek(double seconds);

bool isPlaying() const;
double currentPosition() const;
void setVolume(double volume);
double volume() const;
```

Responsabilidad:

Reemplazar `pygame.mixer` por audio nativo de bajo coste. Debe encapsular inicialización, carga, reproducción, pausa y liberación de recursos.

#### `SpectrumAnalyzer.hpp` / `SpectrumAnalyzer.cpp`

Clase:

```cpp
class SpectrumAnalyzer
```

Atributos privados:

```cpp
std::vector<float> pcmBuffer_;
std::vector<float> window_;
std::vector<float> magnitudes_;
std::vector<float> smoothed_;
std::size_t fftSize_;
std::mutex spectrumMutex_;
```

Métodos públicos:

```cpp
void initialize(std::size_t fftSize);
void pushSamples(const float* samples, std::size_t count);
std::vector<float> getBars(std::size_t numBars);

void applyHanningWindow();
void computeFFT();
void computeMagnitudeBands(std::size_t numBars);
```

Responsabilidad:

Calcular magnitudes espectrales nativas. Debe aplicar ventana de Hanning antes de FFT para reducir leakage espectral.

Ventana de Hanning:

```text
w[n] = 0.5 × (1 - cos((2πn) / (N - 1)))
```

Muestra ventaneada:

```text
xw[n] = x[n] × w[n]
```

Luego se calcula FFT y magnitudes:

```text
mag[k] = sqrt(real[k]^2 + imag[k]^2)
```

Las magnitudes se agrupan en barras visuales normalizadas `0.0..1.0`.

#### `PlaybackState.hpp` / `PlaybackState.cpp`

Clase:

```cpp
class PlaybackState
```

Atributos privados:

```cpp
std::atomic<bool> isPlaying_;
std::atomic<double> progress_;
std::atomic<int> currentTrackId_;
std::atomic<std::uint64_t> queueVersion_;
std::atomic<std::uint64_t> libraryVersion_;
```

Métodos públicos:

```cpp
bool isPlaying() const;
double progress() const;
int currentTrackId() const;

void setPlaying(bool value);
void setProgress(double value);
void setCurrentTrackId(int id);

void incrementQueueVersion();
void incrementLibraryVersion();

std::uint64_t queueVersion() const;
std::uint64_t libraryVersion() const;
```

Responsabilidad:

Centralizar estado observable y versiones para que Python pueda consultar sin bloquear operaciones internas largas.

#### `Engine.hpp` / `Engine.cpp`

Clase:

```cpp
class Engine
```

Atributos privados:

```cpp
LibraryManager library_;
QueueManager queue_;
AudioPlayer audio_;
SpectrumAnalyzer spectrum_;
PlaybackState state_;

std::thread playbackThread_;
std::atomic<bool> running_;
std::mutex engineMutex_;
```

Métodos públicos:

```cpp
void initialize();
void shutdown();

void play();
void pause();
void togglePlay();
void next();
void previous();

void playSelection(const std::string& tab, std::size_t row);
void rateSelection(const std::string& tab, std::size_t row, int stars);
void toggleRandom();

Track currentTrack() const;
double progress() const;
bool isPlaying() const;

std::vector<Track> librarySnapshot() const;
std::vector<Track> queueSnapshot() const;
std::vector<float> audioBars(std::size_t numBars) const;

std::uint64_t queueVersion() const;
std::uint64_t libraryVersion() const;
```

Responsabilidad:

Ser el equivalente nativo de `MockBackend`. Esta clase debe ser la unidad principal expuesta a Python.

### C) Implementación Obligatoria de Estructuras de Datos Avanzadas

#### 1. Lista Doblemente Enlazada Personalizada (`DoublyLinkedList`)

La cola de reproducción debe implementarse con una lista doblemente enlazada personalizada.

Nodo:

```cpp
struct Node {
    Track data;
    Node* next;
    Node* prev;
};
```

Cada nodo conoce el anterior y el siguiente. El manager mantiene:

```cpp
Node* head_;
Node* tail_;
Node* current_;
```

Operaciones:

```text
next     -> current_ = current_->next
previous -> current_ = current_->prev
```

Coste:

```text
next(): O(1)
previous(): O(1)
insert after current: O(1)
remove current: O(1)
```

Esto es óptimo para reproducción lineal porque el reproductor casi siempre se mueve localmente:

```text
canción actual -> siguiente -> siguiente -> anterior
```

En una cola basada solo en `std::vector`, avanzar por índice también es O(1), pero eliminar, insertar o mantener historial alrededor del elemento actual puede implicar movimientos de memoria O(n). La lista doble permite mutaciones locales baratas y conserva punteros estables.

Diseño circular opcional:

```text
tail_->next = head_
head_->prev = tail_
```

Esto permite wrap-around sin ramas complejas:

```cpp
current_ = current_->next ? current_->next : head_;
```

o, si es circular:

```cpp
current_ = current_->next;
```

Para este proyecto, una lista doblemente enlazada no circular con fallback explícito es más fácil de depurar. Una lista circular es más elegante para reproducción infinita.

#### 2. Tabla Hash (`std::unordered_map`)

La biblioteca debe indexarse con hash map:

```cpp
std::unordered_map<int, Track*> trackById_;
```

Esto permite resolver:

```text
TrackID -> Track*
```

en tiempo promedio O(1).

Para conectar biblioteca con cola:

```cpp
std::unordered_map<int, DoublyLinkedList<Track>::Node*> nodeByTrackId_;
```

Esto permite:

```text
TrackID -> Node*
```

Entonces, al seleccionar una pista desde la biblioteca, el motor hace:

```cpp
auto it = nodeByTrackId_.find(trackId);
if (it != nodeByTrackId_.end()) {
    current_ = it->second;
}
```

Coste promedio:

```text
find(trackId): O(1)
jump to node: O(1)
```

Advertencia: si la cola aleatoria contiene pistas duplicadas por ponderación, `TrackID -> Node*` no puede representar todas las apariciones. En ese caso se recomienda:

```cpp
std::unordered_map<int, std::vector<Node*>> nodesByTrackId_;
```

La primera aparición puede reproducirse por defecto, o se puede seleccionar la aparición más cercana al nodo actual.

#### 3. Vectores Dinámicos Estáticos (`std::vector<float>`)

El procesamiento espectral debe usar `std::vector<float>` por tres razones:

1. Memoria contigua.
2. Buen comportamiento de cache.
3. Compatibilidad directa con FFT, SIMD y APIs C.

Buffers recomendados:

```cpp
std::vector<float> pcmBuffer_;
std::vector<float> window_;
std::vector<float> fftInput_;
std::vector<float> magnitudes_;
std::vector<float> bars_;
```

Para evitar realocaciones:

```cpp
pcmBuffer_.reserve(fftSize);
window_.resize(fftSize);
magnitudes_.resize(fftSize / 2);
bars_.resize(numBars);
```

Buffer circular:

```cpp
class RingBuffer {
private:
    std::vector<float> data_;
    std::size_t writeIndex_;
    std::size_t size_;
};
```

Escritura:

```text
data_[writeIndex_] = sample
writeIndex_ = (writeIndex_ + 1) % capacity
```

Coste:

```text
push sample: O(1)
```

Esto permite alimentar el analizador con audio real sin bloquear la UI.

### D) Herramientas, Librerías y Mecanismos de Conexión

#### Audio nativo recomendado

Opciones:

1. **miniaudio.h**
   - Header-only.
   - Muy portable.
   - Bajo overhead.
   - Buena opción para Linux, Windows y macOS.
   - Ideal para un proyecto académico o de migración rápida.

2. **SFML Audio**
   - API simple.
   - Buena documentación.
   - Integra reproducción de archivos fácilmente.
   - Menos flexible para análisis espectral profundo.

3. **SoLoud**
   - Potente para mezcla, efectos y múltiples fuentes.
   - Muy útil si se planean efectos avanzados.
   - Más complejo que miniaudio.

Recomendación principal:

```text
miniaudio.h
```

Motivo: permite reemplazar Pygame Mixer con mínimo overhead y máxima portabilidad. Además, facilita capturar samples para el `SpectrumAnalyzer`.

#### Interoperabilidad con Pybind11

Pybind11 es la opción más limpia si se quiere exponer clases C++ como objetos Python.

Ejemplo conceptual:

```cpp
PYBIND11_MODULE(native_engine, m) {
    py::class_<Engine>(m, "Engine")
        .def(py::init<>())
        .def("initialize", &Engine::initialize)
        .def("play", &Engine::play)
        .def("pause", &Engine::pause)
        .def("toggle_play", &Engine::togglePlay)
        .def("next_track", &Engine::next)
        .def("prev_track", &Engine::previous)
        .def("get_progress", &Engine::progress)
        .def("is_playing", &Engine::isPlaying)
        .def("get_audio_bars", &Engine::audioBars);
}
```

`backend_native.py` podría envolverlo:

```python
import native_engine

class NativeBackend:
    def __init__(self):
        self.engine = native_engine.Engine()
        self.engine.initialize()

    def play(self):
        self.engine.play()

    def pause(self):
        self.engine.pause()

    def toggle_play(self):
        self.engine.toggle_play()

    def get_audio_bars(self, num_bars):
        return self.engine.get_audio_bars(num_bars)
```

`bridge.py` cambiaría solo esta línea:

```python
self.backend = NativeBackend()
```

#### Interoperabilidad con `ctypes` y `extern "C"`

Si se prefiere una ABI C estable:

```cpp
extern "C" {
    EngineHandle* engine_create();
    void engine_destroy(EngineHandle* handle);

    void engine_play(EngineHandle* handle);
    void engine_pause(EngineHandle* handle);
    void engine_toggle_play(EngineHandle* handle);

    double engine_get_progress(EngineHandle* handle);
    bool engine_is_playing(EngineHandle* handle);

    int engine_get_audio_bars(EngineHandle* handle, float* out, int maxBars);
}
```

Python:

```python
self.lib.engine_get_audio_bars(self.handle, buffer, num_bars)
```

Ventajas:

- ABI más estable.
- No depende de detalles de C++ name mangling.
- Puede integrarse con otros lenguajes.

Desventajas:

- Más boilerplate.
- Hay que convertir estructuras manualmente.
- Menos cómodo para listas de `Track`.

#### Flujo de señal: pausa por espacio

Con Pybind11:

```text
Usuario presiona Space
  ↓
InputController.handle_key("space")
  ↓
MusicBridge.toggle_play()
  ↓
NativeBackend.toggle_play()
  ↓
native_engine.Engine.toggle_play()
  ↓
Engine::togglePlay()
  ↓
AudioPlayer::pause() o AudioPlayer::play()
  ↓
PlaybackState::setPlaying(...)
  ↓
UI consulta bridge.is_playing()
```

Con `ctypes`:

```text
MusicBridge.toggle_play()
  ↓
NativeBackend.toggle_play()
  ↓
lib.engine_toggle_play(handle)
  ↓
Engine::togglePlay()
```

#### Flujo de floats para visualizador

C++:

```cpp
std::vector<float> Engine::audioBars(std::size_t numBars);
```

Pybind11 convierte automáticamente `std::vector<float>` a lista Python si está configurado.

Python:

```python
bars = self.backend.get_audio_bars(num_bars)
```

La UI no cambia.

Con `ctypes`, Python crea un buffer:

```python
buffer = (ctypes.c_float * num_bars)()
count = lib.engine_get_audio_bars(handle, buffer, num_bars)
bars = [buffer[i] for i in range(count)]
```

### E) Guía de Migración Paso a Paso

#### Fase 1: Abstracción de tipos y conexión de prueba

Objetivo:

Crear un backend nativo mínimo sin reemplazar aún el backend Python.

Tareas:

1. Crear `core/backend_native.py`.
2. Crear `core/native_engine.cpp`.
3. Configurar CMake o setup build para Pybind11.
4. Exponer una clase `Engine` mínima.
5. Implementar métodos dummy:

```cpp
play()
pause()
togglePlay()
isPlaying()
progress()
audioBars(numBars)
```

6. Hacer que `audioBars()` devuelva un vector artificial de floats.
7. Probar que `bridge.py` puede alternar entre:

```python
MockBackend()
NativeBackend()
```

Criterio de éxito:

- La UI arranca.
- Space alterna play/pause.
- El visualizador recibe floats.
- No se modifica la UI.

#### Fase 2: Desarrollo de estructuras de datos nativas

Objetivo:

Migrar biblioteca y cola a C++.

Tareas:

1. Implementar `Track`.
2. Implementar `DoublyLinkedList<Track>`.
3. Implementar `QueueManager`.
4. Implementar `LibraryManager`.
5. Implementar carga básica desde `library.json`.
6. Implementar snapshots de biblioteca y cola hacia Python.
7. Implementar `queueVersion` y `libraryVersion`.
8. Implementar `playSelection(tab, row)`.
9. Implementar `rateSelection(tab, row, stars)`.

Criterio de éxito:

- Las tablas se renderizan desde datos C++.
- La cola navega con `next` y `previous`.
- La selección desde biblioteca reproduce la pista correcta.
- Los ratings actualizan versión de biblioteca.

#### Fase 3: Integración del motor de audio e hilos

Objetivo:

Reemplazar Pygame Mixer.

Tareas:

1. Integrar `miniaudio.h`.
2. Implementar `AudioPlayer`.
3. Reproducir archivos reales.
4. Implementar pausa, play, stop y cambio de pista.
5. Crear thread nativo de progreso.
6. Proteger estado con mutex y atomics.
7. Conectar fin de pista con `QueueManager::next()`.
8. Implementar volumen.
9. Garantizar shutdown limpio.

Criterio de éxito:

- Audio real reproduce desde C++.
- Pygame ya no es necesario.
- El progreso reportado a Python es correcto.
- Al terminar una canción se salta a la siguiente.
- No hay race conditions visibles.

#### Fase 4: Desconexión de `backend.py` y puesta en marcha del Bridge nativo

Objetivo:

Usar C++ como backend principal.

Tareas:

1. Cambiar `bridge.py` para instanciar `NativeBackend`.
2. Mantener `backend.py` como fallback temporal.
3. Migrar `get_acoustic_dna()` o equivalente a C++.
4. Migrar `get_audio_bars()` a `SpectrumAnalyzer`.
5. Retirar CAVA si el análisis espectral nativo ya funciona.
6. Medir CPU con reproducción activa, pausa y navegación.
7. Validar que `DataTable` solo repinta por versión.
8. Validar shutdown sin hilos colgados.
9. Congelar la API pública del bridge.

Criterio de éxito:

- Python queda como UI + bridge.
- C++ controla reproducción, cola, biblioteca, progreso y espectro.
- `backend.py` puede retirarse o mantenerse solo como backend de simulación.
- La migración no exige cambios estructurales en `main.py`, `ui/` ni `core/input.py`.

---

## Conclusión Técnica

El proyecto ya está orientado correctamente hacia una arquitectura desacoplada. La UI consulta de forma pasiva y evita reconstrucciones pesadas mediante versiones. `bridge.py` actúa como punto de sustitución natural. `backend.py` concentra el estado real y ya contiene los comandos de alto nivel necesarios para impedir que la UI tome decisiones de negocio.

La migración a C++ debe concentrarse en reemplazar progresivamente `MockBackend` por un `Engine` nativo que implemente la misma superficie pública. La estructura recomendada combina:

- `DoublyLinkedList` para cola de reproducción.
- `std::unordered_map` para indexación O(1).
- `std::vector<float>` para buffers espectrales.
- `miniaudio.h` para audio nativo.
- Pybind11 o `ctypes` para interoperabilidad.

La clave arquitectónica es conservar intacto el contrato de `MusicBridge`. Mientras `bridge.py` siga ofreciendo los mismos métodos, la UI puede permanecer estable y el backend puede evolucionar hacia C++ sin fracturar el sistema.