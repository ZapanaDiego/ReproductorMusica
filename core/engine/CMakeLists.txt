cmake_minimum_required(VERSION 3.12)
project(music_engine CXX)

# Estándar C++17 requerido para std::filesystem
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Directorios de cabeceras propias y de terceros
include_directories(include third_party)

# Listar todos los archivos fuente en src/
file(GLOB FUENTES 
    "src/*.cpp"
)

# EXCLUSIÓN: DoublyLinkedList.cpp es un stub vacío (la lógica vive en el .hpp por ser template)
list(REMOVE_ITEM FUENTES "${CMAKE_CURRENT_SOURCE_DIR}/src/DoublyLinkedList.cpp")

# Generar la librería compartida (.so en Linux)
add_library(music_engine SHARED ${FUENTES})

# Enlazar soporte nativo de hilos (pthread)
find_package(Threads REQUIRED)
target_link_libraries(music_engine PRIVATE Threads::Threads)

# Enlazar std::filesystem (necesario en algunos compiladores GCC < 9)
target_link_libraries(music_engine PRIVATE stdc++fs)
