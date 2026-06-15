# ARCHITECTURE MASTER PLAN
## Motor de Audio C++ para Reproductor Musical Híbrido (Python Textual + C++17/20)


## Arbol de directorios
```bash
core/
├── __init__.py
├── bridge.py                  ← Fachada Python (Mantiene la API pública intacta)
├── backend.py                 ← Backend Python legado (Simulación/Mock)
├── backend_native.py          ← Adaptador Python que carga el binario .so/.dll usando ctypes
└── engine/
    ├── include/               ← Archivos de Cabecera (.hpp)
    │   ├── Track.hpp          ← Definición de la entidad canción y mapeos de structs C
    │   ├── DoublyLinkedList.hpp ← Estructura de Datos PURA (Memoria dinámica, nodos, punteros)
    │   ├── QueueManager.hpp   ← Lógica de la Cola (Random Ponderado por Estrellas)
    │   ├── LibraryManager.hpp ← Gestión de Biblioteca (Tabla Hash std::unordered_map e inyección JSON)
    │   ├── AudioPlayer.hpp    ← Reproducción nativa por hardware (Abstracción de miniaudio.h)
    │   ├── SpectrumAnalyzer.hpp ← Procesamiento espectral de buffers PCM (Frecuencias para el visualizador)
    │   ├── PlaybackState.hpp  ← Estado atómico síncrono compartido entre hilos
    │   ├── Engine.hpp         ← Fachada Central de C++ (Orquestador de todos los managers)
    │   └── CApi.hpp           ← Declaraciones extern "C" planas para interoperabilidad
    ├── src/                   ← Implementaciones de Código (.cpp)
    │   ├── Track.cpp
    │   ├── DoublyLinkedList.cpp
    │   ├── QueueManager.cpp
    │   ├── LibraryManager.cpp
    │   ├── AudioPlayer.cpp
    │   ├── SpectrumAnalyzer.cpp
    │   ├── PlaybackState.cpp
    │   ├── Engine.cpp
    │   ├── CApi.cpp           ← Exportación de funciones para Ctypes
    │   └── PybindBindings.cpp ← Alternativa de exportación directa para Pybind11
    ├── third_party/           ← Librerías de terceros (Cabecera Única / Header-only)
    │   ├── miniaudio.h        ← Decodificación y captura de dispositivos de audio
    │   └── nlohmann/
    │       └── json.hpp       ← Parseo ultrarrápido de library.json en C++
    ├── CMakeLists.txt         ← Script de compilación multiplataforma
    └── README_ENGINE.md       ← Instrucciones nativas de compilación (g++, clang, cmake)
```

## 🌐 SECCIÓN MAESTRA: MAPA DE CONECTIVIDAD Y PIPELINE TRANSFRONTERIZO

El diseño del sistema exige una frontera dura entre el entorno gestionado de Python (donde ocurre el pintado de la UI de Textual y el bucle de eventos) y el entorno nativo de alto rendimiento en C++ (donde ocurre el procesamiento numérico y el control de hardware).

### Diagrama de las 5 Capas de Ejecución

```text
[1. CAPA DE INTERFAZ - Python]     (ui/player.py, main.py)
         │  - Detecta eventos de teclado/mouse (ej. presionar botón de pausa).
         │  - Llama a los métodos de alto nivel de la fachada.
         ▼
[2. CAPA DE FACHADA - Python]      (core/bridge.py)
         │  - Actúa como Firewall estructural.
         │  - API pública inalterable: `def toggle_play(self): self.backend.toggle_play()`
         ▼
[3. CAPA DE ADAPTACIÓN - Python]   (core/backend_native.py)
         │  - Carga `libmusic_engine.so` usando `ctypes.CDLL`.
         │  - Empaqueta/desempaqueta tipos: `ctypes.c_int32`, `POINTER(TrackC)`.
         ▼
[4. CAPA DE COMPUERTA - C/C++]     (core/engine/src/CApi.cpp)
         │  - Funciones `extern "C"` que anulan el Name Mangling de C++.
         │  - Localiza la instancia estática del motor: `g_engine->toggle_play()`.
         ▼
[5. CAPA DE CONTROL CENTRAL - C++] (core/engine/src/Engine.cpp)
            - Orquesta las Estructuras de Datos Avanzadas.
            - Envía los comandos al `AudioPlayer.cpp` (hardware miniaudio).
```

### A) FLUJO DESCENDENTE: Traza de Ejecución (Acción Play/Pause)

Cuando un usuario presiona la barra espaciadora en la interfaz, el evento atraviesa las 5 capas sin interrupciones. Aquí la traza exacta de código:

#### 1. Capa de Interfaz (`main.py` / `ui/player.py`)
El controlador de input detecta la pulsación y delega a la fachada (Bridge):
```python
# En InputController (core/input.py) o main.py
if event.key == "space":
    self.bridge.toggle_play()
```

