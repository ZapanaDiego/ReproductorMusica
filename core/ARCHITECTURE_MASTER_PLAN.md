# ARCHITECTURE MASTER PLAN
## Motor de Audio C++ para Reproductor Musical Híbrido (Python Textual + C++17/20)

---

## REGLA ARQUITECTÓNICA INMUTABLE
El flujo de datos debe ser estrictamente unidireccional:
`Textual UI Python` → `core/bridge.py` → `Módulo nativo C++ compilado` → `Estructuras/Motor`

---

## ÍNDICE ANALÍTICO Y ESTRUCTURA DE ARCHIVOS

1. [Capa de Entidades Base](#1-capa-de-entidades-base)
   - `core/engine/include/Track.hpp`
   - `core/engine/src/Track.cpp`
2. [Estructuras de Datos Avanzadas](#2-estructuras-de-datos-avanzadas)
   - `core/engine/include/DoublyLinkedList.hpp`
   - `core/engine/src/DoublyLinkedList.cpp`
3. [Gestión de Biblioteca e Indexación O(1)](#3-gestión-de-biblioteca-e-indexación-o1)
   - `core/engine/include/LibraryManager.hpp`
   - `core/engine/src/LibraryManager.cpp`
4. [Gestión de Cola de Reproducción y Random Ponderado](#4-gestión-de-cola-de-reproducción-y-random-ponderado)
   - `core/engine/include/QueueManager.hpp`
   - `core/engine/src/QueueManager.cpp`
5. [Subsistema de Audio y Estado Concurrente](#5-subsistema-de-audio-y-estado-concurrente)
   - `core/engine/include/PlaybackState.hpp` / `core/engine/src/PlaybackState.cpp`
   - `core/engine/include/AudioPlayer.hpp` / `core/engine/src/AudioPlayer.cpp`
   - `core/engine/include/SpectrumAnalyzer.hpp` / `core/engine/src/SpectrumAnalyzer.cpp`
6. [Motor Central (Facade C++)](#6-motor-central-facade-c)
   - `core/engine/include/Engine.hpp`
   - `core/engine/src/Engine.cpp`
7. [Capa de Interoperabilidad (C-API y Pybind11)](#7-capa-de-interoperabilidad-c-api-y-pybind11)
   - `core/engine/include/CApi.hpp` / `core/engine/src/CApi.cpp`
   - `core/engine/src/PybindBindings.cpp`
8. [Adaptador Python y Compilación](#8-adaptador-python-y-compilación)
   - `core/backend_native.py`
   - `core/engine/CMakeLists.txt`

---

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




## 1. Capa de Entidades Base

### `core/engine/include/Track.hpp`
Define la estructura básica de una pista de audio y la versión POD (Plain Old Data) para cruzar la frontera C/Python sin sobrecarga de serialización.

```cpp
#pragma once

#include <string>
#include <cstdint>

// Tamaño fijo para buffers estáticos en la interfaz C-API.
// Evita asignaciones dinámicas (malloc/new) en el paso de mensajes.
constexpr size_t MAX_STR_LEN = 512;

/**
 * @brief Estructura POD compatible con ctypes.
 * 
 * Alineación estándar de C. No contiene métodos virtuales, constructores 
 * complejos ni punteros inteligentes. Memoria 100% contigua.
 */
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

/**
 * @brief Entidad Track en C++ moderno.
 * 
 * Inmutable en su mayoría, excepto por la calificación (stars).
 */
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

    // Genera el struct POD para enviar a Python
    TrackC to_c_struct() const;

    // Calcula semilla acústica determinista
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

    // Uso seguro de strncpy forzando el terminador nulo para evitar desbordamientos
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
Implementación genérica robusta de Lista Doblemente Enlazada. Optimizada para inserciones O(1) en los extremos y saltos relativos eficientes, requerimiento fundamental para la cola de reproducción bidireccional.

```cpp
#pragma once

#include <cstddef>
#include <stdexcept>
#include <memory>

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

    // Prevención de memory leaks: Regla de los Tres (C++98) / Cinco (C++11)
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
    
    // Obtención O(n/2) optimizada
    Node<T>* get_at_index(size_t index) const;
};
```

### `core/engine/src/DoublyLinkedList.cpp`
```cpp
#include "DoublyLinkedList.hpp"

// Instanciación explícita para evitar errores de enlace (linker errors)
// dado que se usa en QueueManager con tipo Track
class Track; 
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
    if (index >= list_size) {
        return nullptr;
    }

    // Optimización de salto: buscar desde head o tail según cercanía
    Node<T>* current = nullptr;
    if (index <= list_size / 2) {
        current = head_node;
        for (size_t i = 0; i < index; ++i) {
            current = current->next;
        }
    } else {
        current = tail_node;
        for (size_t i = list_size - 1; i > index; --i) {
            current = current->prev;
        }
    }
    return current;
}
```

---

## 3. Gestión de Biblioteca e Indexación O(1)

### `core/engine/include/LibraryManager.hpp`
Maneja la base de datos de canciones. Usa `std::unordered_map` para garantizar O(1) en búsquedas por ID, mientras mantiene un `std::vector` paralelo para iteración ordenada O(n) y serialización determinista a JSON.

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
    std::vector<Track> library_list;                  // Orden secuencial preservado
    std::unordered_map<int32_t, Track> library_map;   // Indexación O(1) por ID
    
    mutable std::mutex lib_mutex;                     // Protege accesos a la librería
    std::atomic<int32_t> version{0};                  // Control de caché para la UI

public:
    explicit LibraryManager(std::string path);
    
    bool load_from_disk();
    bool save_to_disk();
    
    // Búsqueda O(1)
    bool get_track_by_id(int32_t id, Track& out_track) const;
    
    // Modificación
    bool update_rating(int32_t id, int32_t new_stars);
    
    // Acceso
    std::vector<Track> get_all_tracks() const;
    int32_t get_version() const { return version.load(std::memory_order_relaxed); }
};
```

### `core/engine/src/LibraryManager.cpp`
```cpp
#include "LibraryManager.hpp"
#include <fstream>
#include <iostream>
#include "nlohmann/json.hpp" // Header-only library for JSON

using json = nlohmann::json;

LibraryManager::LibraryManager(std::string path) : db_path(std::move(path)) {}

bool LibraryManager::load_from_disk() {
    std::lock_guard<std::mutex> lock(lib_mutex);
    
    std::ifstream file(db_path);
    if (!file.is_open()) {
        std::cerr << "[LibraryManager] Error: No se pudo abrir " << db_path << std::endl;
        return false;
    }

    try {
        json j;
        file >> j;
        
        library_list.clear();
        library_map.clear();
        
        // Reservar memoria previene realocaciones costosas
        library_list.reserve(j.size());
        library_map.reserve(j.size());

        for (const auto& item : j) {
            Track t(
                item.value("id", -1),
                item.value("title", "Unknown"),
                item.value("artist", "Unknown"),
                item.value("album", "Unknown"),
                item.value("duration", 0.0),
                item.value("path", ""),
                item.value("stars", 1)
            );
            
            // Si el ID es válido, insertar en ambas estructuras
            if (t.id != -1) {
                library_list.push_back(t);
                // emplace es más eficiente que insert/operator[] porque construye in-place
                library_map.emplace(t.id, t);
            }
        }
        
        version.fetch_add(1, std::memory_order_release);
        std::cout << "[LibraryManager] Cargadas " << library_list.size() << " pistas." << std::endl;
        return true;
        
    } catch (const json::exception& e) {
        std::cerr << "[LibraryManager] JSON Parse Error: " << e.what() << std::endl;
        return false;
    }
}

bool LibraryManager::save_to_disk() {
    std::lock_guard<std::mutex> lock(lib_mutex);
    
    json j_array = json::array();
    
    // Iteramos sobre la lista para preservar el orden original de inserción
    for (const auto& t : library_list) {
        json j_obj = {
            {"id", t.id},
            {"title", t.title},
            {"artist", t.artist},
            {"album", t.album},
            {"duration", t.duration},
            {"path", t.path},
            {"stars", t.stars}
        };
        j_array.push_back(j_obj);
    }
    
    std::ofstream file(db_path, std::ios::trunc);
    if (!file.is_open()) return false;
    
    file << j_array.dump(4); // Indentación de 4 espacios
    return true;
}

bool LibraryManager::get_track_by_id(int32_t id, Track& out_track) const {
    std::lock_guard<std::mutex> lock(lib_mutex);
    
    // O(1) lookup en unordered_map
    auto it = library_map.find(id);
    if (it != library_map.end()) {
        out_track = it->second;
        return true;
    }
    return false;
}

bool LibraryManager::update_rating(int32_t id, int32_t new_stars) {
    std::lock_guard<std::mutex> lock(lib_mutex);
    
    // 1. Actualizar Hash Map (O(1))
    auto it = library_map.find(id);
    if (it == library_map.end()) return false;
    it->second.stars = new_stars;
    
    // 2. Actualizar Vector Secuencial (O(n) pero necesario para sincronía)
    for (auto& t : library_list) {
        if (t.id == id) {
            t.stars = new_stars;
            break;
        }
    }
    
    version.fetch_add(1, std::memory_order_release);
    return true;
}

std::vector<Track> LibraryManager::get_all_tracks() const {
    std::lock_guard<std::mutex> lock(lib_mutex);
    return library_list; // Copia thread-safe
}
```

---

## 4. Gestión de Cola de Reproducción y Random Ponderado

### `core/engine/include/QueueManager.hpp`
Maneja la lógica de reproducción secuencial vs. aleatoria. Utiliza la clase `DoublyLinkedList` e implementa el algoritmo de Random Ponderado (`Roulette Wheel Selection`) usando `std::discrete_distribution`.

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
    
    std::mt19937_64 rng; // Generador Mersenne Twister 64-bit

    // Función matemática para cálculo de pesos: f(stars) = stars * (stars + 1) / 2
    double calculate_weight(int32_t stars) const;

public:
    QueueManager();
    
    void generate_linear_queue(const std::vector<Track>& library);
    void generate_weighted_random_queue(const std::vector<Track>& library);
    
    void toggle_random_mode(const std::vector<Track>& library);
    bool is_random_mode() const { return random_mode.load(std::memory_order_relaxed); }
    
    bool next();
    bool previous(bool force_prev = false); // force_prev ignora la lógica de "reiniciar canción > 3s"
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
    // Semilla criptográficamente segura o basada en tiempo de alta resolución
    std::random_device rd;
    rng.seed(rd() ^ std::chrono::high_resolution_clock::now().time_since_epoch().count());
}

double QueueManager::calculate_weight(int32_t stars) const {
    int32_t s = std::max(1, std::min(5, stars));
    return static_cast<double>(s * (s + 1)) / 2.0; // Números Triangulares
}

void QueueManager::generate_linear_queue(const std::vector<Track>& library) {
    std::lock_guard<std::mutex> lock(queue_mutex);
    play_queue.clear();
    
    for (const auto& t : library) {
        play_queue.append(t);
    }
    
    current_node = play_queue.get_head();
    version.fetch_add(1, std::memory_order_release);
}

void QueueManager::generate_weighted_random_queue(const std::vector<Track>& library) {
    std::lock_guard<std::mutex> lock(queue_mutex);
    
    if (library.empty()) return;
    
    std::vector<Track> pool = library;
    std::vector<double> weights;
    weights.reserve(pool.size());
    
    for (const auto& t : pool) {
        weights.push_back(calculate_weight(t.stars));
    }
    
    play_queue.clear();
    
    // Roulette Wheel Selection iterativa (Muestreo sin reemplazo ponderado)
    size_t pool_size = pool.size();
    for (size_t i = 0; i < pool_size; ++i) {
        std::discrete_distribution<size_t> dist(weights.begin(), weights.end());
        size_t chosen_idx = dist(rng);
        
        play_queue.append(pool[chosen_idx]);
        
        // Eliminar el elemento elegido para no repetirlo
        pool.erase(pool.begin() + chosen_idx);
        weights.erase(weights.begin() + chosen_idx);
    }
    
    current_node = play_queue.get_head();
    version.fetch_add(1, std::memory_order_release);
}

void QueueManager::toggle_random_mode(const std::vector<Track>& library) {
    bool current = random_mode.load(std::memory_order_relaxed);
    bool new_mode = !current;
    
    if (new_mode) {
        generate_weighted_random_queue(library);
    } else {
        generate_linear_queue(library);
    }
    
    random_mode.store(new_mode, std::memory_order_release);
}

bool QueueManager::next() {
    std::lock_guard<std::mutex> lock(queue_mutex);
    if (!current_node) return false;
    
    if (current_node->next) {
        current_node = current_node->next;
    } else {
        current_node = play_queue.get_head(); // Wrap around circular
    }
    return true;
}

bool QueueManager::previous(bool force_prev) {
    std::lock_guard<std::mutex> lock(queue_mutex);
    if (!current_node) return false;
    
    // La lógica de verificar si progress > 3.0s se maneja en AudioPlayer o Engine
    // Aquí solo saltamos al nodo anterior o hacemos wrap
    
    if (current_node->prev) {
        current_node = current_node->prev;
    } else {
        current_node = play_queue.get_tail();
    }
    return true;
}

bool QueueManager::jump_to_index(size_t index) {
    std::lock_guard<std::mutex> lock(queue_mutex);
    Node<Track>* target = play_queue.get_at_index(index);
    if (target) {
        current_node = target;
        return true;
    }
    return false;
}

bool QueueManager::get_current_track(Track& out_track) const {
    std::lock_guard<std::mutex> lock(queue_mutex);
    if (current_node) {
        out_track = current_node->data;
        return true;
    }
    return false;
}

int32_t QueueManager::get_current_index() const {
    std::lock_guard<std::mutex> lock(queue_mutex);
    if (!current_node) return -1;
    
    int32_t idx = 0;
    Node<Track>* curr = play_queue.get_head();
    while (curr) {
        if (curr == current_node) return idx;
        idx++;
        curr = curr->next;
    }
    return -1;
}

void QueueManager::update_rating_in_queue(int32_t track_id, int32_t stars) {
    std::lock_guard<std::mutex> lock(queue_mutex);
    Node<Track>* curr = play_queue.get_head();
    while (curr) {
        if (curr->data.id == track_id) {
            curr->data.stars = stars;
        }
        curr = curr->next;
    }
    version.fetch_add(1, std::memory_order_release);
}
```

---

## 5. Subsistema de Audio y Estado Concurrente

### `core/engine/include/PlaybackState.hpp`
Encapsula variables de estado modificadas concurrentemente por el callback de hardware y leídas sin lock por Python.

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

### `core/engine/include/AudioPlayer.hpp`
Usa `miniaudio.h` en arquitectura Pull. Opera enteramente sin locks en su loop principal.

```cpp
#pragma once

#include "PlaybackState.hpp"
#include <string>
#include <memory>
#include "miniaudio.h"

class AudioPlayer {
private:
    ma_device device;
    ma_decoder decoder;
    bool is_device_init{false};
    bool is_decoder_init{false};
    
    std::shared_ptr<PlaybackState> state;

    // Callback estático de miniaudio. Debe ser ultra-rápido.
    static void data_callback(ma_device* pDevice, void* pOutput, const void* pInput, ma_uint32 frameCount);

public:
    explicit AudioPlayer(std::shared_ptr<PlaybackState> shared_state);
    ~AudioPlayer();
    
    bool init();
    bool load_and_play(const std::string& filepath);
    void toggle_pause();
    void stop();
    
    // Fuerza un reseteo suave del decodificador (para "prev" cuando progress > 3s)
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

    // Si está pausado, rellenar el buffer de salida con ceros de forma eficiente.
    if (!st->is_playing.load(std::memory_order_relaxed)) {
        size_t bytes = frameCount * ma_get_bytes_per_frame(pDevice->playback.format, pDevice->playback.channels);
        std::memset(pOutput, 0, bytes);
        return;
    }

    ma_uint64 frames_read = 0;
    ma_decoder_read_pcm_frames(&player->decoder, pOutput, frameCount, &frames_read);

    // Detección de fin de pista
    if (frames_read < frameCount) {
        st->is_playing.store(false, std::memory_order_release);
        st->track_ended_flag.store(true, std::memory_order_release);
    }

    // Actualización O(1) lock-free del progreso
    uint32_t sr = st->sample_rate.load(std::memory_order_relaxed);
    if (frames_read > 0 && sr > 0) {
        double dt_ms = (static_cast<double>(frames_read) / sr) * 1000.0;
        double current = st->progress_ms.load(std::memory_order_relaxed);
        st->progress_ms.store(current + dt_ms, std::memory_order_release);
    }
}

AudioPlayer::AudioPlayer(std::shared_ptr<PlaybackState> shared_state) 
    : state(std::move(shared_state)) {}

AudioPlayer::~AudioPlayer() { stop(); }

bool AudioPlayer::init() {
    ma_device_config config = ma_device_config_init(ma_device_type_playback);
    config.playback.format = ma_format_f32;
    config.playback.channels = 2;
    config.sampleRate = 44100;
    config.dataCallback = data_callback;
    config.pUserData = this;
    
    if (ma_device_init(nullptr, &config, &device) != MA_SUCCESS) {
        return false;
    }
    
    state->sample_rate.store(device.sampleRate, std::memory_order_relaxed);
    is_device_init = true;
    ma_device_start(&device);
    return true;
}

bool AudioPlayer::load_and_play(const std::string& filepath) {
    if (is_decoder_init) {
        ma_decoder_uninit(&decoder);
        is_decoder_init = false;
    }

    state->is_playing.store(false, std::memory_order_release);
    state->track_ended_flag.store(false, std::memory_order_release);
    state->progress_ms.store(0.0, std::memory_order_release);

    ma_decoder_config dec_cfg = ma_decoder_config_init(ma_format_f32, device.playback.channels, device.sampleRate);
    if (ma_decoder_init_file(filepath.c_str(), &dec_cfg, &decoder) != MA_SUCCESS) {
        std::cerr << "[AudioPlayer] Error al cargar: " << filepath << std::endl;
        return false;
    }

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
    is_decoder_init = false;
    is_device_init = false;
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
Orquesta `LibraryManager`, `QueueManager` y `AudioPlayer`. Mantiene un hilo supervisor que auto-avanza de pista.

```cpp
#pragma once

#include "LibraryManager.hpp"
#include "QueueManager.hpp"
#include "AudioPlayer.hpp"
#include "PlaybackState.hpp"
#include <memory>
#include <thread>
#include <atomic>

class Engine {
private:
    std::unique_ptr<LibraryManager> library;
    std::unique_ptr<QueueManager> queue;
    std::unique_ptr<AudioPlayer> player;
    std::shared_ptr<PlaybackState> state;

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

    // Getters para C-API
    double get_progress_sec() const;
    bool is_playing() const;
    bool get_current_track(Track& out) const;
    int32_t get_queue_version() const;
    int32_t get_library_version() const;
    int32_t get_current_index() const;
};
```

### `core/engine/src/Engine.cpp`
```cpp
#include "Engine.hpp"
#include <chrono>

Engine::Engine() {
    state = std::make_shared<PlaybackState>();
    queue = std::make_unique<QueueManager>();
    player = std::make_unique<AudioPlayer>(state);
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
    if (supervisor_thread.joinable()) {
        supervisor_thread.join();
    }
    player->stop();
}

void Engine::supervisor_loop() {
    // Thread loop of low priority polling for track end
    while (supervisor_running.load(std::memory_order_relaxed)) {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        
        if (state->track_ended_flag.exchange(false, std::memory_order_acq_rel)) {
            play_next();
        }
    }
}

void Engine::play_current() {
    Track t;
    if (queue->get_current_track(t)) {
        player->load_and_play(t.path);
    }
}

void Engine::play_next() {
    if (queue->next()) play_current();
}

void Engine::play_previous() {
    double prog = get_progress_sec();
    if (prog > 3.0) {
        player->seek_to_start();
    } else {
        if (queue->previous()) play_current();
    }
}

void Engine::toggle_play() { player->toggle_pause(); }

void Engine::toggle_random() {
    queue->toggle_random_mode(library->get_all_tracks());
}

void Engine::jump_to_index(int32_t index) {
    if (queue->jump_to_index(static_cast<size_t>(index))) {
        play_current();
    }
}

void Engine::set_rating(int32_t track_id, int32_t stars) {
    if (library->update_rating(track_id, stars)) {
        library->save_to_disk();
        queue->update_rating_in_queue(track_id, stars);
    }
}

double Engine::get_progress_sec() const { return state->progress_ms.load() / 1000.0; }
bool Engine::is_playing() const { return state->is_playing.load(); }
bool Engine::get_current_track(Track& out) const { return queue->get_current_track(out); }
int32_t Engine::get_queue_version() const { return queue->get_version(); }
int32_t Engine::get_library_version() const { return library->get_version(); }
int32_t Engine::get_current_index() const { return queue->get_current_index(); }
```

---

## 7. Capa de Interoperabilidad (C-API y Pybind11)

### `core/engine/include/CApi.hpp` y `core/engine/src/CApi.cpp`
Expone funciones C planas (sin *name mangling*) consumibles vía `ctypes`. Actúa como Singleton contenedor de la instancia `Engine`.

```cpp
// CApi.cpp
#include "Engine.hpp"
#include "Track.hpp"
#include <memory>
#include <mutex>

static std::unique_ptr<Engine> g_engine = nullptr;
static std::mutex g_api_mutex;

extern "C" {

int32_t engine_init(const char* db_path) {
    std::lock_guard<std::mutex> lock(g_api_mutex);
    if (!g_engine) {
        g_engine = std::make_unique<Engine>();
    }
    return g_engine->init(std::string(db_path)) ? 0 : -1;
}

void engine_shutdown() {
    std::lock_guard<std::mutex> lock(g_api_mutex);
    if (g_engine) {
        g_engine->shutdown();
        g_engine.reset();
    }
}

void engine_play_next() { if(g_engine) g_engine->play_next(); }
void engine_play_previous() { if(g_engine) g_engine->play_previous(); }
void engine_toggle_play() { if(g_engine) g_engine->toggle_play(); }
void engine_toggle_random() { if(g_engine) g_engine->toggle_random(); }
void engine_jump_to_index(int32_t idx) { if(g_engine) g_engine->jump_to_index(idx); }
void engine_set_rating(int32_t id, int32_t s) { if(g_engine) g_engine->set_rating(id, s); }

double engine_get_progress() { return g_engine ? g_engine->get_progress_sec() : 0.0; }
int32_t engine_is_playing() { return (g_engine && g_engine->is_playing()) ? 1 : 0; }

int32_t engine_get_current_track(TrackC* out) {
    if (!g_engine || !out) return 0;
    Track t;
    if (g_engine->get_current_track(t)) {
        *out = t.to_c_struct();
        return 1;
    }
    return 0;
}

void engine_get_versions(int32_t* q_ver, int32_t* l_ver) {
    if (!g_engine) return;
    if (q_ver) *q_ver = g_engine->get_queue_version();
    if (l_ver) *l_ver = g_engine->get_library_version();
}

int32_t engine_get_current_index() {
    return g_engine ? g_engine->get_current_index() : -1;
}

} // extern "C"
```

---

## 8. Adaptador Python y Compilación

### `core/backend_native.py`
Reemplazo directo de `backend.py`. Define estructuras `ctypes` y expone métodos idénticos.

```python
import ctypes
import os
from pathlib import Path

MAX_STR_LEN = 512

class TrackC(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_int32),
        ("title", ctypes.c_char * MAX_STR_LEN),
        ("artist", ctypes.c_char * MAX_STR_LEN),
        ("album", ctypes.c_char * MAX_STR_LEN),
        ("duration", ctypes.c_double),
        ("path", ctypes.c_char * MAX_STR_LEN),
        ("stars", ctypes.c_int32),
    ]

class Track:
    # (El mismo objeto Track que en backend.py para no romper UI)
    def __init__(self, id, title, artist, album, duration, path, stars=1):
        self.id = id; self.title = title; self.artist = artist
        self.album = album; self.duration = duration; self.path = path; self.stars = stars

class NativeBackend:
    def __init__(self, db_path="library.json"):
        so_path = Path(__file__).parent / "engine/build/libmusic_engine.so"
        self.lib = ctypes.CDLL(str(so_path))
        
        # Configurar signatures
        self.lib.engine_init.argtypes = [ctypes.c_char_p]
        self.lib.engine_get_progress.restype = ctypes.c_double
        self.lib.engine_get_current_track.argtypes = [ctypes.POINTER(TrackC)]
        
        if self.lib.engine_init(db_path.encode('utf-8')) != 0:
            raise RuntimeError("Fallo inicializando motor C++")

    # Adaptadores que puentean directamente a ctypes...
    def play(self): self.lib.engine_toggle_play()
    def pause(self): self.lib.engine_toggle_play()
    def toggle_play(self): self.lib.engine_toggle_play()
    def next_track(self): self.lib.engine_play_next()
    def prev_track(self): self.lib.engine_play_previous()
    
    @property
    def progress(self): return self.lib.engine_get_progress()
    
    @property
    def is_playing(self): return bool(self.lib.engine_is_playing())

    def get_current_track(self):
        c_trk = TrackC()
        if self.lib.engine_get_current_track(ctypes.byref(c_trk)):
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

# Incluir headers
include_directories(include third_party)

# Ficheros fuente
set(SOURCES
    src/Track.cpp
    src/DoublyLinkedList.cpp
    src/LibraryManager.cpp
    src/QueueManager.cpp
    src/AudioPlayer.cpp
    src/Engine.cpp
    src/CApi.cpp
)

# Compilar Shared Library
add_library(music_engine SHARED ${SOURCES})

# Enlace de librerías del SO
find_library(ALSA asound)
if(ALSA)
    target_link_libraries(music_engine pthread dl m ${ALSA})
else()
    # Miniaudio falla gracefully o usa Pulse si asound no está.
    target_link_libraries(music_engine pthread dl m)
endif()
```
