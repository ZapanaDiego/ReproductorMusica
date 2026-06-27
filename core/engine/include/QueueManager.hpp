#ifndef QUEUE_MANAGER_HPP
#define QUEUE_MANAGER_HPP

/*
===========================================================================
ARCHIVO: QueueManager.hpp

PROPÓSITO:
Administrar la cola actual de canciones a reproducir.
Existe para abstraer la lógica de mantener qué canción sigue, gestionar el 
modo aleatorio (shuffle) ponderado por calificación (estrellas) y el modo 
secuencial normal.

CÓMO LO HACE:
Utiliza internamente la estructura `ListaDoblementeEnlazada` para almacenar 
las canciones. Cuando se inicializa, puede copiar la biblioteca secuencialmente 
o usar un algoritmo de selección aleatoria ponderada, asegurando que las 
canciones con más estrellas tengan más probabilidad de ser seleccionadas.

VARIABLES PRINCIPALES A USAR:
- lista_cola (ListaDoblementeEnlazada<Track>): La estructura de datos enlazada que guarda las canciones ordenadas.
- modo_aleatorio (bool): Bandera que indica si estamos en modo aleatorio o secuencial.
- version_cola (int32_t): Contador que se incrementa al reconstruir la cola. Python lo monitorea para redibujar la tabla visual.
===========================================================================
*/

#include "Track.hpp"
#include "DoublyLinkedList.hpp"
#include <vector>

class QueueManager {
private:
    ListaDoblementeEnlazada<Track> lista_cola;
    bool modo_aleatorio;
    int32_t version_cola;

    int obtener_peso_por_estrellas(int32_t estrellas);

public:
    QueueManager();
    ~QueueManager() = default;

    void inicializa_secuencial(const std::vector<Track>& biblioteca);
    void inicializar_aleatoria(const std::vector<Track>& biblioteca);
    void alternar_modo_aleatorio(const std::vector<Track>& biblioteca);

    bool avanzar_siguiente();
    bool retroceder_anterior();
    bool saltar_a_posicion(size_t indice);

    Track* obtener_cancion_actual();
    size_t obtener_indice_actual() const;
    size_t obtener_tamanio_cola() const;
    int32_t obtener_version_cola() const;
    bool es_modo_aleatorio() const;

    void limpiar_cola();
    std::vector<TrackC> obtener_snapshot_cola() const;
};

#endif