#### 2. Capa de Fachada (`core/bridge.py`)
La fachada no procesa nada. Protege a la UI de conocer si el backend es Mock o C++.
```python
class MusicBridge:
    def __init__(self):
        # Inyección de dependencia transparente
        from core.backend_native import NativeBackend
        self.backend = NativeBackend()

    def toggle_play(self):
        self.backend.toggle_play()
```

#### 3. Capa de Adaptación (`core/backend_native.py`)
`ctypes` ejecuta el salto al binario de C. La configuración de `argtypes` garantiza la seguridad de memoria.
```python
class NativeBackend:
    def __init__(self):
        # Carga dinámica del archivo .so compilado
        self._lib = ctypes.CDLL("./core/engine/build/libmusic_engine.so")
        self._lib.engine_toggle_play.argtypes = []
        self._lib.engine_toggle_play.restype = None

    def toggle_play(self):
        self._lib.engine_toggle_play()  # ← SALTO AL BINARIO C++
```

#### 4. Capa de Compuerta Nativa (`core/engine/src/CApi.cpp`)
El hilo de ejecución abandona el Intérprete de Python (GIL) y entra en espacio nativo de ejecución. El bloque `extern "C"` captura la llamada sin mangling.
```cpp
#include "Engine.hpp"
#include <mutex>
#include <memory>

static std::unique_ptr<Engine> g_engine = nullptr;
static std::mutex g_api_mutex;

extern "C" {
    // La ABI plana de C asegura compatibilidad binaria perfecta
    void engine_toggle_play() {
        // Bloqueo mínimo para garantizar thread-safety en invocaciones C-API
        std::lock_guard<std::mutex> lock(g_api_mutex);
        if (g_engine) {
            g_engine->toggle_play();
        }
    }
}
```

#### 5. Capa de Control Central (`core/engine/src/Engine.cpp` -> `AudioPlayer.cpp`)
`Engine` transmite la petición al reproductor, el cual invierte atómicamente el estado compartido (`PlaybackState`), lo que afectará inmediatamente al `data_callback` de la tarjeta de sonido.
```cpp
// En Engine.cpp
void Engine::toggle_play() {
    audio_player->toggle_pause();
}

// En AudioPlayer.cpp
void AudioPlayer::toggle_pause() {
    // memory_order_acquire: asegura leer la versión más reciente en memoria caché
    bool current_state = shared_state->is_playing.load(std::memory_order_acquire);
    
    // memory_order_release: publica el cambio inmediatamente al hilo de audio (callback)
    shared_state->is_playing.store(!current_state, std::memory_order_release);
}
```

---

### B) FLUJO ASCENDENTE: Traza de Telemetría (Progreso y Espectro visual)

El bucle UI principal consulta el backend 60 veces por segundo para pintar barras y el tiempo.
**Regla crítica:** La recolección de telemetría debe ser "Wait-Free" (O(1) estricto). No pueden haber semáforos (`std::mutex`) compitiendo con el bucle de audio, o la música se entrecortará (glitches) y la UI tendrá latencia.

#### 1. Producción de Datos (El Hilo de Hardware en C++)
El Driver del Sistema Operativo invoca cíclicamente la función en `AudioPlayer.cpp`.
```cpp
// Este callback ocurre ~100 veces por segundo en un hilo del OS de muy alta prioridad
void AudioPlayer::data_callback(ma_device* pDevice, void* pOutput, const void* pInput, ma_uint32 frameCount) {
    auto* player = static_cast<AudioPlayer*>(pDevice->pUserData);
    
    // 1. Decodificar audio
    ma_decoder_read_pcm_frames(&player->decoder, pOutput, frameCount, &frames_read);
    
    // 2. Escribir telemetría al bus compartido de forma lock-free
    if (frames_read > 0) {
        // A) Actualizar ms
        double ms_added = (frames_read / player->state->sample_rate.load()) * 1000.0;
        double current_ms = player->state->progress_ms.load(std::memory_order_relaxed);
        player->state->progress_ms.store(current_ms + ms_added, std::memory_order_relaxed);
        
        // B) Alimentar el Spectrum Analyzer con las muestras de PCM crudo
        if (player->spectrum_analyzer) {
            player->spectrum_analyzer->push_samples(static_cast<float*>(pOutput), frames_read * 2);
        }
    }
}
```

#### 2. Extracción Plana (C-API -> ctypes)
El hilo principal de Python hace la petición de la telemetría a través del proxy.
```cpp
// En CApi.cpp
extern "C" {
    double engine_get_progress() {
        // Lectura directa atómica (sin locks) O(1)
        return g_engine ? g_engine->get_progress_ms() : 0.0;
    }

    // El buffer pre-alojado se rellena copiando la memoria directamente
    void engine_get_spectrum_bars(float* out_bars, int num_bars) {
        if (g_engine) {
            g_engine->fill_spectrum(out_bars, num_bars);
        }
    }
}
```

