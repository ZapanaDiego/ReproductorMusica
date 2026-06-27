/*
===========================================================================
ARCHIVO: DoublyLinkedList.cpp

NOTA DE DISEÑO Y COMPILACIÓN (C++ TEMPLATES):
Este archivo existe únicamente por motivos de organización de archivos en la 
carpeta src/. Debido a que ListaDoblementeEnlazada es una clase plantilla 
(Template), toda su lógica y código ejecutable reside al 100% en el archivo 
de cabecera "DoublyLinkedList.hpp".

En C++, las plantillas no se compilan de manera independiente como código de 
objeto (.o), sino que el compilador las instancia en tiempo de compilación 
bajo demanda al detectar los tipos concretos (ej: ListaDoblementeEnlazada<Track>).
Si se implementaran los métodos en este archivo .cpp de forma tradicional, 
el linker arrojaría un error de tipo "referencia no definida" (undefined reference) 
al intentar enlazar el motor dinámico.
===========================================================================
*/

#include "../include/DoublyLinkedList.hpp"
