#include "../include/QueueManager.hpp"
#include <random>
#include <algorithm>
#include <ctime>
#include <iostream>

QueueManager::QueueManager() : modo_aleatorio(false), version_cola(1) {}

// Tabla de pesos para el barajado ponderado:
//   0-1 estrellas (o sin calificación) -> peso 1 (probabilidad base)
//   2 estrellas                        -> peso 3 (3x más probable)
//   3 estrellas                        -> peso 6 (6x más probable)
int QueueManager::obtener_peso_por_estrellas(int32_t estrellas) {
    if (estrellas <= 1) return 1;
    if (estrellas == 2) return 3;
    return 6;
}

// Inicializa la cola de forma lineal respetando el orden de la biblioteca
void QueueManager::inicializa_secuencial(const std::vector<Track>& biblioteca) {
    lista_cola.limpiar();
    for (const auto& cancion : biblioteca) {
        lista_cola.agregar_al_final(cancion);
    }
    version_cola++;
}

// Inicializa la cola con barajado ponderado.
// Las calificaciones se obtienen del mapa externo proporcionado por UserManager.
// Si una canción no tiene calificación en el mapa, se asume peso 1 (mínimo).
void QueueManager::inicializar_aleatoria(const std::vector<Track>& biblioteca,
                                          const std::unordered_map<int32_t, int32_t>& calificaciones) {
    if (biblioteca.empty()) return;
    lista_cola.limpiar();

    std::vector<Track> piscina_canciones = biblioteca;
    std::mt19937 generador(static_cast<unsigned int>(std::time(nullptr)));

    // ALGORITMO DE BARAJADO PONDERADO:
    // 1. Calculamos el peso total de todas las canciones en la piscina.
    // 2. Generamos un número aleatorio entre [0, peso_total).
    // 3. Recorremos la piscina acumulando pesos hasta superar el número.
    // 4. La canción que cause la superación es extraída e insertada en la cola.
    // 5. Repetimos hasta vaciar la piscina. Esto garantiza orden sin repeticiones.
    while (lista_cola.obtener_tamanio() < biblioteca.size() && !piscina_canciones.empty()) {
        int peso_total = 0;
        for (const auto& cancion : piscina_canciones) {
            // Consultar la calificación del usuario activo para esta canción
            auto it = calificaciones.find(cancion.identificador);
            int32_t estrellas_usuario = (it != calificaciones.end()) ? it->second : 0;
            peso_total += obtener_peso_por_estrellas(estrellas_usuario);
        }

        std::uniform_int_distribution<int> distribucion(0, peso_total - 1);
        int valor_aleatorio = distribucion(generador);

        int peso_acumulado = 0;
        for (auto iterador = piscina_canciones.begin(); iterador != piscina_canciones.end(); iterador++) {
            auto it = calificaciones.find(iterador->identificador);
            int32_t estrellas_usuario = (it != calificaciones.end()) ? it->second : 0;
            peso_acumulado += obtener_peso_por_estrellas(estrellas_usuario);

            if (valor_aleatorio < peso_acumulado) {
                lista_cola.agregar_al_final(*iterador);
                piscina_canciones.erase(iterador);
                break;
            }
        }
    }
    version_cola++;
}

// Alterna entre secuencial y aleatorio, rescatando la canción que suena actualmente
void QueueManager::alternar_modo_aleatorio(const std::vector<Track>& biblioteca,
                                            const std::unordered_map<int32_t, int32_t>& calificaciones) {
    // LÓGICA CRÍTICA: Rescatar la canción actual antes de destruir la lista
    Track* cancion_previa = obtener_cancion_actual();
    int32_t id_previo = cancion_previa ? cancion_previa->identificador : -1;

    modo_aleatorio = !modo_aleatorio;

    if (modo_aleatorio) {
        inicializar_aleatoria(biblioteca, calificaciones);
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

bool QueueManager::avanzar_siguiente() {
    if (lista_cola.obtener_tamanio() == 0) return false;
    return lista_cola.mover_siguiente();
}

bool QueueManager::retroceder_anterior() {
    if (lista_cola.obtener_tamanio() == 0) return false;
    return lista_cola.mover_anterior();
}

bool QueueManager::saltar_a_posicion(size_t indice) {
    return lista_cola.saltar_a_indice(indice);
}

Track* QueueManager::obtener_cancion_actual() {
    return lista_cola.obtener_elemento_actual();
}

size_t QueueManager::obtener_indice_actual() const {
    return lista_cola.obtener_indice_actual();
}

size_t QueueManager::obtener_tamanio_cola() const {
    return lista_cola.obtener_tamanio();
}

int32_t QueueManager::obtener_version_cola() const {
    return version_cola;
}

bool QueueManager::es_modo_aleatorio() const {
    return modo_aleatorio;
}

void QueueManager::limpiar_cola() {
    lista_cola.limpiar();
    version_cola++;
}

std::vector<TrackC> QueueManager::obtener_snapshot_cola() const {
    std::vector<Track> canciones_planas = lista_cola.a_vector();
    std::vector<TrackC> resultado;
    resultado.reserve(canciones_planas.size());

    for (const auto& cancion : canciones_planas) {
        resultado.push_back(cancion.a_estructura_c());
    }
    return resultado;
}