```python
# En backend_native.py
def get_progress(self) -> float:
    return self._lib.engine_get_progress()

def get_audio_bars(self, num_bars: int) -> list[float]:
    # Creamos un array continuo en memoria que C pueda escribir
    ArrayType = ctypes.c_float * num_bars
    bars_array = ArrayType()
    
    # Pasamos el puntero (byref). C escribirá encima O(1) memcopy
    self._lib.engine_get_spectrum_bars(ctypes.byref(bars_array), num_bars)
    
    # Casteamos la memoria C-like a lista de Python
    return list(bars_array)
```

#### 3. Renderizado Visual (UI de Textual)
`bridge.py` le entrega los flotantes crudos (`0.0` a `1.0`) a `ui/visualizer.py` donde los transforma en barras ASCII y repinta el Widget al instante.

---

## 1. Capa de Entidades Base

### `core/engine/include/Track.hpp`
Define la estructura básica de una pista de audio y la versión POD (Plain Old Data) para cruzar la frontera C/Python sin sobrecarga de serialización.

```cpp
#pragma once

#include <string>
#include <cstdint>

constexpr size_t MAX_STR_LEN = 512;

extern "C" {
    struct TrackC {
        int32_t id;
        char title[MAX_STR_LEN];
        char artist[MAX_STR_LEN];
        char album[MAX_STR_LEN];
        double duration;
        char path[MAX_STR_LEN];
        int32_t stars;
    };
}

class Track {
public:
    int32_t id;
    std::string title;
    std::string artist;
    std::string album;
    double duration;
    std::string path;
    int32_t stars;

    Track() : id(-1), duration(0.0), stars(1) {}

    Track(int32_t _id, std::string _title, std::string _artist, 
          std::string _album, double _duration, std::string _path, int32_t _stars)
        : id(_id), title(std::move(_title)), artist(std::move(_artist)),
          album(std::move(_album)), duration(_duration), path(std::move(_path)), stars(_stars) {}

    TrackC to_c_struct() const;
    int64_t get_acoustic_seed() const;
};
```

### `core/engine/src/Track.cpp`
```cpp
#include "Track.hpp"
#include <cstring>
#include <numeric>

TrackC Track::to_c_struct() const {
    TrackC c_track;
    c_track.id = this->id;
    c_track.duration = this->duration;
    c_track.stars = this->stars;

    std::strncpy(c_track.title, this->title.c_str(), MAX_STR_LEN - 1);
    c_track.title[MAX_STR_LEN - 1] = '\0';
    std::strncpy(c_track.artist, this->artist.c_str(), MAX_STR_LEN - 1);
    c_track.artist[MAX_STR_LEN - 1] = '\0';
    std::strncpy(c_track.album, this->album.c_str(), MAX_STR_LEN - 1);
    c_track.album[MAX_STR_LEN - 1] = '\0';
    std::strncpy(c_track.path, this->path.c_str(), MAX_STR_LEN - 1);
    c_track.path[MAX_STR_LEN - 1] = '\0';

    return c_track;
}

int64_t Track::get_acoustic_seed() const {
    std::string seed_str = title + "-" + artist + "-" + std::to_string(id);
    int64_t seed = 0;
    for (size_t i = 0; i < seed_str.length(); ++i) {
        seed += static_cast<int64_t>(seed_str[i]) * static_cast<int64_t>(i + 1);
    }
    return seed;
}
```

---

## 2. Estructuras de Datos Avanzadas

### `core/engine/include/DoublyLinkedList.hpp`
Lista Doblemente Enlazada genérica para la Cola de Reproducción bidireccional.

```cpp
#pragma once

#include <cstddef>

template <typename T>
struct Node {
    T data;
    Node* prev;
    Node* next;
    explicit Node(const T& val) : data(val), prev(nullptr), next(nullptr) {}
};

template <typename T>
class DoublyLinkedList {
private:
    Node<T>* head_node;
    Node<T>* tail_node;
    size_t list_size;

public:
    DoublyLinkedList() : head_node(nullptr), tail_node(nullptr), list_size(0) {}
    ~DoublyLinkedList() { clear(); }
    
    DoublyLinkedList(const DoublyLinkedList&) = delete;
    DoublyLinkedList& operator=(const DoublyLinkedList&) = delete;

    DoublyLinkedList(DoublyLinkedList&& other) noexcept 
        : head_node(other.head_node), tail_node(other.tail_node), list_size(other.list_size) {
        other.head_node = nullptr;
        other.tail_node = nullptr;
        other.list_size = 0;
    }

    void clear();
    void append(const T& value);
    Node<T>* get_head() const { return head_node; }
    Node<T>* get_tail() const { return tail_node; }
    size_t size() const { return list_size; }
    bool is_empty() const { return list_size == 0; }
    Node<T>* get_at_index(size_t index) const;
};
```

