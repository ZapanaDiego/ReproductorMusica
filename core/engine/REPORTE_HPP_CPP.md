# REPORTE DE ANÁLISIS: Motor C++ y Transición del Backend

## 1. ESTADO ACTUAL DEL CÓDIGO (C++)
Actualmente, el motor C++ de `vercion02` se encuentra estructurado bajo un estándar profesional de **Arquitectura Limpia**, separando estrictamente las declaraciones (`.hpp` en `include/`) de sus implementaciones lógicas (`.cpp` en `src/`).

### Componentes Activos:
* **`Track`, `DoublyLinkedList`, `QueueManager`:** Gestionan las estructuras de datos, la cola de reproducción circular y el algoritmo de barajado (*shuffle*) ponderado.
* **`LibraryManager`:** Lee y escribe el catálogo maestro de música desde `database/library.json`.
* **`UserManager`:** Administra perfiles, listas de favoritos (`liked_tracks`) y álbumes personalizados en `database/users_db.json`.
* **`AudioPlayer` y `Engine`:** Manejan el hardware físico usando hilos secundarios, evitando bloqueos (deadlocks), y protegiendo el hardware con inyecciones de silencio (`std::memset`) para evitar ruidos de estática.
* **`CApi`:** Interfaz externa (`extern "C"`) totalmente terminada y lista para hablar con Python.

---

## 2. ANÁLISIS DE BRECHAS Y FALLAS (Lo que falta por hacer vs. Requerimientos)

Al comparar la arquitectura actual con los nuevos requerimientos que has planteado, he identificado las siguientes **fallas lógicas** y tareas pendientes críticas para la transición del backend de Python a C++:

### Falla Crítica #1: Calificaciones (Estrellas) Globales vs. Por Usuario
* **El Problema:** Actualmente, la propiedad `estrellas` (stars) pertenece a la clase `Track` y se guarda en `library.json`. Esto significa que si un usuario califica una canción con 5 estrellas, ese puntaje se aplica para *todos los usuarios*.
* **La Solución:** Para cumplir tu requerimiento de separar los gustos, la variable `estrellas` debe eliminarse de `LibraryManager` y del archivo `library.json`. En su lugar, el `UserManager` (y `users_db.json`) debe implementar un mapa interno (diccionario) que asocie el `ID de Canción -> Cantidad de Estrellas` de forma exclusiva por cada perfil.

### Tarea Pendiente #2: El Escáner de Directorios de Música
* **El Problema:** Actualmente `LibraryManager` lee el JSON asumiendo que las canciones ya existen ahí. No tiene la capacidad de buscar en el disco duro.
* **La Solución:** Debemos implementar una nueva clase (ej. `DirectoryScanner.cpp`) usando la librería nativa `<filesystem>` de C++17. Al arrancar `Engine::inicializar()`, este escáner debe:
  1. Buscar en la raíz del sistema o rutas locales iterando sobre posibles nombres: `"Musica"`, `"Música"`, `"Music"`, `"music"`, `"muscia"`.
  2. Indexar todos los archivos `.mp3`, `.wav`, etc.
  3. Comparar lo encontrado físicamente con lo que hay en memoria (`library.json`). Si hay canciones nuevas, agregarlas; si hay canciones borradas en el disco, eliminarlas del JSON.

### Tarea Pendiente #3: Flujo de Inicialización de Usuarios
* **El Problema:** `UserManager` carga el JSON, pero si no hay usuarios, el motor no detiene el arranque para forzar una creación.
* **La Solución:** Al conectarse mediante el puente, Python debe consultar a C++ si existen usuarios (`obtener_nombres_usuarios()`). Si la lista está vacía, la interfaz en Textual (Python) debe bloquear la pantalla, pedir un nombre, enviarlo a C++ para registrarlo (`crear_usuario`) y luego continuar.

---

## 3. CONEXIÓN PYTHON - C++ (`core/bridge.py`)

El archivo `bridge.py` será la única frontera de comunicación. Para que el reproductor no colapse, `bridge.py` debe implementarse con mucho cuidado usando la librería `ctypes` de Python:

1. **Carga del Binario:** 
   ```python
   import ctypes
   motor_lib = ctypes.CDLL("./core/engine/build/libmusic_engine.so")
   ```
