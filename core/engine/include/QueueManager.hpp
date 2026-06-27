#ifndef QUEUE_MANAGER_HPP
#define QUEUE_MANAGER_HPP

#include "Track.hpp"
#include "DoublyLinkedList.hpp"
#include <vector>
#include <random>
#include <algorithm>
#include <ctime>

class QueueManager {
private:
    DoublyLinkedList<Track> lista_cola;
    bool modo_aleatorio;
    int32_t version_cola;

    // Ajustado especificamente para un sistema de maximo 3 estrellas
    int obtener_peso_por_estrellas(int32_t estrellas) {
        if (estrellas <= 1) return 1;
        if (estrellas == 2) return 3;
        return 6;
    }

public:
    QueueManager() : modo_aleatorio(false), version_cola(1) {}

    void inicializa_secuencial(const std::vector<Track>& biblioteca) {
        lista_cola.clear();
        for (const auto& cancion : biblioteca) {
            lista_cola.push_back(cancion);
        }
        version_cola++;
    }

    void inicializar_aleatoria(const std::vector<Track>& biblioteca) {
        if (biblioteca.empty()) return;
        lista_cola.clear();

        std::vector<Track> piscina_canciones = biblioteca;

        // Motor de numeros aleatorios
        std::mt19937 generador(static_cast<unsigned int>(std::time(nullptr)));

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
                    lista_cola.push_back(*iterador);
                    piscina_canciones.erase(iterador);
                    break;
                }
            }
        }
        version_cola++;
    }

    void alternar_modo_aleatorio(const std::vector<Track>& biblioteca) {
        modo_aleatorio = !modo_aleatorio;
        if (modo_aleatorio) {
            inicializar_aleatoria(biblioteca);
        } else {
            inicializa_secuencial(biblioteca);
        }
    }

    bool avanzar_siguiente() {
        if (lista_cola.obtener_tamanio() == 0) {
            return false;
        }
        return lista_cola.mover_siguiente();
    }

    bool retroceder_anterior() {
        if (lista_cola.obtener_tamanio() == 0) {
            return false;
        }
        return lista_cola.mover_anterior();
    }

    bool saltar_a_posicion(size_t indice) {
        return lista_cola.saltar_a_indice(indice);
    }

    Track* obtener_cancion_actual() {
        return lista_cola.obtener_item_actual();
    }

    size_t obtener_indice_actual() const {
        return lista_cola.obtener_indice_actual();
    }

    size_t obtener_tamanio_cola() const {
        return lista_cola.obtener_tamanio();
    }

    int32_t obtener_version_cola() const {
        return version_cola;
    }

    bool es_modo_aleatorio() const {
        return modo_aleatorio;
    }

    void limpiar_cola() {
        lista_cola.clear();
        version_cola++;
    }

    std::vector<TrackC> obtener_snapshot_cola() const {
        std::vector<Track> canciones_planas = lista_cola.a_vector();
        std::vector<TrackC> resultado;
        resultado.reserve(canciones_planas.size());

        for (const auto& cancion : canciones_planas) {
            resultado.push_back(cancion.to_c());
        }
        return resultado;
    }
};

#endif