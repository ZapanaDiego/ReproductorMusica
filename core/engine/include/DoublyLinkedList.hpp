#ifndef DOUBLY_LINKED_LIST_HPP
#define DOUBLY_LINKED_LIST_HPP

/*
===========================================================================
ARCHIVO: DoublyLinkedList.hpp

PROPÓSITO:
Define la estructura de datos académica "Lista Doblemente Enlazada".
Existe para gestionar la cola de reproducción musical, permitiendo avanzar
y retroceder canciones de manera eficiente (tiempo constante O(1)), y soportando 
comportamiento circular (volver al inicio al llegar al final).

CÓMO LO HACE:
Utiliza plantillas (templates) de C++ para poder almacenar cualquier tipo de 
dato (en este caso, canciones de tipo 'Track'). Cada nodo conoce a su 
elemento anterior y siguiente.

VARIABLES PRINCIPALES A USAR:
- cabeza (Nodo*): Puntero al primer elemento de la lista.
- cola (Nodo*): Puntero al último elemento de la lista.
- actual (Nodo*): Puntero al elemento en el que estamos posicionados (la canción sonando).
- tamanio (size_t): Cantidad total de elementos en la lista.
===========================================================================
*/

#include <cstddef>
#include <vector>
#include <utility>

template <typename T>
struct NodoListaDoble {
    T dato;
    NodoListaDoble<T>* anterior;
    NodoListaDoble<T>* siguiente;

    explicit NodoListaDoble(T valor) : dato(std::move(valor)), anterior(nullptr), siguiente(nullptr) {}
};

template <typename T>
class ListaDoblementeEnlazada {
private:
    NodoListaDoble<T>* cabeza;
    NodoListaDoble<T>* cola;
    NodoListaDoble<T>* actual;
    size_t tamanio;

public:
    ListaDoblementeEnlazada() : cabeza(nullptr), cola(nullptr), actual(nullptr), tamanio(0) {}

    ~ListaDoblementeEnlazada() {
        limpiar();
    }

    void agregar_al_final(T elemento) {
        NodoListaDoble<T>* nuevo_nodo = new NodoListaDoble<T>(std::move(elemento));

        if (!cabeza) {
            cabeza = nuevo_nodo;
            cola = nuevo_nodo;
            actual = nuevo_nodo;
        } else {
            cola->siguiente = nuevo_nodo;
            nuevo_nodo->anterior = cola;
            cola = nuevo_nodo;
        }
        tamanio++;
    }

    void limpiar() {
        NodoListaDoble<T>* iterador = cabeza;
        while (iterador != nullptr) {
            NodoListaDoble<T>* siguiente_nodo = iterador->siguiente;
            delete iterador;
            iterador = siguiente_nodo;
        }
        cabeza = nullptr;
        cola = nullptr;
        actual = nullptr;
        tamanio = 0;
    }

    T* obtener_elemento_actual() {
        if (!actual) {
            return nullptr;
        }
        return &(actual->dato);
    }

    bool mover_siguiente() {
        if (!cabeza) {
            return false;
        }

        if (!actual || !actual->siguiente) {
            actual = cabeza; // comportamiento circular salta al inicio
        } else {
            actual = actual->siguiente;
        }
        return true;
    }

    bool mover_anterior() {
        if (!cabeza) {
            return false;
        }

        if (!actual || !actual->anterior) {
            actual = cola; // comportamiento circular salta al final
        } else {
            actual = actual->anterior;
        }
        return true;
    }

    bool saltar_a_indice(size_t indice) {
        if (indice >= tamanio) {
            return false;
        }

        if (indice < tamanio / 2) {
            NodoListaDoble<T>* iterador = cabeza;
            for (size_t i = 0; i < indice; i++) {
                iterador = iterador->siguiente;
            }
            actual = iterador;
        } else {
            NodoListaDoble<T>* iterador = cola;
            for (size_t i = tamanio - 1; i > indice; i--) {
                iterador = iterador->anterior;
            }
            actual = iterador;
        }
        return true;
    }

    size_t obtener_indice_actual() const {
        if (!actual) {
            return 0;
        }
        size_t indice = 0;
        NodoListaDoble<T>* iterador = cabeza;
        while (iterador != actual && iterador != nullptr) {
            iterador = iterador->siguiente;
            indice++;
        }
        return indice;
    }

    size_t obtener_tamanio() const {
        return tamanio;
    }

    std::vector<T> a_vector() const {
        std::vector<T> resultado;
        resultado.reserve(tamanio);
        NodoListaDoble<T>* iterador = cabeza;
        while (iterador != nullptr) {
            resultado.push_back(iterador->dato);
            iterador = iterador->siguiente;
        }
        return resultado;
    }
};

#endif