cmake_minimum_required(VERSION 3.12)
project(music_engine CXX)

# Establecer estándar C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Incluir los directorios de cabecera e implementaciones de terceros
include_directories(include third_party)

# Buscar y listar todos los archivos fuentes .cpp recursivamente en src/
file(GLOB FUENTES 
    "src/*.cpp"
)

# REGLA DE EXCLUSIÓN: 
# DoublyLinkedList.cpp debe ser excluido. Al ser una estructura de datos plantilla (template),
# su código e implementación deben compilarse bajo demanda por cada tipo instanciado
# y residir en DoublyLinkedList.hpp para prevenir errores de enlazado ("undefined reference").
list(REMOVE_ITEM FUENTES "${CMAKE_CURRENT_SOURCE_DIR}/src/DoublyLinkedList.cpp")

# Generar la librería compartida (.so en Linux, .dll en Windows)
add_library(music_engine SHARED ${FUENTES})

# Buscar y enlazar soporte nativo para hilos en el SO (pthread)
find_package(Threads REQUIRED)
target_link_libraries(music_engine PRIVATE Threads::Threads)
