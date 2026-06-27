#include "../include/QueueManager.hpp"
#include <random>
#include <algorithm>
#include <ctime>
#include <iostream>

// Constructor por defecto
QueueManager::QueueManager() : modo_aleatorio(false), version_cola(1) {}

// Devuelve el peso de probabilidad de barajado según las estrellas de la canción
int QueueManager::obtener_peso_por_estrellas(int32_t estrellas) {
    if (estrellas <= 1) return 1;
    if (estrellas == 2) return 3;
    return 6; // Mayor peso (6x probabilidad) para 3 estrellas
}

// Inicializa la cola de forma lineal respetando el orden de la biblioteca
void QueueManager::inicializa_secuencial(const std::vector<Track>& biblioteca) {
    lista_cola.limpiar();
    for (const auto& cancion : biblioteca) {
        lista_cola.agregar_al_final(cancion);
    }
    version_cola++;
}

// Inicializa la cola de forma aleatoria ponderada
void QueueManager::inicializar_aleatoria(const std::vector<Track>& biblioteca) {
    if (biblioteca.empty()) return;
    lista_cola.limpiar();

    std::vector<Track> piscina_canciones = biblioteca;
    std::mt19937 generador(static_cast<unsigned int>(std::time(nullptr)));

    // BARAJADO PONDERADO:
    // Extraemos una por una las canciones de la piscina. La probabilidad de extraer 
    // cada canción depende de su peso (estrellas). Una vez extraída, se elimina de 
    // la piscina para evitar repeticiones en la misma cola.
    while (lista_cola.obtener_tamanio() < biblioteca.size() && !piscina_canciones.empty()) {
        int peso_total = 0;
        for (const auto& cancion : piscina_canciones) {
            peso_total += obtener_peso_por_estrellas(cancion.estrellas);
        }

        std::uniform_int_distribution<int> distribucion(0, peso_total - 1);
        int valor_aleatorio = distribucion(generador);

        int peso_acumulado = 0;
        for (auto iterador = piscina_canciones.begin(); iterador != piscina_canciones.end(); iterador++) {
            peso_acumulado += obtener_peso_por_estrellas(iterador->estrellas);

            if (valor_aleatorio < peso_acumulado) {
                lista_cola.agregar_al_final(*iterador);
                piscina_canciones.erase(iterador); // O(N) borrado seguro al salir con break
                break;
            }
        }
    }
    version_cola++;
}

// Cambia el modo y preserva sutilmente la canción reproduciéndose
void QueueManager::alternar_modo_aleatorio(const std::vector<Track>& biblioteca) {
    // LÓGICA CRÍTICA: Rescatar la canción actual antes de destruir la lista
    Track* cancion_previa = obtener_cancion_actual();
    int32_t id_previo = cancion_previa ? cancion_previa->identificador : -1;

    modo_aleatorio = !modo_aleatorio;

    if (modo_aleatorio) {
        inicializar_aleatoria(biblioteca);
    } else {
        inicializa_secuencial(biblioteca);
    }

    // Buscar y re-posicionar el iterador 'actual' en la nueva cola
    if (id_previo != -1) {
        std::vector<Track> canciones_nuevas = lista_cola.a_vector();
        for (size_t i = 0; i < canciones_nuevas.size(); ++i) {
            if (canciones_nuevas[i].identificador == id_previo) {
                lista_cola.saltar_a_indice(i);
                break;
            }
        }
    }
}

// Avanza a la siguiente canción en la lista doblemente enlazada (circular)
bool QueueManager::avanzar_siguiente() {
    if (lista_cola.obtener_tamanio() == 0) {
        return false;
    }
    return lista_cola.mover_siguiente();
}

// Retrocede a la anterior canción en la lista doblemente enlazada (circular)
bool QueueManager::retroceder_anterior() {
    if (lista_cola.obtener_tamanio() == 0) {
        return false;
    }
    return lista_cola.mover_anterior();
}

// Realiza un salto directo por índice a un nodo específico en O(N/2)
bool QueueManager::saltar_a_posicion(size_t indice) {
    return lista_cola.saltar_a_indice(indice);
}

// Obtiene el puntero a la canción posicionada
Track* QueueManager::obtener_cancion_actual() {
    return lista_cola.obtener_elemento_actual();
}

// Retorna la posición numérica del nodo actual
size_t QueueManager::obtener_indice_actual() const {
    return lista_cola.obtener_indice_actual();
}

// Retorna el tamaño total de la cola
size_t QueueManager::obtener_tamanio_cola() const {
    return lista_cola.obtener_tamanio();
}

// Retorna la versión para que Python repinte
int32_t QueueManager::obtener_version_cola() const {
    return version_cola;
}

// Indica si está en shuffle
bool QueueManager::es_modo_aleatorio() const {
    return modo_aleatorio;
}

// Limpia el almacenamiento de nodos
void QueueManager::limpiar_cola() {
    lista_cola.limpiar();
    version_cola++;
}

// Genera un vector plano de structs C para enviar a Python
std::vector<TrackC> QueueManager::obtener_snapshot_cola() const {
    std::vector<Track> canciones_planas = lista_cola.a_vector();
    std::vector<TrackC> resultado;
    resultado.reserve(canciones_planas.size());

    for (const auto& cancion : canciones_planas) {
        resultado.push_back(cancion.a_estructura_c());
    }
    return resultado;
}