### `core/engine/src/DoublyLinkedList.cpp`
```cpp
#include "DoublyLinkedList.hpp"
#include "Track.hpp"

// Instanciación explícita para evitar linker errors en cabeceras dependientes
template class DoublyLinkedList<Track>;

template <typename T>
void DoublyLinkedList<T>::clear() {
    Node<T>* current = head_node;
    while (current != nullptr) {
        Node<T>* next_node = current->next;
        delete current;
        current = next_node;
    }
    head_node = nullptr;
    tail_node = nullptr;
    list_size = 0;
}

template <typename T>
void DoublyLinkedList<T>::append(const T& value) {
    Node<T>* new_node = new Node<T>(value);
    if (is_empty()) {
        head_node = new_node;
        tail_node = new_node;
    } else {
        tail_node->next = new_node;
        new_node->prev = tail_node;
        tail_node = new_node;
    }
    list_size++;
}

template <typename T>
Node<T>* DoublyLinkedList<T>::get_at_index(size_t index) const {
    if (index >= list_size) return nullptr;
    Node<T>* current = nullptr;
    if (index <= list_size / 2) {
        current = head_node;
        for (size_t i = 0; i < index; ++i) current = current->next;
    } else {
        current = tail_node;
        for (size_t i = list_size - 1; i > index; --i) current = current->prev;
    }
    return current;
}
```

---

## 3. Gestión de Biblioteca e Indexación O(1)

### `core/engine/include/LibraryManager.hpp`
Maneja base de datos de canciones con indexación `O(1)` usando `std::unordered_map` y paralelamente `std::vector` para iteración en orden.

```cpp
#pragma once
#include "Track.hpp"
#include <vector>
#include <unordered_map>
#include <string>
#include <mutex>
#include <atomic>

class LibraryManager {
private:
    std::string db_path;
    std::vector<Track> library_list;
    std::unordered_map<int32_t, Track> library_map;
    mutable std::mutex lib_mutex;
    std::atomic<int32_t> version{0};

public:
    explicit LibraryManager(std::string path);
    bool load_from_disk();
    bool save_to_disk();
    bool get_track_by_id(int32_t id, Track& out_track) const;
    bool update_rating(int32_t id, int32_t new_stars);
    std::vector<Track> get_all_tracks() const;
    int32_t get_version() const { return version.load(std::memory_order_relaxed); }
};
```

### `core/engine/src/LibraryManager.cpp`
```cpp
#include "LibraryManager.hpp"
#include <fstream>
#include <iostream>
#include "nlohmann/json.hpp" 

using json = nlohmann::json;

LibraryManager::LibraryManager(std::string path) : db_path(std::move(path)) {}

bool LibraryManager::load_from_disk() {
    std::lock_guard<std::mutex> lock(lib_mutex);
    std::ifstream file(db_path);
    if (!file.is_open()) return false;

    try {
        json j;
        file >> j;
        library_list.clear();
        library_map.clear();
        library_list.reserve(j.size());
        library_map.reserve(j.size());

        for (const auto& item : j) {
            Track t(
                item.value("id", -1), item.value("title", "Unknown"),
                item.value("artist", "Unknown"), item.value("album", "Unknown"),
                item.value("duration", 0.0), item.value("path", ""), item.value("stars", 1)
            );
            if (t.id != -1) {
                library_list.push_back(t);
                library_map.emplace(t.id, t);
            }
        }
        version.fetch_add(1, std::memory_order_release);
        return true;
    } catch (const json::exception&) {
        return false;
    }
}

bool LibraryManager::save_to_disk() {
    std::lock_guard<std::mutex> lock(lib_mutex);
    json j_array = json::array();
    for (const auto& t : library_list) {
        j_array.push_back({
            {"id", t.id}, {"title", t.title}, {"artist", t.artist},
            {"album", t.album}, {"duration", t.duration}, {"path", t.path}, {"stars", t.stars}
        });
    }
    std::ofstream file(db_path, std::ios::trunc);
    if (!file.is_open()) return false;
    file << j_array.dump(4);
    return true;
}

bool LibraryManager::get_track_by_id(int32_t id, Track& out_track) const {
    std::lock_guard<std::mutex> lock(lib_mutex);
    auto it = library_map.find(id);
    if (it != library_map.end()) {
        out_track = it->second;
        return true;
    }
    return false;
}

bool LibraryManager::update_rating(int32_t id, int32_t new_stars) {
    std::lock_guard<std::mutex> lock(lib_mutex);
    auto it = library_map.find(id);
    if (it == library_map.end()) return false;
    it->second.stars = new_stars;
    for (auto& t : library_list) {
        if (t.id == id) { t.stars = new_stars; break; }
    }
    version.fetch_add(1, std::memory_order_release);
    return true;
}

std::vector<Track> LibraryManager::get_all_tracks() const {
    std::lock_guard<std::mutex> lock(lib_mutex);
    return library_list;
}
```

---

## 4. Gestión de Cola de Reproducción y Random Ponderado

