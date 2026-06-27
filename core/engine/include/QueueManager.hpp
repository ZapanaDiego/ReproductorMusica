#ifndef QUEUE_MANAGER_HPP
#define QUEUE_MANAGER_HPP

/*
===========================================================================
ARCHIVO: QueueManager.hpp

PROPÓSITO:
Administrar la cola actual de canciones a reproducir usando una lista
doblemente enlazada circular.

REFACTORIZACIÓN v2.0:
El algoritmo de barajado ponderado ya no lee 'cancion.estrellas'
(eliminada de Track). Ahora recibe un mapa externo de calificaciones
{ID_canción -> estrellas} proporcionado por UserManager, garantizando
que el shuffle refleje los gustos del usuario activo.
===========================================================================
*/

#include "Track.hpp"
#include "DoublyLinkedList.hpp"
#include <vector>
#include <unordered_map>

class QueueManager {
private:
    ListaDoblementeEnlazada<Track> lista_cola;
    bool modo_aleatorio;
    int32_t version_cola;

    // Recibe las estrellas desde el mapa externo; si la canción no tiene calificación, retorna peso 1
    int obtener_peso_por_estrellas(int32_t estrellas);

public:
    QueueManager();
    ~QueueManager() = default;

    void inicializa_secuencial(const std::vector<Track>& biblioteca);

    // Reciben el mapa de calificaciones del usuario activo
    void inicializar_aleatoria(const std::vector<Track>& biblioteca,
                               const std::unordered_map<int32_t, int32_t>& calificaciones);
    void alternar_modo_aleatorio(const std::vector<Track>& biblioteca,
                                 const std::unordered_map<int32_t, int32_t>& calificaciones);

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