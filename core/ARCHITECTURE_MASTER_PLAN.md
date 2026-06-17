# ARCHITECTURE MASTER PLAN v2.0
## Motor de Audio C++ para Reproductor Musical Híbrido (Python Textual + C++17)
**Última revisión:** Sprint 3.5 completado — Fase Python 100% funcional  
**Próxima fase:** Migración del `MockBackend` al motor nativo en C++

---

## ÍNDICE
1. [Diagnóstico de la Arquitectura Actual (Hybrid-Ready)](#1-diagnóstico-de-la-arquitectura-actual)
2. [Árbol de Directorios Futuro](#2-árbol-de-directorios-futuro)
3. [Mapeo de Estructuras de Datos Académicas](#3-mapeo-de-estructuras-de-datos-académicas)
4. [Especificación de Clases y Métodos en C++](#4-especificación-de-clases-y-métodos-en-c)
5. [Plan de Implementación Paso a Paso](#5-plan-de-implementación-paso-a-paso)
6. [Contrato de la C-API (Tabla de Funciones Exportadas)](#6-contrato-de-la-c-api)

---

## 1. Diagnóstico de la Arquitectura Actual

### 1.1 Estado Real del Prototipo Python

El sistema Python está completamente operativo y desacoplado en tres capas claramente separadas. El flujo de datos tiene **una sola dirección descendente** para comandos y **una sola dirección ascendente** para estado:

```
┌─────────────────────────────────────────────────────────────────┐
│  CAPA 1: UI ASÍNCRONA (Textual Event Loop — Hilo Principal)     │
│                                                                 │
│  main.py ──► MusicPlayerApp                                     │
│    • on_key()  →  input.py (InputController)                    │
│    • update_ui() cada 0.1s  →  lee estado del bridge            │
│    • push_screen(AlbumInputModal) para diálogos                 │
│                                                                 │
│  ui/views.py     → DataTable (Library, Queue, Albums)           │
│  ui/player.py    → PlayerBottomBar (ProgressBar + tiempo)       │
│  ui/info_panel.py→ 4 zonas: Header/Meta/Playback/Shortcuts      │
│  ui/visualizer.py→ CavaVisualizer (barras espectrales)          │
│  ui/modals.py    → AlbumInputModal (ModalScreen[str])           │
└────────────────────────┬────────────────────────────────────────┘
                         │  Llamadas de método directas (sin bus)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  CAPA 2: FACHADA (Facade Pattern — core/bridge.py)             │
│                                                                 │
│  MusicBridge  ←── ÚNICA interfaz que la UI conoce              │
│  • __init__(current_user) → inyecta usuario en MockBackend      │
│  • play() / pause() / toggle_play() / next() / prev()           │
│  • get_current_track() / get_progress() / is_playing()          │
│  • get_library() / get_queue() / get_queue_version()            │
│  • toggle_random() / set_rating() / play_selection()            │
│  • create_album() / add_track_to_album() / remove_album()       │
│  • get_audio_bars(num_bars) / get_acoustic_dna()                │
│                                                                 │
│  CONTRATO INMUTABLE: La UI nunca importa MockBackend.           │
│  Cuando se cambie backend.py por C++, CERO cambios en la UI.   │
└────────────────────────┬────────────────────────────────────────┘
                         │  self.backend.method()
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  CAPA 3: NÚCLEO DE NEGOCIO (core/backend.py — Hilo de Audio)   │
│                                                                 │
│  MockBackend                                                    │
│  Estado:                                                        │
│    • library: list[Track]          → std::vector futuro         │
│    • queue: list[Track]            → DoublyLinkedList futuro    │
│    • current_index: int            → puntero al nodo actual     │
│    • is_playing: bool              → std::atomic<bool> futuro   │
│    • is_paused: bool               → flag de reanudación        │
│    • progress: float               → segundos transcurridos     │
│    • current_user: dict            → struct User futuro         │
│                                                                 │
│  Hilos:                                                         │
│    • _playback_loop (daemon)       → bucle cada 50ms            │
│      - acumula dt con time.time()                               │
│      - detecta fin con pygame.mixer.music.get_busy()            │
│      - llama _next_track_locked() bajo threading.Lock           │
│    • CavaSubprocess (daemon)       → lee barras espectrales      │
│                                                                 │
│  Audio:                                                         │
│    • Pygame (SDL_VIDEODRIVER=dummy para terminal)               │
│    • Mutagen: lee duración exacta de VBR MP3 en scan            │
│                                                                 │
│  Persistencia:                                                  │
│    • library.json: lista de pistas con metadatos                │
│    • users_db.json: usuarios + liked_tracks + liked_albums      │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Por qué el Facade Pattern hace la migración segura

El `MusicBridge` actúa como **firewall contractual**. En este momento su `__init__` contiene:

```python
# core/bridge.py — línea 25 (actual)
self.backend = MockBackend(current_user)
```

Para migrar al motor C++, esa línea se convierte en:

```python
# core/bridge.py — línea 25 (post-migración)
from core.backend_native import NativeBackend
self.backend = NativeBackend(current_user)
```

**Eso es todo el cambio en Python.** La UI nunca sabrá que el backend cambió porque el `MusicBridge` garantiza que `NativeBackend` exponga exactamente los mismos atributos y métodos que `MockBackend`.

### 1.3 Contratos actuales del MockBackend que NativeBackend debe respetar

| Atributo/Método Python | Tipo | Notas para C++ |
|---|---|---|
| `backend.library` | `list[Track]` | Vector de structs exportado vía snapshot |
| `backend.queue` | `list[Track]` | Snapshot de la DLL exportado en cada tick |
| `backend.current_index` | `int` | Índice del nodo actual en la DLL |
| `backend.is_playing` | `bool` | `std::atomic<bool>` en el estado compartido |
| `backend.is_paused` | `bool` | Flag de pausa separado para no confundir con stop |
| `backend.progress` | `float` | Segundos acumulados, consultado en cada tick |
| `backend.queue_version` | `int` | Contador atómico incrementado al regenerar la cola |
| `backend.library_version` | `int` | Contador atómico incrementado al actualizar ratings |
| `backend.is_random_mode` | `bool` | Estado de modo aleatorio ponderado |
| `backend.current_user` | `dict` | Datos del usuario activo (id, name, liked_albums) |
| `backend.toggle_play()` | `None` | Alterna entre play y pause |
| `backend.next_track()` | `None` | Siguiente en la DLL |
| `backend.prev_track()` | `None` | Anterior en la DLL (si progress > 3s, reinicia) |
| `backend.jump_to_queue_index(i)` | `None` | Salta al nodo i de la DLL |
| `backend.generate_queue()` | `None` | Reconstruye la cola (random ponderado o secuencial) |
| `backend.toggle_random()` | `bool` | Alterna modo, regenera cola, retorna estado |
| `backend.set_rating(id, stars)` | `None` | Actualiza rating en library + queue + JSON |
| `backend.play_selection(tab, row)` | `None` | Reproduce por fila de tabla |
| `backend.rate_selection(tab, row, stars)` | `None` | Califica por fila de tabla |
| `backend.get_current_track()` | `Track\|None` | Nodo actual de la DLL como objeto Python |
| `backend.get_audio_bars(n)` | `list[float]` | n barras espectrales [0.0, 1.0] |
| `backend.get_acoustic_dna()` | `dict` | Semilla, perfil, color ambiental de la pista |
| `backend.get_directories()` | `list[dict]` | Directorios escaneados y si existen |
| `backend.create_album(name)` | `bool` | Crea álbum vacío en JSON del usuario |
| `backend.add_track_to_album(name, id)` | `bool` | Añade id a la lista del álbum |
| `backend.get_albums_summary()` | `list[dict]` | `[{name, count}]` de todos los álbumes |
| `backend.get_album_tracks(name)` | `list[Track]` | Objetos Track reales del álbum |
| `backend.remove_album(name)` | `bool` | Elimina álbum del JSON |
| `backend.remove_track_from_album(name, id)` | `bool` | Elimina id del álbum en JSON |
| `backend.like_track(id)` | `bool` | Añade/quita de liked_tracks |
| `backend.get_active_user_name()` | `str` | Nombre del usuario activo |

---

## 2. Árbol de Directorios Futuro

```
vercion02/
├── main.py                          ← SIN CAMBIOS (Textual App)
├── styles.tcss                      ← SIN CAMBIOS
├── library.json                     ← Generado por LibraryManager C++
├── app.log                          ← SIN CAMBIOS
│
├── ui/                              ← SIN CAMBIOS (bloque sellado)
│   ├── __init__.py
│   ├── views.py
│   ├── player.py
│   ├── visualizer.py
│   ├── info_panel.py
│   └── modals.py
│
└── core/
    ├── __init__.py
    ├── input.py                     ← SIN CAMBIOS
    ├── logger.py                    ← SIN CAMBIOS
    ├── cava.py                      ← SIN CAMBIOS (subproceso CAVA)
    ├── user_manager.py              ← SIN CAMBIOS (CLI pre-Textual)
    │
    ├── bridge.py                    ← [MODIFICAR] 1 línea: self.backend = NativeBackend()
    │
    ├── backend.py                   ← [DEPRECAR] Mantener como fallback en desarrollo
    │
    ├── backend_native.py            ← [NUEVO] Adaptador Python → C++
    │   # Usa ctypes para cargar libmusic_engine.so
    │   # Expone los mismos atributos que MockBackend
    │   # Convierte structs C a objetos Track Python
    │
    ├── database/
    │   └── users_db.json            ← Gestionado por UserManager C++
    │
    └── engine/                      ← Motor C++ (compilado a .so)
        ├── CMakeLists.txt           ← [IMPLEMENTAR] Script de build
        ├── README_ENGINE.md
        │
        ├── third_party/
        │   ├── miniaudio.h          ← YA PRESENTE. Audio sin dependencias.
        │   └── nlohmann/
        │       └── json.hpp         ← YA PRESENTE. Parser JSON header-only.
        │
        ├── include/                 ← Cabeceras (esqueletos YA creados)
        │   ├── Track.hpp            ← [COMPLETAR] struct TrackC + class Track
        │   ├── DoublyLinkedList.hpp ← [IMPLEMENTAR] template DLL
        │   ├── QueueManager.hpp     ← [IMPLEMENTAR] cola ponderada
        │   ├── LibraryManager.hpp   ← [IMPLEMENTAR] hash map + scan
        │   ├── AudioPlayer.hpp      ← [IMPLEMENTAR] abstracción miniaudio
        │   ├── SpectrumAnalyzer.hpp ← [IMPLEMENTAR] FFT simple
        │   ├── PlaybackState.hpp    ← [IMPLEMENTAR] atomics compartidos
        │   ├── Engine.hpp           ← [IMPLEMENTAR] fachada C++
        │   └── CApi.hpp             ← [IMPLEMENTAR] extern "C" declaraciones
        │
        ├── src/                     ← Implementaciones (todos vacíos, pendientes)
        │   ├── Track.cpp
        │   ├── DoublyLinkedList.cpp
        │   ├── QueueManager.cpp
        │   ├── LibraryManager.cpp
        │   ├── AudioPlayer.cpp
        │   ├── SpectrumAnalyzer.cpp
        │   ├── PlaybackState.cpp
        │   ├── Engine.cpp
        │   ├── CApi.cpp
        │   └── PybindBindings.cpp  ← Alternativa a ctypes (opcional)
        │
        └── build/                  ← [GENERADO por CMake, en .gitignore]
            └── libmusic_engine.so  ← Binario final que carga backend_native.py
```

### Archivos que desaparecen en Fase Final

| Archivo | Destino |
|---|---|
| `core/backend.py` (MockBackend) | Reemplazado por `core/backend_native.py` + `libmusic_engine.so` |
| `pygame` (dependencia) | Reemplazado por `miniaudio.h` en C++ |
| `mutagen` (dependencia) | Reemplazado por parsing de metadatos ID3 en C++ con `miniaudio` |
| `CavaSubprocess` | Reemplazado por `SpectrumAnalyzer` con FFT sobre buffer PCM real |

---

## 3. Mapeo de Estructuras de Datos Académicas

### 3.1 Entidad: Track

**Python actual:**
```python
class Track:
    id: int; title: str; artist: str; album: str
    duration: float; path: str; stars: int
```

**C++ futuro:**
```cpp
// include/Track.hpp
struct Track {
    int32_t     id;
    std::string title;
    std::string artist;
    std::string album;
    double      duration;    // segundos exactos de Mutagen/miniaudio
    std::string path;
    int32_t     stars;       // 1, 2, 3
};

// Para el cruce de frontera ctypes (ABI plana, sin vtable):
struct TrackC {
    int32_t id;
    char    title[256];
    char    artist[256];
    char    album[128];
    double  duration;
    char    path[512];
    int32_t stars;
};
```

**Razón de la doble representación:** `Track` (con `std::string`) es la estructura interna de C++ con todas las comodidades del lenguaje. `TrackC` es la estructura "aplanada" (POD — Plain Old Data) que ctypes puede leer directamente desde Python sin conversión. La C-API serializa `Track` → `TrackC` antes de enviarlo a Python.

---

### 3.2 Gestión de Biblioteca: `LibraryManager`

**Python actual:** `self.library = []` (lista Python simple, acceso O(n))

**C++ diseño:**

```
ESTRUCTURA PRINCIPAL:  std::vector<Track>  (índice posicional para la UI)
ÍNDICE POR ID:         std::unordered_map<int32_t, size_t>  → O(1) búsqueda por ID
ÍNDICE POR TÍTULO:     std::multimap<std::string, size_t>   → O(log n) ordenación
```

**¿Por qué vector + índice en lugar de árbol puro?**

La UI necesita acceso posicional `library[row]` para mapear filas de la `DataTable` a tracks. Un árbol AVL puro no tiene índice posicional sin recorrido in-order O(n). La solución híbrida mantiene el vector como almacén principal y el `unordered_map` como índice de búsqueda rápida:

```cpp
class LibraryManager {
    std::vector<Track>                       library;      // O(1) acceso por posición
    std::unordered_map<int32_t, size_t>      id_index;     // O(1) búsqueda por ID
    std::multimap<std::string, size_t>       title_index;  // O(log n) ordenación

public:
    // Carga desde library.json usando nlohmann::json
    bool load_from_json(const std::string& path);
    
    // Escanea ~/Música o ~/Music y llena la biblioteca
    void scan_directories(const std::vector<std::string>& paths);
    
    // O(1) por ID gracias al índice hash
    Track* find_by_id(int32_t id);
    
    // Acceso posicional para la UI (row → track)
    Track* at(size_t index);
    size_t size() const;
    
    // Actualiza rating en memoria Y persiste en library.json
    bool set_rating(int32_t track_id, int32_t stars);
    
    void save_to_json(const std::string& path);
    
    // Snapshot para enviar a Python: serializa a vector<TrackC>
    std::vector<TrackC> get_snapshot() const;
};
```

---

### 3.3 Cola de Reproducción: `PlaybackQueue` (Lista Doblemente Enlazada)

**Python actual:** `self.queue = list(self.library)` o lista barajada. Navegación O(1) en lista Python (pero no es DLL real).

**C++ diseño — Lista Doblemente Enlazada Académica:**

```cpp
// include/DoublyLinkedList.hpp
template <typename T>
struct DLLNode {
    T           data;
    DLLNode<T>* prev;
    DLLNode<T>* next;

    explicit DLLNode(T val) : data(std::move(val)), prev(nullptr), next(nullptr) {}
};

template <typename T>
class DoublyLinkedList {
    DLLNode<T>* head;
    DLLNode<T>* tail;
    DLLNode<T>* current;   // puntero al nodo en reproducción
    size_t      _size;

public:
    DoublyLinkedList();
    ~DoublyLinkedList();

    void push_back(T item);       // O(1) — añadir al final
    void clear();                 // O(n) — libera memoria

    // Navegación O(1) — solo mover el puntero
    T*   current_item();          // nodo activo
    bool move_next();             // avanza, wraps al head si llega al tail
    bool move_prev();             // retrocede, wraps al tail si llega al head
    bool jump_to_index(size_t i); // O(n) — necesario para "clic en fila"
    
    size_t current_index() const;
    size_t size() const;
    
    // Snapshot para Python (no expone punteros)
    std::vector<T> to_vector() const;
};
```

**Clase de gestión de alto nivel:**

```cpp
// include/QueueManager.hpp
class QueueManager {
    DoublyLinkedList<Track> queue;
    bool   is_random_mode;
    size_t queue_version;

public:
    // Construye la cola a partir de la biblioteca
    // Modo secuencial: copia directa
    // Modo random: pool ponderado por estrellas (★=1x, ★★=3x, ★★★=6x) + shuffle
    void generate(const std::vector<Track>& library);
    
    bool toggle_random(const std::vector<Track>& library);
    bool get_random_mode() const;
    
    Track*  current_track();
    bool    advance();             // siguiente → O(1)
    bool    retreat();             // anterior → O(1)
    bool    jump_to(size_t index); // salto directo → O(n)
    
    size_t  get_version() const;
    size_t  size() const;
    size_t  current_index() const;
    
    std::vector<TrackC> get_snapshot() const;
};
```

**Ventaja académica de la DLL:** `advance()` y `retreat()` son O(1) porque solo mueven el puntero `current`. No hay copia de datos, no hay reallocation. En Python, `list` usaba acceso por índice entero con `self.current_index`, lo cual es funcionalmente equivalente pero sin semántica de nodo.

---

### 3.4 Gestión de Usuarios: `UserManager`

**Python actual:** `current_user` es un `dict` Python con `liked_albums` como `dict[str, list[int]]`.

**C++ diseño:**

```cpp
// Estructura base del usuario
struct User {
    int32_t                                              id;
    std::string                                          name;
    std::vector<int32_t>                                 liked_tracks;
    std::unordered_map<std::string, std::vector<int32_t>> liked_albums;
    // Album name → vector de track IDs
    // unordered_map: O(1) lookup por nombre de álbum
    // vector interno: preserva orden de inserción
};

class UserManager {
    std::unordered_map<int32_t, User> users_table; // O(1) búsqueda por ID
    User* active_user;
    std::string db_path;

public:
    bool load_from_json(const std::string& path);
    bool save_to_json();
    
    std::vector<std::string> get_user_names() const;
    bool set_active_user(int32_t id);
    
    std::string get_active_name() const;
    
    // Gestión de álbumes del usuario activo
    bool create_album(const std::string& name);
    bool remove_album(const std::string& name);
    bool add_track_to_album(const std::string& album, int32_t track_id);
    bool remove_track_from_album(const std::string& album, int32_t track_id);
    
    // Retorna vector de {name, count} pares
    std::vector<std::pair<std::string, size_t>> get_albums_summary() const;
    
    // Retorna IDs de pistas del álbum (el Engine resuelve los objetos Track)
    std::vector<int32_t> get_album_track_ids(const std::string& album) const;
    
    bool like_track(int32_t track_id);
    bool is_track_liked(int32_t track_id) const;
};
```

**Elección de `std::unordered_map<int32_t, User>` para la tabla de usuarios:**  
Con un máximo de 5 usuarios, el beneficio de la tabla hash es mínimo en la práctica, pero sí cumple el contrato académico de búsqueda O(1) amortizado. Si la app escala a cientos de usuarios, el comportamiento se mantiene. Un `std::map` ordenado daría O(log n) sin razón en este contexto.

---

### 3.5 Estado de Reproducción: `PlaybackState` (Compartido entre hilos)

Este es el componente más crítico para la concurrencia. El hilo de audio de `miniaudio` (el `data_callback`) corre en contexto de alta prioridad y no puede tomar locks pesados. Toda comunicación usa **operaciones atómicas libres de bloqueo**:

```cpp
// include/PlaybackState.hpp
#include <atomic>
#include <cstdint>

struct PlaybackState {
    // Leídos/escritos por múltiples hilos — SIEMPRE atómicos
    std::atomic<bool>     is_playing{false};
    std::atomic<bool>     is_paused{false};
    std::atomic<double>   progress_seconds{0.0};
    std::atomic<int32_t>  current_track_id{-1};
    std::atomic<int32_t>  queue_version{0};
    std::atomic<int32_t>  library_version{0};
    std::atomic<bool>     track_ended_flag{false}; // señal del data_callback
    
    // Solo el hilo de control los escribe; solo los lee el data_callback:
    std::atomic<double>   current_duration{0.0};
};
```

**Protocolo de comunicación entre hilos:**
- El `data_callback` de miniaudio (hilo de audio) **solo lee** `is_playing` y `is_paused`.
- El `data_callback` **solo escribe** `track_ended_flag = true` cuando su buffer de datos se vacía.
- El hilo de control (`_playback_loop` equivalente) **lee** `track_ended_flag` cada 50ms y, si es `true`, lo resetea y llama a `QueueManager::advance()`.
- `progress_seconds` es acumulado por el hilo de control, no por el callback.

---

## 4. Especificación de Clases y Métodos en C++

### 4.1 `AudioPlayer` — Abstracción de miniaudio

```cpp
// include/AudioPlayer.hpp
#pragma once
#include "PlaybackState.hpp"
#include "Track.hpp"
#define MINIAUDIO_IMPLEMENTATION
#include "../third_party/miniaudio.h"
#include <string>
#include <functional>

class AudioPlayer {
    ma_engine    engine;       // motor de audio miniaudio (maneja el hilo)
    ma_sound     sound;        // sonido activo cargado
    bool         sound_loaded; // flag de guard para operaciones seguras
    
    PlaybackState* shared_state; // puntero al estado compartido (no dueño)

public:
    explicit AudioPlayer(PlaybackState* state);
    ~AudioPlayer();
    
    bool initialize();
    void shutdown();
    
    // Carga y reproduce un archivo de audio (MP3, WAV, OGG, FLAC)
    // Internamente: ma_engine_play_sound o ma_sound_init_from_file
    bool load_and_play(const std::string& path, double duration);
    
    // Pausa/reanuda sin reiniciar la posición
    void pause();
    void resume();
    void stop();
    
    // Consulta si el hardware aún está procesando audio
    bool is_hardware_busy() const;
    
    // Posición en segundos del cursor de audio (más preciso que Pygame)
    double get_position_seconds() const;
    
    // Obtiene la duración exacta del archivo (reemplaza a Mutagen)
    static double get_file_duration(const std::string& path);
};
```

**Nota sobre miniaudio vs Pygame:**
- miniaudio es una librería C de cabecera única (`miniaudio.h`). Ya está en `core/engine/third_party/`.
- `ma_sound_get_length_in_pcm_frames()` + sample rate = duración exacta en segundos, sin el bug VBR de Pygame.
- El `data_callback` de miniaudio no es necesario implementarlo manualmente para reproducción simple: `ma_engine` lo abstrae completamente.

---

### 4.2 `LibraryManager` — Gestor de Biblioteca

*(Ver sección 3.2 para el detalle completo de la clase)*

Métodos adicionales importantes:

```cpp
// Lectura de metadatos sin dependencia externa
// miniaudio puede leer ID3 tags básicos con ma_decoder
struct TrackMetadata {
    std::string title;
    std::string artist;
    std::string album;
    double      duration;
};

static TrackMetadata read_metadata(const std::string& path);
// Intenta: ID3v2 tags → ID3v1 tags → fallback al nombre de archivo
```

---

### 4.3 `Engine` — Fachada Central C++

`Engine` es el `MockBackend` de C++. Orquesta todos los managers y expone una interfaz coherente para la C-API.

```cpp
// include/Engine.hpp
#pragma once
#include "LibraryManager.hpp"
#include "QueueManager.hpp"
#include "AudioPlayer.hpp"
#include "UserManager.hpp"
#include "PlaybackState.hpp"
#include <thread>
#include <atomic>

class Engine {
    LibraryManager  library_mgr;
    QueueManager    queue_mgr;
    AudioPlayer     audio_player;
    UserManager     user_mgr;
    PlaybackState   state;
    
    // Hilo de control (equivalente a _playback_loop de Python)
    std::thread         control_thread;
    std::atomic<bool>   running{false};
    
    void _control_loop(); // corre cada 50ms; detecta fin de pista, acumula progreso

public:
    Engine();
    ~Engine();
    
    bool initialize(const std::string& library_path,
                    const std::string& users_db_path,
                    int32_t            active_user_id);
    void shutdown();
    
    // ── Controles de reproducción ─────────────────────────────────────
    void play();
    void pause();
    void toggle_play();
    void next_track();
    void prev_track();
    void jump_to_queue_index(int32_t index);
    
    // ── Estado de reproducción ────────────────────────────────────────
    const Track*   get_current_track() const;
    double         get_progress() const;
    bool           get_is_playing() const;
    bool           get_is_paused() const;
    int32_t        get_current_index() const;
    int32_t        get_queue_version() const;
    int32_t        get_library_version() const;
    
    // ── Biblioteca y cola ─────────────────────────────────────────────
    const std::vector<Track>& get_library() const;
    std::vector<TrackC>        get_library_snapshot() const;
    std::vector<TrackC>        get_queue_snapshot() const;
    bool                       toggle_random();
    bool                       get_random_mode() const;
    void                       set_rating(int32_t track_id, int32_t stars);
    void                       play_selection(const std::string& tab, int32_t row);
    
    // ── Espectro ──────────────────────────────────────────────────────
    // Genera barras espectrales matemáticas (mismo algoritmo que Python)
    std::vector<float> get_audio_bars(int32_t num_bars) const;
    
    // ── Gestión de usuarios ───────────────────────────────────────────
    std::string  get_active_user_name() const;
    bool         like_track(int32_t track_id);
    bool         create_album(const std::string& name);
    bool         remove_album(const std::string& name);
    bool         add_track_to_album(const std::string& album, int32_t track_id);
    bool         remove_track_from_album(const std::string& album, int32_t track_id);
    std::vector<std::pair<std::string,size_t>> get_albums_summary() const;
    std::vector<TrackC> get_album_tracks(const std::string& album) const;
};
```

---

### 4.4 `CApi` — Frontera Python/C++

Todas las funciones son `extern "C"` (ABI plana) para que ctypes pueda llamarlas sin descifrar el name mangling de C++. La instancia del Engine vive como singleton estático protegido por mutex.

```cpp
// include/CApi.hpp
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

// ── Ciclo de vida ─────────────────────────────────────────────────────
void  engine_init(const char* library_path, const char* users_db_path, int active_user_id);
void  engine_shutdown();

// ── Controles ────────────────────────────────────────────────────────
void  engine_play();
void  engine_pause();
void  engine_toggle_play();
void  engine_next();
void  engine_prev();
void  engine_jump_to_index(int index);

// ── Estado ───────────────────────────────────────────────────────────
// Llena el struct TrackC apuntado por out_track. Retorna 0 si no hay pista.
int   engine_get_current_track(struct TrackC* out_track);
double engine_get_progress();
int   engine_is_playing();
int   engine_is_paused();
int   engine_get_current_index();
int   engine_get_queue_version();
int   engine_get_library_version();

// ── Biblioteca y cola ─────────────────────────────────────────────────
// Llena out_tracks (array de TrackC de capacidad max_count). Retorna count real.
int   engine_get_library(struct TrackC* out_tracks, int max_count);
int   engine_get_queue(struct TrackC* out_tracks, int max_count);
int   engine_toggle_random();
void  engine_set_rating(int track_id, int stars);

// ── Espectro ──────────────────────────────────────────────────────────
// Llena out_bars con num_bars floats [0.0, 1.0].
void  engine_get_audio_bars(float* out_bars, int num_bars);

// ── Usuarios ──────────────────────────────────────────────────────────
void  engine_get_active_user_name(char* out_name, int max_len);
int   engine_like_track(int track_id);
int   engine_create_album(const char* name);
int   engine_remove_album(const char* name);
int   engine_add_track_to_album(const char* album, int track_id);
int   engine_remove_track_from_album(const char* album, int track_id);

// Llena out_pairs como array alternado: [name0, name1, ...] y out_counts como [count0, count1, ...]
int   engine_get_albums_summary(char** out_names, int* out_counts, int max_albums);
int   engine_get_album_tracks(const char* album, struct TrackC* out_tracks, int max_count);

#ifdef __cplusplus
}
#endif
```

---

### 4.5 `backend_native.py` — Adaptador Python

Este archivo es el único intermediario entre ctypes y el `MusicBridge`. Su responsabilidad es traducir tipos C a objetos Python.

```python
# core/backend_native.py
import ctypes
import os
from pathlib import Path

LIB_PATH = str(Path(__file__).parent / "engine" / "build" / "libmusic_engine.so")

# Struct Python espejo de TrackC en C++
class TrackC(ctypes.Structure):
    _fields_ = [
        ("id",       ctypes.c_int32),
        ("title",    ctypes.c_char * 256),
        ("artist",   ctypes.c_char * 256),
        ("album",    ctypes.c_char * 128),
        ("duration", ctypes.c_double),
        ("path",     ctypes.c_char * 512),
        ("stars",    ctypes.c_int32),
    ]

class Track:
    """Objeto Python compatible con el MockBackend.Track."""
    def __init__(self, c: TrackC):
        self.id       = c.id
        self.title    = c.title.decode("utf-8", errors="replace")
        self.artist   = c.artist.decode("utf-8", errors="replace")
        self.album    = c.album.decode("utf-8", errors="replace")
        self.duration = c.duration
        self.path     = c.path.decode("utf-8", errors="replace")
        self.stars    = c.stars

class NativeBackend:
    """
    Reemplazo exacto de MockBackend usando el motor C++.
    Expone los mismos atributos y métodos para que MusicBridge no cambie.
    """
    def __init__(self, current_user=None):
        self._lib = ctypes.CDLL(LIB_PATH)
        self._setup_argtypes()
        
        # Inicializar motor C++
        user_id = current_user["id"] if current_user else 0
        self._lib.engine_init(
            b"library.json",
            b"core/database/users_db.json",
            ctypes.c_int(user_id)
        )
        
        # Cache local de versiones para detectar cambios
        self._lib_version_cache  = -1
        self._queue_version_cache = -1
        self._library_cache      = []
        self._queue_cache        = []
        self.current_user        = current_user

    # ── Propiedades que imitan atributos del MockBackend ──────────────
    @property
    def is_playing(self): return bool(self._lib.engine_is_playing())
    
    @property
    def is_paused(self):  return bool(self._lib.engine_is_paused())
    
    @property
    def progress(self):   return self._lib.engine_get_progress()
    
    @property
    def current_index(self): return self._lib.engine_get_current_index()
    
    @property
    def queue_version(self): return self._lib.engine_get_queue_version()
    
    @property
    def library_version(self): return self._lib.engine_get_library_version()
    
    @property
    def library(self):
        # Usar cache para no serializar en cada tick
        lv = self.library_version
        if lv != self._lib_version_cache:
            self._library_cache = self._fetch_library()
            self._lib_version_cache = lv
        return self._library_cache

    @property
    def queue(self):
        qv = self.queue_version
        if qv != self._queue_version_cache:
            self._queue_cache = self._fetch_queue()
            self._queue_version_cache = qv
        return self._queue_cache

    # ── Métodos proxy ─────────────────────────────────────────────────
    def play(self):            self._lib.engine_play()
    def pause(self):           self._lib.engine_pause()
    def toggle_play(self):     self._lib.engine_toggle_play()
    def next_track(self):      self._lib.engine_next()
    def prev_track(self):      self._lib.engine_prev()
    def toggle_random(self):   return bool(self._lib.engine_toggle_random())
    
    def get_current_track(self):
        c = TrackC()
        if self._lib.engine_get_current_track(ctypes.byref(c)):
            return Track(c)
        return None
    
    def _fetch_library(self, max_count=5000):
        arr = (TrackC * max_count)()
        n = self._lib.engine_get_library(arr, max_count)
        return [Track(arr[i]) for i in range(n)]
    
    def _fetch_queue(self, max_count=10000):
        arr = (TrackC * max_count)()
        n = self._lib.engine_get_queue(arr, max_count)
        return [Track(arr[i]) for i in range(n)]
    
    def _setup_argtypes(self):
        lib = self._lib
        lib.engine_init.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
        lib.engine_get_progress.restype = ctypes.c_double
        lib.engine_get_current_track.argtypes = [ctypes.POINTER(TrackC)]
        lib.engine_get_current_track.restype = ctypes.c_int
        lib.engine_get_library.argtypes = [ctypes.POINTER(TrackC), ctypes.c_int]
        lib.engine_get_library.restype = ctypes.c_int
        lib.engine_get_queue.argtypes = [ctypes.POINTER(TrackC), ctypes.c_int]
        lib.engine_get_queue.restype = ctypes.c_int
        lib.engine_get_audio_bars.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_int]
    
    # ── Stubs de las demás funciones (se implementan siguiendo el mismo patrón)
    def get_audio_bars(self, n): ...
    def get_acoustic_dna(self):  ...
    def set_rating(self, tid, stars): ...
    def play_selection(self, tab, row): ...
    def rate_selection(self, tab, row, stars): ...
    def like_track(self, tid): ...
    def get_active_user_name(self): ...
    def create_album(self, name): ...
    def remove_album(self, name): ...
    def add_track_to_album(self, album, tid): ...
    def remove_track_from_album(self, album, tid): ...
    def get_albums_summary(self): ...
    def get_album_tracks(self, album): ...
    def get_directories(self): ...
    def jump_to_queue_index(self, i): ...
    def generate_queue(self): ...
    def toggle_random(self): ...
    def is_random_mode(self): ...
```

---

## 5. Plan de Implementación Paso a Paso

### FASE 1: Infraestructura CMake y "Hola Mundo" cross-language

**Objetivo:** Compilar un `.so` mínimo y llamarlo desde Python en menos de 2 horas.

**Paso 1.1 — Escribir `CMakeLists.txt`:**

```cmake
cmake_minimum_required(VERSION 3.20)
project(MusicEngine VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Flags de producción
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG -ffast-math")
set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)

# Rutas de código fuente
set(SRC_DIR ${CMAKE_SOURCE_DIR}/src)
set(INC_DIR ${CMAKE_SOURCE_DIR}/include)
set(TP_DIR  ${CMAKE_SOURCE_DIR}/third_party)

# Archivos fuente (se agregan al compilar cada fase)
set(SOURCES
    ${SRC_DIR}/Track.cpp
    ${SRC_DIR}/PlaybackState.cpp
    ${SRC_DIR}/DoublyLinkedList.cpp
    ${SRC_DIR}/QueueManager.cpp
    ${SRC_DIR}/LibraryManager.cpp
    ${SRC_DIR}/AudioPlayer.cpp
    ${SRC_DIR}/Engine.cpp
    ${SRC_DIR}/CApi.cpp
)

# Biblioteca compartida (.so en Linux, .dll en Windows)
add_library(music_engine SHARED ${SOURCES})
target_include_directories(music_engine PRIVATE ${INC_DIR} ${TP_DIR})

# Linking: solo dl en Linux (miniaudio lo necesita para dlopen)
target_link_libraries(music_engine PRIVATE dl pthread m)
```

**Paso 1.2 — Hola Mundo mínimo para validar la cadena:**

En `CApi.cpp`:
```cpp
#include <cstring>
extern "C" {
    const char* engine_hello() { return "C++ engine online"; }
}
```

En Python:
```python
import ctypes
lib = ctypes.CDLL("./core/engine/build/libmusic_engine.so")
lib.engine_hello.restype = ctypes.c_char_p
print(lib.engine_hello())  # → b"C++ engine online"
```

**Comandos de compilación:**
```bash
cd core/engine
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
# Resultado: build/libmusic_engine.so
```

**Criterio de éxito Fase 1:** `python -c "import ctypes; lib=ctypes.CDLL('./core/engine/build/libmusic_engine.so'); print('OK')"` sin errores.

---

### FASE 2: Carga de JSON y Estructuras de Datos

**Objetivo:** LibraryManager y QueueManager completamente funcionales, dados de prueba desde `library.json`.

**Orden de implementación:**
1. `Track.cpp` — constructor, `to_c()`, `from_json(nlohmann::json&)`
2. `LibraryManager.cpp` — `load_from_json()`, `scan_directories()`, `get_snapshot()`
3. `DoublyLinkedList.cpp` — template completo con nodos, push_back, move_next, move_prev, jump_to_index
4. `QueueManager.cpp` — `generate()` secuencial, `generate()` random ponderado, `get_snapshot()`
5. `CApi.cpp` — `engine_get_library()`, `engine_get_queue()`, `engine_get_queue_version()`
6. `backend_native.py` — `library` property, `queue` property, `queue_version` property

**Test de validación Fase 2:**
```python
from core.backend_native import NativeBackend
b = NativeBackend({"id": 1, "name": "Test"})
tracks = b.library
print(f"{len(tracks)} pistas cargadas")
print(tracks[0].title, tracks[0].duration)
```

---

### FASE 3: Motor de Audio (AudioPlayer + control_loop)

**Objetivo:** Reproducción real, pausa, next/prev, sin Pygame, con detección correcta de fin de pista.

**Orden de implementación:**
1. `AudioPlayer.cpp`:
   - `initialize()`: `ma_engine_init(NULL, &engine)` o configuración custom
   - `load_and_play(path, duration)`: `ma_sound_init_from_file`, `ma_sound_start`
   - `pause()` / `resume()`: `ma_sound_stop` / `ma_sound_start`
   - `is_hardware_busy()`: `ma_sound_is_playing(&sound)`
   - `get_file_duration(path)`: `ma_decoder_init_file` → `ma_decoder_get_length_in_pcm_frames` / sample_rate
2. `Engine.cpp`:
   - `_control_loop()`: corre cada 50ms, acumula progreso, detecta `!audio_player.is_hardware_busy()` para `next_track()`
   - Toda la lógica de `toggle_play()`, `next_track()` bajo mutex

**Pausa sin reinicio (lección aprendida de Python):**
```cpp
void Engine::toggle_play() {
    std::lock_guard<std::mutex> lock(control_mutex);
    if (state.is_playing.load()) {
        audio_player.pause();
        state.is_playing.store(false);
        state.is_paused.store(true);
    } else {
        if (state.is_paused.load()) {
            audio_player.resume();  // ← NO llama a load_and_play()
        } else {
            audio_player.load_and_play(current_track->path, current_track->duration);
        }
        state.is_playing.store(true);
        state.is_paused.store(false);
    }
}
```

**Criterio de éxito Fase 3:** Reproducir MP3 VBR completo, pausar/reanudar sin reinicio, saltar pistas, auto-saltar al terminar.

---

### FASE 4: Integración Final con bridge.py

**Objetivo:** La UI Python funciona idéntica pero el audio corre en C++.

1. Completar todos los stubs de `backend_native.py`:
   - `get_audio_bars()` → `engine_get_audio_bars()`
   - `get_acoustic_dna()` → genera el DNA en Python usando semilla del Engine
   - Gestión de álbumes completa
2. Modificar `core/bridge.py`:
   ```python
   def __init__(self, current_user=None):
       try:
           from core.backend_native import NativeBackend
           self.backend = NativeBackend(current_user)
           logger.info("Motor C++ activo.")
       except Exception as e:
           logger.warning(f"Motor C++ no disponible ({e}). Usando Python.")
           from core.backend import MockBackend
           self.backend = MockBackend(current_user)
   ```
3. Tests de regresión visual: ejecutar la app completa y verificar que las 4 pestañas, los álbumes, las calificaciones y el visualizador funcionen exactamente igual.

---

## 6. Contrato de la C-API

Tabla completa de funciones exportadas que `backend_native.py` deberá mapear:

| Función C | Firma | Equivalente Python |
|---|---|---|
| `engine_init` | `(char*, char*, int) → void` | `MockBackend.__init__()` |
| `engine_shutdown` | `() → void` | `del backend` |
| `engine_play` | `() → void` | `backend.play()` |
| `engine_pause` | `() → void` | `backend.pause()` |
| `engine_toggle_play` | `() → void` | `backend.toggle_play()` |
| `engine_next` | `() → void` | `backend.next_track()` |
| `engine_prev` | `() → void` | `backend.prev_track()` |
| `engine_jump_to_index` | `(int) → void` | `backend.jump_to_queue_index(i)` |
| `engine_get_current_track` | `(TrackC*) → int` | `backend.get_current_track()` |
| `engine_get_progress` | `() → double` | `backend.progress` |
| `engine_is_playing` | `() → int` | `backend.is_playing` |
| `engine_is_paused` | `() → int` | `backend.is_paused` |
| `engine_get_current_index` | `() → int` | `backend.current_index` |
| `engine_get_queue_version` | `() → int` | `backend.queue_version` |
| `engine_get_library_version` | `() → int` | `backend.library_version` |
| `engine_get_library` | `(TrackC*, int) → int` | `backend.library` |
| `engine_get_queue` | `(TrackC*, int) → int` | `backend.queue` |
| `engine_toggle_random` | `() → int` | `backend.toggle_random()` |
| `engine_set_rating` | `(int, int) → void` | `backend.set_rating()` |
| `engine_get_audio_bars` | `(float*, int) → void` | `backend.get_audio_bars(n)` |
| `engine_get_active_user_name` | `(char*, int) → void` | `backend.get_active_user_name()` |
| `engine_like_track` | `(int) → int` | `backend.like_track(id)` |
| `engine_create_album` | `(char*) → int` | `backend.create_album(name)` |
| `engine_remove_album` | `(char*) → int` | `backend.remove_album(name)` |
| `engine_add_track_to_album` | `(char*, int) → int` | `backend.add_track_to_album()` |
| `engine_remove_track_from_album` | `(char*, int) → int` | `backend.remove_track_from_album()` |
| `engine_get_albums_summary` | `(char**, int*, int) → int` | `backend.get_albums_summary()` |
| `engine_get_album_tracks` | `(char*, TrackC*, int) → int` | `backend.get_album_tracks()` |

---

*Fin del ARCHITECTURE MASTER PLAN v2.0*  
*El prototipo Python es la especificación ejecutable de todo lo anterior.*