2. **Traducción de Estructuras (Structs):**
   Para poder leer el catálogo (snapshot) desde C++, `bridge.py` debe declarar un `ctypes.Structure` exacto que haga espejo con la estructura `TrackC` definida en `Track.hpp` (respetando los arreglos de 512 bytes de caracteres).
3. **Mapeo de Firmas:**
   Se deben definir explícitamente los `argtypes` (tipos de entrada) y `restype` (tipos de salida) para todas las funciones de `CApi.cpp`. Por ejemplo:
   ```python
   motor_lib.engine_is_playing.argtypes = [ctypes.c_void_p]
   motor_lib.engine_is_playing.restype = ctypes.c_int32
   ```

### CONCLUSIÓN E INDICACIONES PARA LOS SIGUIENTES PASOS
La infraestructura central es robusta, pero antes de lanzar el frontend completo, la prioridad absoluta es:
1. **Refactorizar el modelo de estrellas** (trasladar las calificaciones de `library` a `users_db`).
2. **Construir el Escáner Automático de C++17** (`<filesystem>`) que detecte modificaciones en los directorios de música al iniciar el programa.
3. **Programar `bridge.py`** implementando los callbacks de `ctypes` para interactuar con la C-API ya finalizada.


# REPORTE DE ARQUITECTURA Y AUDITORÍA: MOTOR C++ (v2.0)

## 1. Resumen Ejecutivo
El motor nativo de C++ para `vercion02` se encuentra en una fase avanzada de estabilización arquitectónica. Se ha logrado una separación estricta y rigurosa entre las cabeceras (`.hpp`) y las implementaciones (`.cpp`), garantizando tiempos de compilación óptimos y mitigando por completo los errores de redefinición de símbolos durante el enlazado (linker). 

Actualmente, el motor maneja correctamente la persistencia base mediante `nlohmann/json`, delega la concurrencia física del audio al hardware a través de `miniaudio.h` y expone una fachada plana funcional en `CApi.cpp`. Sin embargo, el estado actual es fundacional; carece de las implementaciones dinámicas de escaneo de disco, sincronización autónoma y aislamiento real de datos por perfil de usuario que exige la lógica de negocio final.

## 2. Análisis del Código Existente

### Evaluación Estructural (HPP/CPP)
* **Aislamiento de Lógica:** Las clases `LibraryManager`, `UserManager`, `QueueManager`, `AudioPlayer` y `Engine` han sido correctamente desacopladas. Los archivos `.hpp` actúan exclusivamente como contratos e interfaces, mientras que la complejidad reside en los `.cpp`.
* **Templates:** La clase `DoublyLinkedList` permanece correctamente alojada en su cabecera para permitir la instanciación de tipos (Template Metaprogramming) en tiempo de compilación.

### Análisis de Concurrencia y Memoria
* **Protección del Hilo de Monitoreo:** En `Engine.cpp`, la implementación del hilo `std::thread hilo_monitoreo` está correctamente salvaguardada por un `std::mutex`. Sin embargo, existe un cuello de botella potencial: si el hilo secundario compite demasiado rápido por el mutex al despertar cada 50ms, podría generar una ligera degradación de rendimiento. Usar `std::condition_variable` sería una arquitectura más eficiente que el *polling* con `sleep_for`.
* **Seguridad de Punteros (Memory Safety):** El puente C-API (`CApi.cpp`) utiliza `std::strncpy` para poblar arreglos estáticos `char[512]` hacia Python, mitigando eficazmente los desbordamientos de búfer (Buffer Overflow).
* **Ausencia de Fugas (Memory Leaks):** El ciclo de vida de `engine_create` y `engine_destroy` administra explícitamente el uso del Heap (`new`/`delete`).

## 3. Integración C++ y Python (`bridge.py`)

La interoperabilidad binaria a través de `ctypes` presenta desafíos específicos relacionados con el hilo principal (Main Thread) de la interfaz de Python:

* **Bloqueos de la UI Asíncrona (Event Loop):** Las operaciones pesadas en C++ (como el futuro escaneo de discos) bloquearán el GIL de Python y el bucle de eventos si se invocan de forma síncrona desde `bridge.py`.
* **Mitigación:** `CApi.cpp` deberá exponer el método de escaneo en un hilo en segundo plano (detached thread en C++) o, preferiblemente, Python deberá ejecutar la llamada a `ctypes` dentro de un `ThreadPoolExecutor` usando `asyncio.to_thread()`.
* **Estructuras de Datos C-Compatible:** `bridge.py` debe definir rigurosamente clases herederas de `ctypes.Structure` para decodificar los arreglos planos generados por `engine_get_library` y `engine_get_queue`, validando que los tipos de datos numéricos (`int32_t`, `double`) empaten exactamente en tamaño.

