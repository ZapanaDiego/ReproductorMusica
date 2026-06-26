#ifndef DOUBLY_LINKED_LIST_HPP
#define DOUBLY_LINKED_LIST_HPP

#include <cstddef>
#include <vector>
#include <utility>

template <typename T>
struct DLLNode{
    T dato;
    DLLNode<T>* anterior;
    DLLNode<T>* siguiente;

    explicit DLLNode(T valor) : dato(std::move(valor)), anterior(nullptr), siguiente(nullptr) {}

};

template <typename T>
class DoublyLinkedList{

private:
    DLLNode<T>* cabeza;
    DLLNode<T>* cola;
    DLLNode<T>* actual;
    size_t tamanio;

public:
    DoublyLinkedList() : cabeza(nullptr), cola(nullptr), actual(nullptr), tamanio(0) {}

    ~DoublyLinkedList (){
        clear();
    }

    void push_back(T elemento){
        DLLNode<T>* nuevo_nodo = new DLLNode<T>(std::move(elemento));

        if(!cabeza){
            cabeza = nuevo_nodo;
            cola = nuevo_nodo;
            actual = nuevo_nodo;
        }else{
            cola->siguiente = nuevo_nodo;
            nuevo_nodo->anterior = cola;
            cola = nuevo_nodo;
        }
        tamanio++;
    }

    void clear(){
        DLLNode<T>* iterador = cabeza;
        while(iterador != nullptr){
            DLLNode<T>* siguiente_nodo = iterador->siguiente;
            delete iterador;
            iterador = siguiente_nodo;
        }
        cabeza = nullptr;
        cola = nullptr;
        actual = nullptr;
        tamanio = 0;
    }

    T* obtener_item_actual(){
        if(!actual){
            return nullptr;
        }
        return &(actual->dato);
    }

    bool mover_siguiente(){
        if(!cabeza){
            return false;
        }

        if(!actual || !actual->siguiente){
            actual = cabeza;
        }else{
            actual = actual->siguiente;
        }
        return true;
    }

    bool mover_anterior(){
        if(!cabeza){
            return false;
        }

        if(!actual || !actual->anterior){
            actual = cola; //comportamiento circular salta al final de la cola
        }else{
            actual = actual->anterior;
        }
        return true;
    }

    bool saltar_a_indice(size_t indice){
        if(indice >= tamanio){
            return false;
        }

        if(indice < tamanio /2 ){
            DLLNode<T>* iterador = cabeza;
            for(size_t i = 0; i<indice; i++){
                iterador = iterador->siguiente;
            }
            actual = iterador;
        }else{
            DLLNode<T>* iterador = cola;
            for(size_t i = tamanio - 1; i>indice; i--){
                iterador = iterador->anterior;
            }
            actual = iterador;
        }
        return true;
    }


    size_t obtener_indice_actual() const{
        if(!actual){
            return 0;
        }
        size_t indice = 0;
        DLLNode<T>* iterador = cabeza;
        while (iterador != actual && iterador != nullptr){
            iterador =  iterador->siguiente;
            indice++;
        }
        return indice;
    }



    size_t obtener_tamanio() const{
        return tamanio;
    }

    std::vector<T> a_vector() const{
        std::vector<T> resultado;
        resultado.reserve(tamanio);
        DLLNode<T>* iterador = cabeza;
        while (iterador != nullptr){
            resultado.push_back(iterador->dato);
            iterador = iterador->siguiente;
        }
        return resultado;
    }
};


#endif