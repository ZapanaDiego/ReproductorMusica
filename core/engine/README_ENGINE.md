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