### `core/engine/include/QueueManager.hpp`
Lógica de reproducción secuencial vs. aleatoria. Algoritmo `Roulette Wheel Selection` (Muestreo ponderado de Alias) mediante `std::discrete_distribution`.

```cpp
#pragma once
#include "DoublyLinkedList.hpp"
#include "Track.hpp"
#include <vector>
#include <mutex>
#include <atomic>
#include <random>

class QueueManager {
private:
    DoublyLinkedList<Track> play_queue;
    Node<Track>* current_node;
    mutable std::mutex queue_mutex;
    std::atomic<bool> random_mode{false};
    std::atomic<int32_t> version{0};
    std::mt19937_64 rng;

    double calculate_weight(int32_t stars) const;

public:
    QueueManager();
    void generate_linear_queue(const std::vector<Track>& library);
    void generate_weighted_random_queue(const std::vector<Track>& library);
    void toggle_random_mode(const std::vector<Track>& library);
    bool is_random_mode() const { return random_mode.load(std::memory_order_relaxed); }
    
    bool next();
    bool previous();
    bool jump_to_index(size_t index);
    
    bool get_current_track(Track& out_track) const;
    int32_t get_current_index() const;
    int32_t get_version() const { return version.load(std::memory_order_relaxed); }
    void update_rating_in_queue(int32_t track_id, int32_t stars);
};
```

### `core/engine/src/QueueManager.cpp`
```cpp
#include "QueueManager.hpp"
#include <chrono>

QueueManager::QueueManager() : current_node(nullptr) {
    std::random_device rd;
    rng.seed(rd() ^ std::chrono::high_resolution_clock::now().time_since_epoch().count());
}

double QueueManager::calculate_weight(int32_t stars) const {
    int32_t s = std::max(1, std::min(5, stars));
    return static_cast<double>(s * (s + 1)) / 2.0;
}

void QueueManager::generate_linear_queue(const std::vector<Track>& library) {
    std::lock_guard<std::mutex> lock(queue_mutex);
    play_queue.clear();
    for (const auto& t : library) play_queue.append(t);
    current_node = play_queue.get_head();
    version.fetch_add(1, std::memory_order_release);
}

void QueueManager::generate_weighted_random_queue(const std::vector<Track>& library) {
    std::lock_guard<std::mutex> lock(queue_mutex);
    if (library.empty()) return;
    
    std::vector<Track> pool = library;
    std::vector<double> weights;
    weights.reserve(pool.size());
    for (const auto& t : pool) weights.push_back(calculate_weight(t.stars));
    
    play_queue.clear();
    size_t pool_size = pool.size();
    for (size_t i = 0; i < pool_size; ++i) {
        std::discrete_distribution<size_t> dist(weights.begin(), weights.end());
        size_t chosen_idx = dist(rng);
        play_queue.append(pool[chosen_idx]);
        pool.erase(pool.begin() + chosen_idx);
        weights.erase(weights.begin() + chosen_idx);
    }
    current_node = play_queue.get_head();
    version.fetch_add(1, std::memory_order_release);
}

void QueueManager::toggle_random_mode(const std::vector<Track>& library) {
    bool new_mode = !random_mode.load(std::memory_order_relaxed);
    if (new_mode) generate_weighted_random_queue(library);
    else generate_linear_queue(library);
    random_mode.store(new_mode, std::memory_order_release);
}

bool QueueManager::next() {
    std::lock_guard<std::mutex> lock(queue_mutex);
    if (!current_node) return false;
    current_node = current_node->next ? current_node->next : play_queue.get_head();
    return true;
}

bool QueueManager::previous() {
    std::lock_guard<std::mutex> lock(queue_mutex);
    if (!current_node) return false;
    current_node = current_node->prev ? current_node->prev : play_queue.get_tail();
    return true;
}

bool QueueManager::jump_to_index(size_t index) {
    std::lock_guard<std::mutex> lock(queue_mutex);
    Node<Track>* target = play_queue.get_at_index(index);
    if (target) { current_node = target; return true; }
    return false;
}

bool QueueManager::get_current_track(Track& out_track) const {
    std::lock_guard<std::mutex> lock(queue_mutex);
    if (current_node) { out_track = current_node->data; return true; }
    return false;
}

int32_t QueueManager::get_current_index() const {
    std::lock_guard<std::mutex> lock(queue_mutex);
    if (!current_node) return -1;
    int32_t idx = 0;
    Node<Track>* curr = play_queue.get_head();
    while (curr) {
        if (curr == current_node) return idx;
        idx++; curr = curr->next;
    }
    return -1;
}

void QueueManager::update_rating_in_queue(int32_t track_id, int32_t stars) {
    std::lock_guard<std::mutex> lock(queue_mutex);
    Node<Track>* curr = play_queue.get_head();
    while (curr) {
        if (curr->data.id == track_id) curr->data.stars = stars;
        curr = curr->next;
    }
    version.fetch_add(1, std::memory_order_release);
}
```