## 4. Brechas de Funcionalidad (Gap Analysis)

Con base en los requerimientos del negocio, el motor actual presenta las siguientes deficiencias críticas:

1. **Escáner Ciego:** `LibraryManager` asume que `database/library.json` ya contiene los datos. No existe lógica nativa para rastrear y descubrir archivos en el sistema (`Musica`, `Música`, etc.).
2. **Ausencia de Sincronización Automática:** Si un usuario añade un `.mp3` en su carpeta física mediante su explorador de archivos, el motor C++ no tiene manera de detectar este cambio (sincronización delta diferencial).
3. **Fallo en el Modelo de Datos (Estrellas Globales):** Actualmente, la propiedad `estrellas` (rating) pertenece a la clase `Track` y se guarda en `library.json`. Esto provoca una fuga de preferencias: si el *Usuario A* califica con 5 estrellas, el *Usuario B* verá 5 estrellas. **Los metadatos dinámicos no están separados por perfil.**
4. **Flujo de Usuario Inicialización:** El motor en C++ asume que el usuario activo se impone desde fuera; carece de un disparador condicional que alerte a Python que la base de datos de usuarios está virgen y requiere un flujo de creación obligatorio (Onboarding).

## 5. Diseño Lógico para Nuevas Funcionalidades

### Arquitectura de Escaneo Recursivo (`std::filesystem`)
Se implementará una nueva clase `DirectoryScanner`.
* **Mecanismo:** Utilizará `std::filesystem::recursive_directory_iterator` de C++17 para buscar ágilmente en los directorios raíces habituales del sistema operativo (ej. detectando `$HOME/Music`, `/mnt/c/Users/Usuario/Music`).
* **Optimización Criptográfica Rápida:** Para determinar si un directorio físico cambió respecto al JSON, se iterará sobre las fechas de modificación (`std::filesystem::last_write_time`). Si el directorio no ha sido alterado, se omite el análisis profundo, garantizando una carga instantánea (O(1)).
* **Resolución de Diferencias (Diffing):** Se usarán conjuntos (`std::set<std::string>`) para cruzar las rutas en el JSON actual contra las rutas físicas. Se inyectarán los `inserts` y `deletes` correspondientes, actualizando `database/library.json`.

### Refactorización Estructural: Aislamiento de Metadatos
Se alterará el esquema JSON y los modelos de memoria:
* **`database/library.json` (Inventario Puro):** Solo almacenará identificador `id`, `title`, `artist`, `album`, `duration` y `path`.
* **`database/users_db.json` (Preferencias Dinámicas):** El esquema del usuario adquirirá un nuevo mapeo: `"ratings": { "ID_Cancion": estrellas }`.
Al cargar un usuario en el `Engine`, las propiedades visuales de la interfaz cruzarán el ID estático de la canción con el diccionario de preferencias aislando así los gustos (Estrellas, Listas y Favoritos).

## 6. Plan de Acción (Hoja de Ruta)

Para concluir el núcleo de este motor y habilitar el enlace total con el Textual de Python, se ejecutará el siguiente plan:

1. **Refactorización del Modelo `Track`:** Extraer la variable `estrellas` de `LibraryManager` y crear su persistencia en el `std::unordered_map` interno de `UserManager`.
2. **Implementación de `DirectoryScanner.cpp`:**
   * Programar la lógica C++17 para detectar carpetas raíz (`Música`, `Music`, etc.).
   * Indexar archivos filtrando por extensiones soportadas (`.mp3`, `.wav`, `.flac`).
3. **Programación de la Sincronización Delta (`sync_library`):**
   * Incorporar en el ciclo de inicialización del `Engine` el cruce de datos entre el escáner y la base de datos de biblioteca.
4. **Actualización del Puente Binario (`CApi.cpp`):**
   * Añadir funciones como `engine_has_users()`, `engine_sync_directories()`, y `engine_set_user_rating()`.
5. **Codificación de `core/bridge.py` en Python:**
   * Crear la clase Wrapper en Python que cargue el `.so`, mapee los `ctypes` y exponga llamadas `async` seguras para la interfaz.