# ESTUDIO TÉCNICO EXHAUSTIVO DEL MOTOR NATIVO C++ — REPRODUCTOR DE MÚSICA `vercion02`

> **Documento:** `ESTUDIO_HPP_CPP_H_TXT.md`
> **Ubicación:** `vercion02/core/engine/`
> **Autor:** Arquitecto de Sistemas — Auditoría de Código de Bajo Nivel
> **Fecha:** 30 de junio de 2026

---

# TABLA DE CONTENIDOS

1. [LA FÁBRICA DEL CÓDIGO — CMakeLists.txt](#1-la-fábrica-del-código--análisis-de-cmakeliststxt)
2. [LOS GIGANTES EXTERNOS — third_party/](#2-los-gigantes-externos--análisis-de-third_party)
3. [LAS ESTRUCTURAS DE DATOS BASE Y LA MEMORIA — DoublyLinkedList](#3-las-estructuras-de-datos-base-y-la-memoria)
4. [DISECCIÓN INDUSTRIAL DE LOS ARCHIVOS DEL MOTOR](#4-disección-industrial-de-los-archivos-del-motor)
   - 4.1 Track.hpp
   - 4.2 AudioPlayer.hpp / .cpp
   - 4.3 PlaybackState.hpp / .cpp
   - 4.4 QueueManager.hpp / .cpp
   - 4.5 LibraryManager.hpp / .cpp
   - 4.6 UserManager.hpp / .cpp
   - 4.7 DirectoryScanner.hpp / .cpp
   - 4.8 SpectrumAnalyzer.hpp / .cpp
   - 4.9 Engine.hpp / .cpp
5. [EL PUENTE E INTERFAZ BINARIA A PYTHON — CApi y Estructuras POD](#5-el-puente-e-interfaz-binaria-a-python)

---

# 1. LA FÁBRICA DEL CÓDIGO — Análisis de CMakeLists.txt

## 1.1 ¿Qué es compilar y enlazar?

Imagina que estás construyendo un rompecabezas enorme. Cada archivo `.cpp` es una bolsa sellada con piezas de una sección del rompecabezas. **Compilar** es el acto de abrir cada bolsa y armar las piezas individuales de esa sección. Al compilar `AudioPlayer.cpp`, el compilador (`g++`) traduce tu código escrito en C++ a **código máquina**: instrucciones binarias que el procesador (la CPU Intel o AMD de tu computadora) puede ejecutar directamente. El resultado de compilar un solo `.cpp` es un **archivo objeto** (`.o`), que contiene las instrucciones en ceros y unos, pero que todavía no es un programa funcional porque sus piezas tienen "huecos": referencias a funciones que están definidas en *otros* archivos `.cpp`.

**Enlazar** (o "linkear") es el segundo paso. El **enlazador** (`ld`, invocado automáticamente por `g++`) toma *todos* los archivos `.o` generados y los ensambla como las secciones del rompecabezas para formar una única pieza final. En nuestro caso, esa pieza final no es un programa ejecutable, sino una **librería compartida** llamada `libmusic_engine.so`. El `.so` significa "Shared Object" (Objeto Compartido): es un bloque de código máquina que otro programa (en este caso, Python) puede cargar dinámicamente en tiempo de ejecución usando `ctypes.CDLL()`.

## 1.2 Análisis línea por línea de CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.12)
```
Esta línea le dice a CMake: "Necesito que tengas al menos la versión 3.12 para entender mis instrucciones". CMake es un **meta-sistema de construcción**: no compila nada por sí mismo, sino que genera los archivos `Makefile` que luego el comando `make` utiliza para invocar al compilador `g++`.

```cmake
project(music_engine CXX)
```
Declara el nombre del proyecto (`music_engine`) y especifica que el lenguaje de programación es C++ (`CXX` es la abreviatura estándar que usa CMake para C++).

```cmake
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
```
Estas dos líneas son críticas. Le dicen al compilador: "Compila usando el estándar C++17, y si no lo soportas, aborta con un error". C++17 es esencial en este proyecto porque usamos `std::filesystem` (para escanear directorios de música) y `std::optional`, entre otros.

```cmake
include_directories(include third_party)
```
Le dice al compilador dónde buscar los archivos `.hpp` cuando tu código escribe `#include "Track.hpp"` o `#include "miniaudio.h"`. Es como decirle al cartero: "Las direcciones de los buzones están en estas dos carpetas".

```cmake
file(GLOB FUENTES "src/*.cpp")
```
Busca automáticamente todos los archivos que terminen en `.cpp` dentro de la carpeta `src/` y los guarda en una variable llamada `FUENTES`. Es un comodín: si mañana agregas un nuevo archivo `MiModulo.cpp` en `src/`, CMake lo detectará automáticamente.

```cmake
list(REMOVE_ITEM FUENTES "${CMAKE_CURRENT_SOURCE_DIR}/src/DoublyLinkedList.cpp")
```
Excluye explícitamente el archivo `DoublyLinkedList.cpp` de la compilación. ¿Por qué? Porque `DoublyLinkedList` es una **clase plantilla** (Template). Las plantillas en C++ son como moldes de galletas: no existen como objeto hasta que alguien las usa con un tipo específico (ej. `ListaDoblementeEnlazada<Track>`). Si intentáramos compilar el `.cpp` por separado, el compilador no sabría qué tipo usar y el enlazador fallaría con "undefined reference".

```cmake
add_library(music_engine SHARED ${FUENTES})
```
Esta es la instrucción central. Le dice a CMake: "Con todos los archivos `.cpp` que encontraste (excepto el excluido), compílalos y enlázalos para generar una **librería compartida** llamada `libmusic_engine.so`". La palabra `SHARED` es la que determina que el producto final sea un `.so` (Linux) en lugar de un ejecutable.

```cmake
find_package(Threads REQUIRED)
target_link_libraries(music_engine PRIVATE Threads::Threads)
```
Busca la implementación de hilos del sistema operativo (`pthreads` en Linux) y la enlaza con nuestra librería. Esto es necesario porque `Engine.cpp` usa `std::thread` para crear un hilo secundario de monitoreo. Sin esta línea, el enlazador fallaría al no encontrar los símbolos de `pthread_create`.

```cmake
target_link_libraries(music_engine PRIVATE stdc++fs)
```
Enlaza la librería de `std::filesystem`. En versiones de GCC anteriores a la 9, `<filesystem>` no estaba integrada automáticamente en la librería estándar y debía enlazarse manualmente. Esta línea garantiza compatibilidad.

---

# 2. LOS GIGANTES EXTERNOS — Análisis de third_party/

## 2.1 ¿Qué es una "Single-Header Library"?

Normalmente, una librería de C/C++ se distribuye en dos partes: los archivos de **declaración** (`.h` o `.hpp` con las firmas de las funciones) y los archivos de **implementación** precompilados (`.a`, `.so` o `.lib`). Instalar una librería así requiere configurar rutas de búsqueda, versiones y compatibilidad.

Una **Single-Header Library** (Biblioteca de Un Solo Encabezado) es un enfoque radicalmente diferente: TODO el código —tanto las declaraciones como la implementación completa— está empaquetado dentro de un **único archivo** `.h` o `.hpp`. No necesitas instalar nada. Simplemente copias el archivo a tu proyecto, escribes `#include "miniaudio.h"` y listo. El compilador se encarga de procesar las decenas de miles de líneas de código como si fueran parte de tu propio proyecto.

## 2.2 miniaudio.h — El Controlador del Hardware de Audio

`miniaudio.h` es una librería de audio de bajo nivel escrita en C puro. Tiene aproximadamente **90,000 líneas de código** en un solo archivo. Su trabajo es ser un traductor universal entre tu programa y la tarjeta de sonido física de tu computadora.

### ¿Cómo llega la música desde un archivo .mp3 hasta tus audífonos?

El viaje completo tiene esta secuencia:

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│  Archivo.mp3 │────>│  ma_decoder      │────>│  Búfer de Audio      │
│  (en disco)  │     │  (decodificador) │     │  (array de floats    │
│              │     │  Descomprime MP3 │     │   en la RAM)         │
│              │     │  a muestras PCM  │     │                      │
└──────────────┘     └──────────────────┘     └──────────┬───────────┘
                                                         │
                                                         ▼
                                              ┌──────────────────────┐
                                              │  ma_device           │
                                              │  (dispositivo)       │
                                              │  Envía los datos al  │
                                              │  Kernel de Linux     │
                                              └──────────┬───────────┘
                                                         │
                                                         ▼
                                              ┌──────────────────────┐
                                              │  ALSA / PulseAudio   │
                                              │  / PipeWire          │
                                              │  (Servidor de audio  │
                                              │   del SO)            │
                                              └──────────┬───────────┘
                                                         │
                                                         ▼
                                              ┌──────────────────────┐
                                              │  TARJETA DE SONIDO   │
                                              │  (Hardware físico)   │
                                              │  Convierte señales   │
                                              │  digitales a ondas   │
                                              │  eléctricas (DAC)    │
                                              └──────────┬───────────┘
                                                         │
                                                         ▼
                                              ┌──────────────────────┐
                                              │  🎧 AUDÍFONOS /     │
                                              │     PARLANTES        │
                                              └──────────────────────┘
```

**PCM** significa "Pulse Code Modulation" (Modulación por Pulsos Codificados). Es el formato universal de audio crudo: una secuencia enormemente larga de números decimales (flotantes de 32 bits), donde cada número representa la amplitud de la onda de sonido en un instante de tiempo. Un segundo de audio estéreo a 44,100 Hz contiene **88,200 flotantes** (44,100 muestras × 2 canales).

El **callback** es la pieza más crítica de todo el sistema. miniaudio crea un hilo de **muy alta prioridad** controlado por el sistema operativo. Cada pocos milisegundos, este hilo le dice a tu código: "Dame más datos de audio AHORA". Tu función `procesar_audio()` debe llenar un búfer de memoria con las muestras PCM lo más rápido posible, en microsegundos. Si tardas demasiado, se escucharán cortes, chasquidos o silencio.

## 2.3 nlohmann/json.hpp — El Parser de JSON

`nlohmann/json.hpp` tiene aproximadamente **25,000 líneas de código** en un solo archivo. Transforma texto plano de un archivo `.json` en estructuras de datos navegables en memoria.

### ¿Cómo parsea un JSON? El viaje del texto a la memoria

Cuando tu código escribe:
```cpp
std::ifstream archivo("database/library.json");
json datos;
archivo >> datos;
```

Ocurre lo siguiente:

1. **Lectura del archivo:** `std::ifstream` pide al kernel de Linux (mediante la llamada al sistema `read()`) que lea los bytes del archivo desde el disco duro hacia un búfer temporal en la RAM.

2. **Tokenización (Lexer):** La librería recorre cada carácter del texto. Cuando encuentra `{`, sabe que empieza un objeto. Cuando encuentra `"title"`, sabe que es una cadena de texto (string). Cuando encuentra `:`, sabe que viene el valor asociado. Esto genera una lista de "tokens" (fichas).

3. **Parsing (Análisis sintáctico):** Los tokens se organizan en un árbol jerárquico en memoria llamado **DOM** (Document Object Model). Cada nodo del árbol es un objeto `nlohmann::json` que internamente usa un `std::map` para objetos, un `std::vector` para arreglos, un `std::string` para textos y un `double` para números.

### ¿Dónde vive este árbol en la RAM?

Los objetos `json` de nlohmann se almacenan en el **Heap** (montículo dinámico). Cuando escribes `json datos;`, la variable `datos` es una cáscara pequeña que vive en el **Stack** (pila de ejecución), pero internamente, cuando el parser descubre que el JSON contiene un arreglo de 500 canciones, invoca `new` implícitamente para asignar la memoria dinámica necesaria en el Heap. Cuando la variable `datos` sale del alcance (scope) de la función, su destructor se ejecuta automáticamente y libera toda la memoria del Heap. Esto se llama **RAII** (Resource Acquisition Is Initialization): el recurso se adquiere al crear el objeto y se libera automáticamente al destruirlo.

---

# 3. LAS ESTRUCTURAS DE DATOS BASE Y LA MEMORIA

## 3.1 Lección Fundamental: Stack vs Heap — Las Dos Zonas de la RAM

Cuando tu programa en C++ se ejecuta, el sistema operativo le asigna un espacio de memoria virtual dividido en varias regiones. Las dos más importantes para entender el código del motor son:

### EL STACK (La Pila de Ejecución)

```
DIRECCIONES ALTAS DE MEMORIA (ej. 0x7FFF...)
┌─────────────────────────────────────────┐
│  main() - variables locales             │ ← El Stack crece
│  ├─ int contador = 5;        (4 bytes)  │    hacia ABAJO
│  └─ float volumen = 0.8;    (4 bytes)  │
├─────────────────────────────────────────┤
│  reproducir() - variables locales       │
│  ├─ bool pausado = false;    (1 byte)   │
│  └─ Track* puntero;         (8 bytes)  │
├─────────────────────────────────────────┤
│  cargar_archivo() - variables locales   │
│  └─ ma_result resultado;    (4 bytes)  │
├─────────────────────────────────────────┤
│  ... (más funciones llamadas)           │
└─────────────────────────────────────────┘
DIRECCIONES BAJAS DE MEMORIA (ej. 0x0000...)
```

Características del Stack:
- **Ultra rápido**: asignar una variable toma una sola instrucción de la CPU (mover el puntero de pila, el registro `RSP` en x86-64).
- **Automático**: las variables se crean al entrar a una función y se destruyen al salir. No necesitas liberar nada manualmente.
- **Tamaño fijo y limitado**: típicamente 8 MB en Linux. Si lo desbortas (por ejemplo, con recursión infinita), obtienes un **Stack Overflow** y el programa muere.
- **Aquí viven**: variables `int`, `float`, `bool`, punteros crudos (`Track*`), y la "cáscara" de objetos como `std::string` (que internamente apunta al Heap).

### EL HEAP (El Montículo Dinámico)

```
DIRECCIONES BAJAS DE MEMORIA
┌─────────────────────────────────────────┐
│  Nodo 1 (Track: "Bohemian Rhapsody")   │ ← Creado con 'new'
│  [dato | *anterior=NULL | *siguiente=──]──┐
├─────────────────────────────────────────┤  │
│  Nodo 2 (Track: "Hotel California")    │<─┘
│  [dato | *anterior=────── | *siguiente=──]──┐
├─────────────────────────────────────────┤    │
│  Nodo 3 (Track: "Stairway to Heaven")  │<───┘
│  [dato | *anterior=────── | *siguiente=NULL]
├─────────────────────────────────────────┤
│  std::string datos internos "Bohemian.."│ ← Asignado por std::string
├─────────────────────────────────────────┤
│  std::vector búfer interno [Track0,     │ ← Asignado por std::vector
│                              Track1...] │
├─────────────────────────────────────────┤
│  (espacio libre / fragmentado)          │
└─────────────────────────────────────────┘
DIRECCIONES ALTAS DE MEMORIA (el Heap crece hacia arriba)
```

Características del Heap:
- **Flexible**: puedes pedir cualquier cantidad de memoria cuando quieras, usando `new` (C++) o `malloc` (C).
- **Manual (o semi-manual)**: si usas `new`, debes usar `delete` para liberar. Si olvidas hacerlo, tienes una **fuga de memoria** (Memory Leak). Los contenedores de la STL (`std::vector`, `std::string`, `std::unordered_map`) gestionan su propia memoria del Heap automáticamente mediante RAII.
- **Más lento**: asignar memoria en el Heap requiere que el sistema operativo busque un bloque libre, lo que puede tomar cientos de nanosegundos.

### ¿Cómo gestiona std::string la memoria internamente?

Cuando declaras `std::string titulo = "Bohemian Rhapsody";`, ocurre lo siguiente:

1. En el **Stack** se reservan ~32 bytes para la "cáscara" del `std::string`. Esta cáscara contiene: un puntero al búfer de texto real, el tamaño actual del texto y la capacidad del búfer.
2. Si el texto es muy corto (típicamente ≤ 15 caracteres), se usa la **SSO** (Small String Optimization): el texto se almacena directamente dentro de la cáscara del Stack, sin tocar el Heap.
3. Si el texto es largo (como una ruta de archivo `/home/diego/Música/Mi Canción.mp3`), se invoca `new char[N]` internamente para asignar un bloque en el **Heap**, y el puntero de la cáscara apunta a ese bloque.

```
STACK                           HEAP
┌─────────────────────┐         ┌──────────────────────────────────────┐
│ std::string titulo   │         │ B o h e m i a n   R h a p s o d y  │
│ ├─ ptr ──────────────┼────────>│ (18 bytes de texto + '\0')          │
│ ├─ size = 17         │         └──────────────────────────────────────┘
│ └─ capacity = 32     │
└─────────────────────┘
```

## 3.2 Análisis Profundo de DoublyLinkedList.hpp

### Propósito de Diseño

`DoublyLinkedList.hpp` implementa una **Lista Doblemente Enlazada** genérica usando plantillas de C++ (`template<typename T>`). Su rol en el reproductor es ser el esqueleto de la cola de reproducción: almacenar las canciones en orden, permitir avanzar a la siguiente (`mover_siguiente()`), retroceder a la anterior (`mover_anterior()`), y comportarse de forma **circular** (al llegar al final, vuelve al principio).

### Estructura del Nodo en Memoria

Cada nodo (`NodoListaDoble<Track>`) se crea en el **Heap** usando el operador `new`. El nodo contiene:
- **dato** (una copia completa del objeto `Track`): ~120 bytes en el Heap (las strings internas de Track también se alojan en el Heap).
- **anterior** (puntero de 8 bytes): dirección de memoria del nodo previo.
- **siguiente** (puntero de 8 bytes): dirección de memoria del nodo siguiente.

### Diagrama ASCII: Lista con 3 Canciones

```
Variables de control (viven en el Stack del QueueManager):

  cabeza ──┐    actual ──┐    cola ──┐
           │             │           │
           ▼             ▼           ▼
HEAP:  ┌────────────┐  ┌────────────┐  ┌────────────┐
       │  NODO 0    │  │  NODO 1    │  │  NODO 2    │
       │────────────│  │────────────│  │────────────│
       │ Track:     │  │ Track:     │  │ Track:     │
       │ "Bohemian" │  │ "Hotel     │  │ "Stairway" │
       │ "Queen"    │  │  California│  │ "Led Zep"  │
       │ id: 1      │  │ id: 2      │  │ id: 3      │
       │────────────│  │────────────│  │────────────│
       │ anterior:  │  │ anterior: ─┼─>│ anterior: ─┼──┐
       │   NULL     │<─┼─ anterior  │  │  (Nodo 1)  │  │
       │────────────│  │────────────│  │────────────│  │
       │ siguiente:─┼─>│ siguiente:─┼─>│ siguiente: │  │
       │  (Nodo 1)  │  │  (Nodo 2)  │  │   NULL     │  │
       └────────────┘  └────────────┘  └────────────┘  │
                       ▲                                │
                       └────────────────────────────────┘
```

### Análisis de Métodos Críticos

**`agregar_al_final(T elemento)` — Complejidad: O(1)**

```cpp
NodoListaDoble<T>* nuevo_nodo = new NodoListaDoble<T>(std::move(elemento));
```

Esta línea ejecuta el operador `new`, que hace dos cosas: (1) Pide al sistema operativo un bloque de memoria en el Heap lo suficientemente grande para almacenar un `NodoListaDoble<Track>` (dato + 2 punteros). (2) Llama al constructor del nodo, que usa `std::move` para **trasladar** los datos del `Track` original al nodo nuevo sin copiarlos (como mudar muebles a una casa nueva en vez de comprar muebles nuevos idénticos).

**`limpiar()` — Complejidad: O(N)**

```cpp
NodoListaDoble<T>* iterador = cabeza;
while (iterador != nullptr) {
    NodoListaDoble<T>* siguiente_nodo = iterador->siguiente;
    delete iterador;     // ← Libera la memoria del Heap para este nodo
    iterador = siguiente_nodo;
}
```

Recorre cada nodo de la lista desde la cabeza hasta la cola, liberando la memoria de cada uno con `delete`. Es crucial guardar el puntero `siguiente` ANTES de borrar el nodo actual, porque una vez que haces `delete iterador`, esa zona de la RAM se marca como "libre" y leer `iterador->siguiente` después sería un **Dangling Pointer** (puntero colgante) que causa comportamiento indefinido.

**`saltar_a_indice(size_t indice)` — Complejidad: O(N/2)**

Este método es inteligente: si el índice está en la primera mitad de la lista, recorre desde la cabeza hacia adelante. Si está en la segunda mitad, recorre desde la cola hacia atrás. En el peor caso, recorre la mitad de la lista, por lo que su complejidad es O(N/2), que simplificado es O(N), pero en la práctica es el doble de rápido que una lista simple.

**`obtener_indice_actual()` — Complejidad: O(N)**

Recorre desde `cabeza` hasta `actual` contando pasos. Una mejora futura sería almacenar el índice como variable miembro para lograr O(1).

## 3.3 Tablas Hash: std::unordered_map

Varios componentes del motor usan `std::unordered_map`, una implementación de **tabla hash** de la STL. En `LibraryManager`, por ejemplo:

```cpp
std::unordered_map<int32_t, size_t> indice_por_id;
```

### ¿Cómo funciona una Tabla Hash por dentro?

Imagina un estacionamiento con 16 espacios numerados del 0 al 15. Cada coche (dato) tiene una placa (clave). La **función hash** es una fórmula matemática que convierte la placa en un número del 0 al 15 para saber en qué espacio estacionar.

```
Función Hash:  h(clave) = clave % cantidad_casilleros

Si clave = 42 y hay 16 casilleros:
h(42) = 42 % 16 = 10  →  Va al casillero 10

TABLA HASH EN MEMORIA (Heap):
┌─────┬───────────────────────────────────┐
│  0  │  (vacío)                          │
├─────┼───────────────────────────────────┤
│  1  │  clave: 17 → valor: posición 3   │
├─────┼───────────────────────────────────┤
│  2  │  (vacío)                          │
├─────┼───────────────────────────────────┤
│ ... │  ...                              │
├─────┼───────────────────────────────────┤
│ 10  │  clave: 42 → valor: posición 7   │──┐ COLISIÓN
│     │  clave: 58 → valor: posición 12  │<─┘ (58 % 16 = 10 también)
├─────┼───────────────────────────────────┤
│ ... │  ...                              │
└─────┴───────────────────────────────────┘
```

Una **colisión** ocurre cuando dos claves distintas producen el mismo índice. `std::unordered_map` resuelve colisiones usando **encadenamiento** (chaining): cada casillero contiene una lista enlazada de pares `{clave, valor}`. Cuando buscas una clave, primero calculas el hash para encontrar el casillero, luego recorres la lista corta del casillero. En promedio, cada casillero tiene ~1 elemento, por lo que la búsqueda es **O(1)** (tiempo constante). En el peor caso degenerado (todas las claves caen en el mismo casillero), sería O(N).

---

# 4. DISECCIÓN INDUSTRIAL DE LOS ARCHIVOS DEL MOTOR

## 4.1 Track.hpp — La Entidad Fundamental

### A) Propósito de Diseño

`Track.hpp` define las dos caras de una canción:
- **`Track`** (clase C++): Para uso interno del motor. Usa `std::string` para comodidad y seguridad.
- **`TrackC`** (estructura POD): Para exportar datos a Python. Usa arreglos fijos `char[512]` para que `ctypes` pueda calcular los desplazamientos en bytes.

No depende de ningún otro archivo del motor (es la hoja del árbol de dependencias).

### B) Análisis del Código

El constructor por defecto inicializa los campos numéricos a cero:
```cpp
Track() : identificador(0), duracion(0.0) {}
```
Los `std::string` se inicializan automáticamente como cadenas vacías `""` por su propio constructor por defecto.

El método `a_estructura_c()` realiza la conversión (aplanamiento):
```cpp
std::strncpy(c.titulo, titulo.c_str(), LONGITUD_MAXIMA_CADENA - 1);
c.titulo[LONGITUD_MAXIMA_CADENA - 1] = '\0';
```
`strncpy` copia hasta 511 caracteres del `std::string` al arreglo fijo y luego fuerza un carácter nulo `'\0'` al final. Esto previene un **Buffer Overflow** (desbordamiento de búfer): si el título tuviera 600 caracteres, `strncpy` solo copiaría 511 y el `'\0'` garantiza que Python no lea basura de memoria.

### C) Anatomía de la Memoria

```
Track (en el Stack o Heap, dependiendo de quién lo crea):
┌─────────────────────────────────────────────────────┐
│ identificador (int32_t)        │  4 bytes  │ STACK  │
│ titulo (std::string cáscara)   │ ~32 bytes │ STACK  │
│   └─> búfer interno ──────────>│ N bytes   │ HEAP   │
│ artista (std::string cáscara)  │ ~32 bytes │ STACK  │
│   └─> búfer interno ──────────>│ N bytes   │ HEAP   │
│ album (std::string cáscara)    │ ~32 bytes │ STACK  │
│ duracion (double)              │  8 bytes  │ STACK  │
│ ruta (std::string cáscara)     │ ~32 bytes │ STACK  │
│   └─> búfer interno ──────────>│ N bytes   │ HEAP   │
└─────────────────────────────────────────────────────┘

TrackC (estructura plana, contigua, sin punteros al Heap):
┌─────────────────────────────────────────────────────┐
│ identificador (int32_t)        │    4 bytes          │
│ titulo[512]                    │  512 bytes          │
│ artista[512]                   │  512 bytes          │
│ album[512]                     │  512 bytes          │
│ duracion (double)              │    8 bytes          │
│ ruta[512]                      │  512 bytes          │
│ TOTAL por TrackC               │ ~2060 bytes         │
└─────────────────────────────────────────────────────┘
```

## 4.2 AudioPlayer.hpp / AudioPlayer.cpp — El Controlador del Hardware

### A) Propósito de Diseño

`AudioPlayer` es la interfaz directa entre el software y la tarjeta de sonido física. Encapsula dos objetos pesados de miniaudio: un **decodificador** (`ma_decoder`) que lee archivos .mp3/.wav del disco y los convierte en muestras PCM crudas, y un **dispositivo** (`ma_device`) que representa la tarjeta de sonido y envía esas muestras al kernel de Linux.

Depende de: `miniaudio.h`, `<atomic>`, `<string>`.

### B) Análisis del Código de Bajo Nivel

**El Callback de Audio — La Función Más Crítica del Sistema:**

```cpp
void AudioPlayer::callback_audio(ma_device* puntero_dispositivo, void* puntero_salida,
                                  const void* puntero_entrada, ma_uint32 conteo_marcos) {
    AudioPlayer* reproductor = static_cast<AudioPlayer*>(puntero_dispositivo->pUserData);
    reproductor->procesar_audio(puntero_salida, conteo_marcos);
}
```

Esta función es invocada por un **hilo del kernel** de altísima prioridad creado por miniaudio. El parámetro `puntero_salida` es un puntero a una zona de memoria que el kernel mapeó directamente al búfer DMA de la tarjeta de sonido. Tu código debe llenar esa zona con muestras de audio.

**Protección Anti-Zumbidos:**

```cpp
if (!decodificador_inicializado || !reproduciendo) {
    std::memset(puntero_salida, 0, conteo_marcos * bytes_por_marco);
    return;
}
```

`std::memset(ptr, 0, bytes)` escribe ceros binarios en cada byte del búfer de salida. Si no hiciéramos esto, el búfer contendría **basura de memoria** (valores aleatorios que quedaron de operaciones anteriores), que la tarjeta de sonido interpretaría como ondas de audio y reproduciría como zumbidos eléctricos violentos.

**Detección de Fin de Canción:**

```cpp
if (marcos_leidos < conteo_marcos) {
    reproduciendo = false;
    // Llenar el sobrante con silencio
    std::memset(puntero_salida_bytes + (marcos_leidos * bytes_por_marco), 0, ...);
    if (cancion_terminada) {
        *cancion_terminada = true;  // Notificación atómica al Engine
    }
}
```

Cuando el decodificador retorna menos marcos de los solicitados, significa que llegó al EOF (End Of File) del archivo de audio. El código llena el espacio sobrante con ceros (silencio) y levanta la bandera atómica `cancion_terminada`.

### C) Anatomía de la Memoria

```
AudioPlayer (instancia dentro de Engine, en el Heap):
┌──────────────────────────────────────────────────────┐
│ ma_decoder decodificador    │ ~600-800 bytes  │ AQUÍ │
│  └─> búfer interno decodif. │ ~64KB           │ HEAP │
│ ma_device dispositivo       │ ~400-600 bytes  │ AQUÍ │
│  └─> búfer de audio ring    │ variable        │ HEAP │
│ dispositivo_inicializado    │ 1 byte (bool)   │ AQUÍ │
│ decodificador_inicializado  │ 1 byte (bool)   │ AQUÍ │
│ reproduciendo               │ 1 byte (bool)   │ AQUÍ │
│ volumen                     │ 4 bytes (float) │ AQUÍ │
│ cancion_terminada (ptr)     │ 8 bytes         │ AQUÍ │
│  └─> apunta a ──────────── │ Engine.cancion_terminada │
└──────────────────────────────────────────────────────┘
```

### D) Concurrencia

`AudioPlayer` opera en **dos hilos simultáneos**:

1. **Hilo Principal** (el de tu programa): Llama a `cargar_archivo()`, `reproducir()`, `pausar()`.
2. **Hilo de Audio** (creado por miniaudio): Invoca `callback_audio()` cada ~5ms.

La variable `cancion_terminada` es un `std::atomic<bool>*`. Las operaciones atómicas usan instrucciones especiales de la CPU (`lock cmpxchg` en x86) que garantizan que la escritura es visible para todos los hilos instantáneamente, sin necesidad de un mutex pesado.

**Riesgo Latente:** La variable `reproduciendo` (un `bool` no atómico) se lee en el hilo de audio y se escribe en el hilo principal. Estrictamente, esto es una **condición de carrera** (Data Race), aunque en la práctica es benigna en x86 porque las lecturas/escrituras de `bool` son naturalmente atómicas en esa arquitectura. Para máxima corrección, debería ser `std::atomic<bool>`.

## 4.3 PlaybackState.hpp / PlaybackState.cpp — Módulo Reservado

### A) Propósito

`PlaybackState` fue diseñado originalmente para encapsular el estado concurrente del reproductor (banderas atómicas como "pista terminada" y "progreso en segundos"). Sin embargo, esta funcionalidad fue absorbida directamente por `Engine.hpp` y `AudioPlayer.hpp` usando variables atómicas integradas.

Tanto el `.hpp` como el `.cpp` son **stubs** (marcadores de posición) que no contienen lógica ejecutable. Existen en el proyecto para mantener la integridad del sistema de archivos y prevenir errores del enlazador si `CMakeLists.txt` los referencia.

## 4.4 QueueManager.hpp / QueueManager.cpp — El Director de la Cola de Reproducción

### A) Propósito de Diseño

`QueueManager` es el cerebro que decide QUÉ canción suena a continuación. Gestiona la cola de reproducción usando una `ListaDoblementeEnlazada<Track>` e implementa dos modos:
- **Secuencial**: Las canciones se reproducen en el orden del catálogo.
- **Aleatorio Ponderado**: Las canciones con más estrellas (calificación del usuario activo) tienen más probabilidad de aparecer antes.

Depende de: `Track.hpp`, `DoublyLinkedList.hpp`, `<unordered_map>`.

### B) Análisis del Algoritmo de Barajado Ponderado

Este algoritmo es la joya académica del motor. Funciona así:

1. Se copia toda la biblioteca a una "piscina" temporal.
2. Se calcula el **peso total** sumando los pesos de todas las canciones en la piscina.
3. Se genera un número aleatorio entre 0 y peso_total-1.
4. Se recorre la piscina acumulando pesos. Cuando el acumulado supera al número aleatorio, esa canción es la elegida.
5. Se extrae la canción de la piscina y se inserta en la cola.
6. Se repite hasta vaciar la piscina.

```
Ejemplo con 3 canciones:
  "Bohemian" (3★ = peso 6)
  "Hotel"    (1★ = peso 1)
  "Stairway" (2★ = peso 3)

  Peso total = 6 + 1 + 3 = 10
  Número aleatorio = 7

  Acumulado: 6 (Bohemian) → 7 ≤ 6? NO
  Acumulado: 7 (Hotel)    → 7 ≤ 7? SÍ → "Hotel" sale primero

  Pero "Bohemian" tenía 6/10 = 60% de probabilidad de salir primero.
  "Hotel" tenía 1/10 = 10%. "Stairway" tenía 3/10 = 30%.
```

Complejidad del algoritmo completo: **O(N²)** en el peor caso, porque por cada una de las N canciones, recorremos la piscina (que se encoge). Para catálogos típicos de música personal (~500-5000 canciones), esto toma menos de un segundo.

### C) Lógica de Rescate al Cambiar de Modo

Cuando el usuario presiona "Shuffle" mientras suena una canción, `alternar_modo_aleatorio()` debe:
1. Guardar el ID de la canción actual.
2. Destruir la cola completa y reconstruirla (aleatoria o secuencial).
3. Buscar en la nueva cola el nodo con ese ID y reposicionar el cursor `actual`.

Esto garantiza que la canción que suena no se interrumpa al cambiar de modo.

## 4.5 LibraryManager.hpp / LibraryManager.cpp — La Base de Datos en Memoria

### A) Propósito de Diseño

`LibraryManager` es el administrador del catálogo maestro de canciones. Carga `database/library.json` al arrancar, mantiene las canciones indexadas en memoria para búsquedas rápidas, y puede mutar el catálogo cuando el `DirectoryScanner` descubre canciones nuevas o eliminadas.

Depende de: `Track.hpp`, `nlohmann/json.hpp`, `<unordered_map>`, `<unordered_set>`.

### B) Sistema de Índices

`LibraryManager` mantiene tres estructuras de acceso:

```
1. biblioteca (std::vector<Track>)
   → Almacenamiento principal. Acceso por posición O(1).
   Búsqueda por ID o título: O(N) si solo usamos el vector.

2. indice_por_id (std::unordered_map<int32_t, size_t>)
   → Tabla hash: {ID_canción → posición_en_vector}
   Búsqueda por ID: O(1) promedio.

3. indice_por_titulo (std::multimap<std::string, size_t>)
   → Árbol rojo-negro: {título → posición_en_vector}
   Búsqueda por título: O(log N).
   Es "multi" porque puede haber canciones con el mismo título.
```

Cuando se agrega o elimina una canción, se llama a `reconstruir_indices()` que destruye ambos índices y los reconstruye desde cero en O(N). Esto es correcto porque las mutaciones son infrecuentes (solo al sincronizar con el disco).

### C) Mapeo JSON Bidireccional

El código implementa una traducción explícita entre las llaves en inglés del JSON y las variables en español del código C++:

```
JSON (disco)    ↔    C++ (memoria)
─────────────────────────────────
"id"           →    identificador
"title"        →    titulo
"artist"       →    artista
"album"        →    album
"duration"     →    duracion
"path"         →    ruta
```

Este mapeo ocurre en `cargar_desde_json()` (lectura) y `guardar_en_json()` (escritura).

### D) Generador de IDs Secuenciales

```cpp
int32_t siguiente_id;
```

Al cargar el JSON, se busca el ID más alto existente y se suma 1. Esto garantiza que las canciones nuevas descubiertas por el escáner nunca colisionen con IDs existentes.

## 4.6 UserManager.hpp / UserManager.cpp — El Gestor de Perfiles

### A) Propósito de Diseño

`UserManager` gestiona los perfiles de usuario locales. Cada perfil contiene:
- Favoritos (pistas con "like")
- Álbumes personalizados (playlists)
- **Calificaciones por pista** (las estrellas, que antes vivían globalmente en `Track`)

Depende de: `nlohmann/json.hpp`, `<unordered_map>`, `<set>`, `<map>`.

### B) Estructura del Perfil en Memoria

```
PerfilUsuario (en el Heap, dentro de la tabla hash):
┌───────────────────────────────────────────────────────────────────┐
│ identificador (int32_t)                           │    4 bytes   │
│ nombre (std::string)                              │   ~32 bytes  │
│   └─> "Diego" ─────────────────────────────────── │ HEAP (SSO)   │
│ pistas_favoritas (std::set<int32_t>)              │   ~48 bytes  │
│   └─> Árbol rojo-negro: {3, 17, 42}              │ HEAP (nodos) │
│ albumes_personalizados (std::map<string,vector>)  │   ~48 bytes  │
│   └─> Árbol: {"Rock": [1,3,5], "Jazz": [2,4]}    │ HEAP (nodos) │
│ calificaciones_pistas (std::unordered_map)        │   ~56 bytes  │
│   └─> Tabla Hash: {42→3, 17→2, 3→1}              │ HEAP (buckets)│
└───────────────────────────────────────────────────────────────────┘
```

La `tabla_usuarios` principal es `std::unordered_map<std::string, PerfilUsuario>`. Cada perfil se busca por nombre en O(1) promedio.

### C) Puntero al Usuario Activo

```cpp
PerfilUsuario* usuario_activo;
```

Este es un **puntero crudo** (raw pointer) de 8 bytes que apunta directamente al `PerfilUsuario` que está dentro de la tabla hash. **Riesgo:** Si la tabla hash se rehashea (cuando crece internamente al agregar más usuarios), todos los punteros a elementos existentes se **invalidan** porque los elementos se mueven a nuevas posiciones en memoria. Si `usuario_activo` apuntaba a un perfil y luego se inserta otro usuario que causa un rehash, `usuario_activo` se convierte en un **Dangling Pointer** (puntero colgante). En la práctica, la creación de usuarios es extremadamente infrecuente, pero es una vulnerabilidad latente.

## 4.7 DirectoryScanner.hpp / DirectoryScanner.cpp — El Explorador del Disco Duro

### A) Propósito de Diseño

`DirectoryScanner` es el componente autónomo que le permite al motor C++ descubrir música por sí mismo, sin depender de que Python le pase las rutas. Usa `std::filesystem` de C++17 para interactuar con el sistema de archivos del kernel de Linux.

Depende de: `LibraryManager.hpp`, `<filesystem>`.

### B) Algoritmo de Sincronización Diferencial

```
PASO 1: Buscar carpetas de música en $HOME
  ├─ Iterar primer nivel de /home/diego/
  ├─ Comparar cada nombre con variaciones ("Music", "Música", "musica"...)
  └─ Almacenar las rutas encontradas

PASO 2: Escanear recursivamente las carpetas encontradas
  ├─ Usar std::filesystem::recursive_directory_iterator
  ├─ Filtrar por extensiones (.mp3, .wav, .flac, .ogg, .m4a)
  └─ Almacenar todas las rutas en un std::unordered_set (rutas_en_disco)

PASO 3: Obtener las rutas del LibraryManager
  └─ biblioteca.obtener_conjunto_rutas() → std::unordered_set (rutas_en_biblioteca)

PASO 4: Diferencial de INSERCIÓN
  ├─ Para cada ruta_en_disco:
  │   └─ Si NO está en rutas_en_biblioteca → CANCIÓN NUEVA → agregar
  └─ Complejidad: O(N) donde N = canciones en disco

PASO 5: Diferencial de ELIMINACIÓN
  ├─ Para cada ruta_en_biblioteca:
  │   └─ Si NO está en rutas_en_disco → CANCIÓN HUÉRFANA → eliminar
  └─ Complejidad: O(M) donde M = canciones en biblioteca

PASO 6: Persistir SOLO si hubo cambios
  └─ if (hubo_cambios) → biblioteca.guardar_en_json();
```

Las búsquedas de pertenencia (`count()`) en `std::unordered_set` son **O(1)** promedio gracias al hashing, lo que hace que la sincronización total sea **O(N + M)** — lineal y extremadamente eficiente.

### C) Detección del Home del Usuario

```cpp
const char* home = std::getenv("HOME");
```

`std::getenv()` consulta las **variables de entorno** del proceso. Estas son cadenas de texto que el sistema operativo inyecta en el espacio de memoria del proceso al crearlo. `$HOME` típicamente vale `/home/diego` en Linux. El puntero retornado apunta a memoria gestionada por el sistema operativo; no debes hacer `delete` ni `free` sobre él.

## 4.8 SpectrumAnalyzer.hpp / SpectrumAnalyzer.cpp — Módulo Delegado

### A) Propósito

Originalmente diseñado para realizar la Transformada Rápida de Fourier (FFT) sobre el audio y generar barras de ecualización. Sin embargo, esta funcionalidad fue delegada completamente a Python, que usa el binario externo **CAVA** en un subproceso asíncrono para renderizar las barras del espectro en la terminal usando Textual y Rich.

Ambos archivos son stubs vacíos que previenen errores de enlazado.

## 4.9 Engine.hpp / Engine.cpp — El Orquestador Central

### A) Propósito de Diseño

`Engine` es la **fachada** (Facade Pattern) que unifica todos los subsistemas. Posee instancias de `LibraryManager`, `QueueManager`, `UserManager` y `AudioPlayer` como miembros privados. Toda la lógica de coordinación (cargar canción → decodificar → reproducir → detectar fin → avanzar) se centraliza aquí.

Depende de: Todos los módulos del motor.

### B) Ciclo de Vida del Motor

```
┌─────────────────────────────────────────────────────────────────┐
│                   DIAGRAMA DE ESTADOS DEL ENGINE                │
│                                                                 │
│  engine_create()        engine_initialize()     engine_play()   │
│       │                       │                      │          │
│       ▼                       ▼                      ▼          │
│  ┌─────────┐           ┌───────────┐          ┌──────────┐     │
│  │ CREADO  │──────────>│INICIALIZADO│────────>│REPRODUCIENDO│   │
│  │(no init)│           │(JSON cargado│        │(audio activo)│  │
│  └─────────┘           │cola lista) │        └──────┬───────┘  │
│                        └───────────┘               │           │
│                              ▲            pause()  │           │
│                              │              │      │           │
│                              │              ▼      │           │
│                        ┌───────────┐  ┌──────────┐ │           │
│                        │           │<─│ PAUSADO  │<┘           │
│                        │           │  └──────────┘             │
│                        └───────────┘       │ play()            │
│                              ▲             │(reanuda sin       │
│                              │             │ recargar archivo) │
│                              └─────────────┘                   │
│                                                                 │
│  engine_destroy() → detiene hilo → libera audio → delete       │
└─────────────────────────────────────────────────────────────────┘
```

### C) El Hilo de Monitoreo — Concurrencia en Profundidad

```cpp
Engine::Engine() : ... {
    reproductor_audio.asociar_bandera_fin(&cancion_terminada);
    hilo_monitoreo = std::thread(&Engine::ciclo_monitoreo_pistas, this);
}
```

Al construir el `Engine`, se crea un **hilo secundario** (`std::thread`) que ejecuta `ciclo_monitoreo_pistas()` en paralelo al hilo principal. Este hilo duerme 50ms, se despierta, revisa la bandera atómica `cancion_terminada` y, si es `true`, avanza a la siguiente canción.

```
HILO PRINCIPAL (Python/ctypes)        HILO DE MONITOREO         HILO DE AUDIO (miniaudio)
        │                                    │                          │
        │ engine_play()                      │                          │
        │────────────────>                   │                          │
        │ lock(mutex)                        │                          │
        │ reproductor.reproducir()           │                          │
        │ unlock(mutex)                      │                          │
        │                                    │                          │
        │                                    │ sleep(50ms)              │
        │                                    │ ¿cancion_terminada?      │
        │                                    │ → NO → dormir            │
        │                                    │                          │
        │                                    │                          │ callback: lee PCM
        │                                    │                          │ marcos_leidos < pedidos
        │                                    │                          │ → EOF detectado
        │                                    │                          │ *cancion_terminada = true
        │                                    │                          │   (escritura atómica)
        │                                    │                          │
        │                                    │ sleep(50ms)              │
        │                                    │ ¿cancion_terminada?      │
        │                                    │ → SÍ                     │
        │                                    │ lock(mutex)              │
        │                                    │ cancion_terminada = false │
        │                                    │ avanzar_siguiente()      │
        │                                    │   → pausar audio         │
        │                                    │   → cargar nuevo archivo │
        │                                    │   → reproducir           │
        │                                    │ unlock(mutex)            │
```

### D) Protección con Mutex

Casi todos los métodos públicos de `Engine` usan:
```cpp
std::lock_guard<std::mutex> seguro(mutex_motor);
```

`std::lock_guard` es un objeto RAII que bloquea el mutex al construirse y lo desbloquea al destruirse (cuando la función retorna o sale del scope). Esto garantiza que solo un hilo a la vez pueda modificar el estado interno del motor.

**Bug Detectado:** El método `avanzar_siguiente()` NO adquiere el mutex:
```cpp
bool Engine::avanzar_siguiente() {
    if (!inicializado) return false;  // ← Sin lock_guard
    bool movido = administrador_cola.avanzar_siguiente();
    ...
}
```
Esto fue diseñado intencionalmente porque `avanzar_siguiente()` es llamado DESDE `ciclo_monitoreo_pistas()`, que ya posee el mutex. Si añadiéramos un `lock_guard` aquí, tendríamos un **Deadlock** (bloqueo mutuo): el hilo de monitoreo intenta adquirir un mutex que él mismo ya posee, quedándose bloqueado para siempre. Sin embargo, `avanzar_siguiente()` también se puede llamar desde `engine_next()` a través de `CApi.cpp`, que no pasa por `ciclo_monitoreo_pistas()`. En ese escenario, no estaría protegido.

**Bug en Engine.cpp — Inconsistencia con la API refactorizada:**
```cpp
void Engine::asignar_calificacion_pista(...) {
    administrador_biblioteca.asignar_calificacion(...);  // ← Este método ya NO EXISTE
}
```
Tras la refactorización, las calificaciones fueron trasladadas de `LibraryManager` a `UserManager`. Sin embargo, `Engine.cpp` aún llama a `administrador_biblioteca.asignar_calificacion()` que fue eliminado. Esto causará un **error de compilación**. La corrección es delegar a `administrador_usuarios.asignar_calificacion()`.

**Bug en Engine.cpp — `alternar_modo_aleatorio()` no pasa calificaciones:**
```cpp
void Engine::alternar_modo_aleatorio() {
    administrador_cola.alternar_modo_aleatorio(administrador_biblioteca.obtener_todas_las_canciones());
    // ← FALTA el segundo parámetro: mapa de calificaciones
}
```
Tras la refactorización, `QueueManager::alternar_modo_aleatorio()` requiere dos parámetros: la biblioteca Y el mapa de calificaciones. `Engine.cpp` solo pasa uno, lo que causará un **error de compilación**.

---

# 5. EL PUENTE E INTERFAZ BINARIA A PYTHON

## 5.1 CApi.hpp / CApi.cpp — La Frontera Binaria

### A) Propósito de Diseño

`CApi` es el traductor entre dos mundos: el código C++ orientado a objetos (con clases, métodos, herencia y Name Mangling) y el código C plano que Python puede consumir a través de `ctypes`.

### B) ¿Por qué Python no puede leer objetos C++ directamente?

Cuando el compilador de C++ compila una función como:
```cpp
void Engine::reproducir();
```
El nombre que genera en el binario NO es `reproducir`. Debido al **Name Mangling** (mutilación de nombres), el compilador transforma el nombre a algo como `_ZN6Engine10reproducirEv` para codificar el nombre de la clase, el nombre del método y los tipos de los parámetros. Cada compilador (GCC, Clang, MSVC) usa un esquema de mangling diferente.

Python, usando `ctypes`, carga la librería `.so` y busca funciones por nombre exacto:
```python
motor_lib.engine_play(puntero)
```
Si el nombre en el binario es `_ZN6Engine10reproducirEv`, Python simplemente no lo encuentra.

La solución es `extern "C"`:
```cpp
extern "C" {
    void engine_play(void* puntero_motor) { ... }
}
```
`extern "C"` le dice al compilador: "No mutiles este nombre. Usa la convención de nombres de C, que es simplemente el nombre tal cual". Así, en el binario el símbolo será exactamente `engine_play`, y Python lo encontrará sin problemas.

### C) El Puntero Opaco `void*`

```cpp
void* engine_create() {
    return static_cast<void*>(new Engine());
}
```

`void*` es un puntero "sin tipo": simplemente almacena una dirección de memoria (8 bytes en sistemas de 64 bits) sin saber qué hay en esa dirección. Python lo recibe como un número entero (la dirección de memoria) y lo reenvía en cada llamada posterior:

```python
puntero = motor_lib.engine_create()        # Python recibe un entero: 0x55A3B7C00000
motor_lib.engine_play(puntero)             # Python envía ese entero de vuelta
motor_lib.engine_destroy(puntero)          # C++ convierte: static_cast<Engine*>(puntero)
```

En C++, `static_cast<Engine*>(puntero)` convierte ese número crudo de vuelta a un puntero tipado que permite acceder a los métodos del `Engine`.

### D) Aplanamiento de Memoria — Plain Old Data (POD)

`std::string` de C++ es un objeto complejo: contiene un puntero interno al Heap, un tamaño y una capacidad. Su layout exacto en bytes depende del compilador y la versión de la STL. Python no puede leer esto de forma segura.

La solución es `TrackC`: una estructura con arreglos fijos de caracteres:

```
TrackC en memoria RAM (ejemplo de una canción):
Dirección   Contenido                        Campo
─────────────────────────────────────────────────────
0x0000      2A 00 00 00                      identificador = 42
0x0004      42 6F 68 65 6D 69 61 6E 20 52    titulo = "Bohemian R..."
            68 61 70 73 6F 64 79 00 00 00    (512 bytes, relleno con 0x00)
            ... (hasta byte 0x0203)
0x0204      51 75 65 65 6E 00 00 00 ...      artista = "Queen"
            ... (512 bytes)
0x0404      41 20 4E 69 67 68 74 ...         album = "A Night..."
            ... (512 bytes)
0x0604      00 00 00 00 D0 46 72 40          duracion = 354.67 (double, 8 bytes)
0x060C      2F 68 6F 6D 65 2F ...            ruta = "/home/..."
            ... (512 bytes)
```

Python en `bridge.py` declararía:
```python
class TrackC(ctypes.Structure):
    _fields_ = [
        ("identificador", ctypes.c_int32),
        ("titulo",        ctypes.c_char * 512),
        ("artista",       ctypes.c_char * 512),
        ("album",         ctypes.c_char * 512),
        ("duracion",      ctypes.c_double),
        ("ruta",          ctypes.c_char * 512),
    ]
```

`ctypes` calcula los desplazamientos (offsets) en bytes exactos: `identificador` está en el byte 0, `titulo` empieza en el byte 4, `artista` en el byte 516, etc. Como la estructura es **contigua y predecible**, Python puede leer la memoria cruda del `.so` sin ningún riesgo de corrupción.

### E) Bugs Detectados en CApi.cpp

**Bug de coherencia con la refactorización:**
```cpp
void engine_set_rating(void* puntero_motor, int32_t identificador_pista, int32_t estrellas) {
    static_cast<Engine*>(puntero_motor)->asignar_calificacion_pista(identificador_pista, estrellas);
}
```
Este método delega a `Engine::asignar_calificacion_pista()`, que a su vez llama a `administrador_biblioteca.asignar_calificacion()` — un método que ya no existe tras la refactorización. La cadena completa debe actualizarse para delegar a `administrador_usuarios.asignar_calificacion()`.

**Funciones faltantes en la C-API:**
Las siguientes funciones fueron declaradas como necesarias en el reporte de arquitectura pero aún no están implementadas en `CApi.hpp/.cpp`:
- `engine_has_users()` — ¿Hay usuarios registrados?
- `engine_create_user()` — Crear un perfil nuevo
- `engine_sync_directories()` — Disparar el escáner de archivos
- `engine_set_user_rating()` / `engine_get_user_rating()` — Calificaciones por usuario

---

> **FIN DEL ESTUDIO TÉCNICO**
>
> Este documento constituye la auditoría completa del motor nativo C++ del reproductor de música `vercion02`. Los bugs identificados en la Sección 4.9 y 5.E deben corregirse antes de intentar compilar el proyecto. La implementación de la Capa 3 (actualización de `Engine.cpp` y `CApi.cpp`) es el paso inmediato para completar la migración del backend de Python a C++.