---

## 5. Subsistema de Audio y Estado Concurrente

### `core/engine/include/PlaybackState.hpp`
Buffers de variables modificadas atómicamente para proveer lecturas sin latencia y evitar el bloqueo mutuo entre el hilo de audio nativo y el main thread de Python.

```cpp
#pragma once
#include <atomic>

struct PlaybackState {
    std::atomic<double> progress_ms{0.0};
    std::atomic<bool> is_playing{false};
    std::atomic<bool> track_ended_flag{false};
    std::atomic<uint32_t> sample_rate{44100};
};
```

### `core/engine/include/SpectrumAnalyzer.hpp`
Transformación PCM a magnitudes frecuenciales.

```cpp
#pragma once
#include <vector>
#include <mutex>

class SpectrumAnalyzer {
private:
    std::vector<float> magnitudes;
    std::mutex spec_mutex;
public:
    SpectrumAnalyzer() : magnitudes(128, 0.0f) {}
    void push_samples(const float* pcm_data, size_t frame_count) {
        // Implementación Mock rápida para el pipeline
        std::lock_guard<std::mutex> lock(spec_mutex);
        for(size_t i=0; i < 128; ++i) {
            magnitudes[i] = (pcm_data && frame_count > 0) ? std::abs(pcm_data[i % frame_count]) : 0.0f;
        }
    }
    void fill_bars(float* out_array, int num_bars) {
        std::lock_guard<std::mutex> lock(spec_mutex);
        for(int i=0; i < num_bars; ++i) out_array[i] = magnitudes[i % 128];
    }
};
```

### `core/engine/include/AudioPlayer.hpp`
```cpp
#pragma once
#include "PlaybackState.hpp"
#include "SpectrumAnalyzer.hpp"
#include <string>
#include <memory>
#include "miniaudio.h"

class AudioPlayer {
private:
    ma_device device;
    ma_decoder decoder;
    bool is_device_init{false};
    bool is_decoder_init{false};
    
public:
    std::shared_ptr<PlaybackState> state;
    std::shared_ptr<SpectrumAnalyzer> spectrum_analyzer;

    static void data_callback(ma_device* pDevice, void* pOutput, const void* pInput, ma_uint32 frameCount);

    AudioPlayer(std::shared_ptr<PlaybackState> st, std::shared_ptr<SpectrumAnalyzer> spec);
    ~AudioPlayer();
    
    bool init();
    bool load_and_play(const std::string& filepath);
    void toggle_pause();
    void stop();
    void seek_to_start();
};
```

### `core/engine/src/AudioPlayer.cpp`
```cpp
#define MINIAUDIO_IMPLEMENTATION
#include "AudioPlayer.hpp"
#include <iostream>

void AudioPlayer::data_callback(ma_device* pDevice, void* pOutput, const void* pInput, ma_uint32 frameCount) {
    auto* player = static_cast<AudioPlayer*>(pDevice->pUserData);
    if (!player) return;
    auto st = player->state;

    if (!st->is_playing.load(std::memory_order_relaxed)) {
        size_t bytes = frameCount * ma_get_bytes_per_frame(pDevice->playback.format, pDevice->playback.channels);
        std::memset(pOutput, 0, bytes);
        return;
    }

    ma_uint64 frames_read = 0;
    ma_decoder_read_pcm_frames(&player->decoder, pOutput, frameCount, &frames_read);

    if (frames_read < frameCount) {
        st->is_playing.store(false, std::memory_order_release);
        st->track_ended_flag.store(true, std::memory_order_release);
    }

    uint32_t sr = st->sample_rate.load(std::memory_order_relaxed);
    if (frames_read > 0 && sr > 0) {
        double dt_ms = (static_cast<double>(frames_read) / sr) * 1000.0;
        double current = st->progress_ms.load(std::memory_order_relaxed);
        st->progress_ms.store(current + dt_ms, std::memory_order_relaxed);
        
        if (player->spectrum_analyzer) {
            player->spectrum_analyzer->push_samples(static_cast<float*>(pOutput), frames_read * 2);
        }
    }
}

AudioPlayer::AudioPlayer(std::shared_ptr<PlaybackState> st, std::shared_ptr<SpectrumAnalyzer> spec) 
    : state(std::move(st)), spectrum_analyzer(std::move(spec)) {}

AudioPlayer::~AudioPlayer() { stop(); }

bool AudioPlayer::init() {
    ma_device_config config = ma_device_config_init(ma_device_type_playback);
    config.playback.format = ma_format_f32;
    config.playback.channels = 2;
    config.sampleRate = 44100;
    config.dataCallback = data_callback;
    config.pUserData = this;
    
    if (ma_device_init(nullptr, &config, &device) != MA_SUCCESS) return false;
    
    state->sample_rate.store(device.sampleRate, std::memory_order_relaxed);
    is_device_init = true;
    ma_device_start(&device);
    return true;
}

bool AudioPlayer::load_and_play(const std::string& filepath) {
    if (is_decoder_init) { ma_decoder_uninit(&decoder); is_decoder_init = false; }
    state->is_playing.store(false, std::memory_order_release);
    state->track_ended_flag.store(false, std::memory_order_release);
    state->progress_ms.store(0.0, std::memory_order_release);

    ma_decoder_config dec_cfg = ma_decoder_config_init(ma_format_f32, device.playback.channels, device.sampleRate);
    if (ma_decoder_init_file(filepath.c_str(), &dec_cfg, &decoder) != MA_SUCCESS) return false;

    is_decoder_init = true;
    state->is_playing.store(true, std::memory_order_release);
    return true;
}

void AudioPlayer::toggle_pause() {
    bool current = state->is_playing.load(std::memory_order_acquire);
    state->is_playing.store(!current, std::memory_order_release);
}

void AudioPlayer::stop() {
    if (is_decoder_init) ma_decoder_uninit(&decoder);
    if (is_device_init) ma_device_uninit(&device);
    is_decoder_init = is_device_init = false;
}

void AudioPlayer::seek_to_start() {
    if (is_decoder_init) {
        ma_decoder_seek_to_pcm_frame(&decoder, 0);
        state->progress_ms.store(0.0, std::memory_order_release);
        state->is_playing.store(true, std::memory_order_release);
    }
}
```

---

## 6. Motor Central (Facade C++)

### `core/engine/include/Engine.hpp`
```cpp
#pragma once
#include "LibraryManager.hpp"
#include "QueueManager.hpp"
#include "AudioPlayer.hpp"
#include "PlaybackState.hpp"
#include "SpectrumAnalyzer.hpp"
#include <memory>
#include <thread>
#include <atomic>

class Engine {
private:
    std::unique_ptr<LibraryManager> library;
    std::unique_ptr<QueueManager> queue;
    std::unique_ptr<AudioPlayer> player;
    
    std::shared_ptr<PlaybackState> state;
    std::shared_ptr<SpectrumAnalyzer> spectrum;

    std::atomic<bool> supervisor_running{false};
    std::thread supervisor_thread;

    void supervisor_loop();
    void play_current();

public:
    Engine();
    ~Engine();

    bool init(const std::string& json_db_path);
    void shutdown();
    void play_next();
    void play_previous();
    void toggle_play();
    void toggle_random();
    void jump_to_index(int32_t index);
    void set_rating(int32_t track_id, int32_t stars);

    double get_progress_ms() const;
    bool is_playing() const;
    bool get_current_track(Track& out) const;
    void fill_spectrum(float* out_bars, int num_bars);
};
```

### `core/engine/src/Engine.cpp`
```cpp
#include "Engine.hpp"
#include <chrono>

Engine::Engine() {
    state = std::make_shared<PlaybackState>();
    spectrum = std::make_shared<SpectrumAnalyzer>();
    queue = std::make_unique<QueueManager>();
    player = std::make_unique<AudioPlayer>(state, spectrum);
}

Engine::~Engine() { shutdown(); }

bool Engine::init(const std::string& json_db_path) {
    library = std::make_unique<LibraryManager>(json_db_path);
    if (!library->load_from_disk()) return false;
    if (!player->init()) return false;

    queue->generate_linear_queue(library->get_all_tracks());
    
    supervisor_running.store(true, std::memory_order_release);
    supervisor_thread = std::thread(&Engine::supervisor_loop, this);
    return true;
}

void Engine::shutdown() {
    supervisor_running.store(false, std::memory_order_release);
    if (supervisor_thread.joinable()) supervisor_thread.join();
    player->stop();
}

void Engine::supervisor_loop() {
    while (supervisor_running.load(std::memory_order_relaxed)) {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        if (state->track_ended_flag.exchange(false, std::memory_order_acq_rel)) {
            play_next();
        }
    }
}

void Engine::play_current() {
    Track t;
    if (queue->get_current_track(t)) player->load_and_play(t.path);
}

void Engine::play_next() { if (queue->next()) play_current(); }

void Engine::play_previous() {
    if (get_progress_ms() > 3000.0) player->seek_to_start();
    else if (queue->previous()) play_current();
}

void Engine::toggle_play() { player->toggle_pause(); }

void Engine::toggle_random() { queue->toggle_random_mode(library->get_all_tracks()); }

void Engine::jump_to_index(int32_t index) {
    if (queue->jump_to_index(static_cast<size_t>(index))) play_current();
}

void Engine::set_rating(int32_t track_id, int32_t stars) {
    if (library->update_rating(track_id, stars)) {
        library->save_to_disk();
        queue->update_rating_in_queue(track_id, stars);
    }
}

double Engine::get_progress_ms() const { return state->progress_ms.load(std::memory_order_relaxed); }
bool Engine::is_playing() const { return state->is_playing.load(std::memory_order_relaxed); }
bool Engine::get_current_track(Track& out) const { return queue->get_current_track(out); }
void Engine::fill_spectrum(float* out_bars, int num_bars) { spectrum->fill_bars(out_bars, num_bars); }
```

---

## 7. Capa de Interoperabilidad (C-API)

### `core/engine/src/CApi.cpp`
Expone interfaz OPAQUE hacia Python. Elimina necesidad de compiladores de headers.

```cpp
#include "CApi.hpp"
#include "Engine.hpp"
#include "Track.hpp"
#include <memory>
#include <mutex>

static std::unique_ptr<Engine> g_engine = nullptr;
static std::mutex g_api_mutex;

extern "C" {

int32_t engine_init(const char* db_path) {
    std::lock_guard<std::mutex> lock(g_api_mutex);
    if (!g_engine) g_engine = std::make_unique<Engine>();
    return g_engine->init(std::string(db_path)) ? 0 : -1;
}

void engine_toggle_play() { std::lock_guard<std::mutex> lock(g_api_mutex); if(g_engine) g_engine->toggle_play(); }
void engine_play_next() { std::lock_guard<std::mutex> lock(g_api_mutex); if(g_engine) g_engine->play_next(); }
void engine_play_previous() { std::lock_guard<std::mutex> lock(g_api_mutex); if(g_engine) g_engine->play_previous(); }

double engine_get_progress() { return g_engine ? g_engine->get_progress_ms() / 1000.0 : 0.0; }
int32_t engine_is_playing() { return (g_engine && g_engine->is_playing()) ? 1 : 0; }

int32_t engine_get_current_track(TrackC* out) {
    if (!g_engine || !out) return 0;
    Track t;
    if (g_engine->get_current_track(t)) { *out = t.to_c_struct(); return 1; }
    return 0;
}

void engine_get_spectrum_bars(float* out_bars, int num_bars) {
    if(g_engine && out_bars) g_engine->fill_spectrum(out_bars, num_bars);
}
}
```

---

## 8. Adaptador Python y Compilación

### `core/backend_native.py`
Enlaza el framework de UI de Python (`ui/player.py`) con el backend `CApi.cpp`. 

```python
import ctypes
import os
from pathlib import Path

MAX_STR_LEN = 512

class TrackC(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_int32), ("title", ctypes.c_char * MAX_STR_LEN),
        ("artist", ctypes.c_char * MAX_STR_LEN), ("album", ctypes.c_char * MAX_STR_LEN),
        ("duration", ctypes.c_double), ("path", ctypes.c_char * MAX_STR_LEN),
        ("stars", ctypes.c_int32)
    ]

class NativeBackend:
    def __init__(self, db_path="library.json"):
        so_path = Path(__file__).parent / "engine/build/libmusic_engine.so"
        self._lib = ctypes.CDLL(str(so_path))
        
        # Configurar signatures para salvaguardas de memoria
        self._lib.engine_init.argtypes = [ctypes.c_char_p]
        self._lib.engine_get_progress.restype = ctypes.c_double
        self._lib.engine_get_current_track.argtypes = [ctypes.POINTER(TrackC)]
        self._lib.engine_get_spectrum_bars.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_int32]
        
        if self._lib.engine_init(db_path.encode('utf-8')) != 0:
            raise RuntimeError("Fallo inicializando motor C++")

    def toggle_play(self): self._lib.engine_toggle_play()
    def next_track(self): self._lib.engine_play_next()
    def prev_track(self): self._lib.engine_play_previous()
    
    @property
    def progress(self): return self._lib.engine_get_progress()
    
    @property
    def is_playing(self): return bool(self._lib.engine_is_playing())

    def get_audio_bars(self, num_bars: int) -> list[float]:
        ArrayType = ctypes.c_float * num_bars
        bars_array = ArrayType()
        self._lib.engine_get_spectrum_bars(ctypes.byref(bars_array), num_bars)
        return list(bars_array)

    def get_current_track(self):
        c_trk = TrackC()
        if self._lib.engine_get_current_track(ctypes.byref(c_trk)):
            from core.backend import Track
            return Track(c_trk.id, c_trk.title.decode(), c_trk.artist.decode(),
                         c_trk.album.decode(), c_trk.duration, c_trk.path.decode(), c_trk.stars)
        return None
```

### `core/engine/CMakeLists.txt`
```cmake
cmake_minimum_required(VERSION 3.16)
project(MusicEngine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_BUILD_TYPE Release)

include_directories(include third_party)

set(SOURCES
    src/Track.cpp src/DoublyLinkedList.cpp src/LibraryManager.cpp
    src/QueueManager.cpp src/AudioPlayer.cpp src/Engine.cpp src/CApi.cpp
)

add_library(music_engine SHARED ${SOURCES})

find_library(ALSA asound)
if(ALSA)
    target_link_libraries(music_engine pthread dl m ${ALSA})
else()
    target_link_libraries(music_engine pthread dl m)
endif()
```
