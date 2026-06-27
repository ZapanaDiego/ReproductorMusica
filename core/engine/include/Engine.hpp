#ifndef ENGINE_HPP
#define ENGINE_HPP

/*
===========================================================================
ARCHIVO: Engine.hpp
===========================================================================
*/

#include "Track.hpp"
#include "LibraryManager.hpp"
#include "QueueManager.hpp"
#include "UserManager.hpp"
#include "AudioPlayer.hpp"
#include <string>
#include <vector>
#include <thread>
#include <atomic>
#include <mutex>

class Engine {
private:
    LibraryManager administrador_biblioteca;
    QueueManager administrador_cola;
    UserManager administrador_usuarios;
    AudioPlayer reproductor_audio;
    
    bool inicializado;
    bool esta_pausado;

    std::thread hilo_monitoreo;
    std::atomic<bool> ejecutando_hilo;
    std::atomic<bool> cancion_terminada;
    mutable std::mutex mutex_motor;

    bool cargar_tema_actual();
    void ciclo_monitoreo_pistas();

public:
    Engine();
    ~Engine();

    // Sin parámetros, la persistencia local es autónoma
    bool inicializar();
    void finalizar();

    void reproducir();
    void pausar();
    bool avanzar_siguiente();
    bool retroceder_anterior();
    bool saltar_a_posicion_cola(size_t indice);

    void asignar_calificacion_pista(int32_t identificador_pista, int32_t estrellas);
    void alternar_modo_aleatorio();
    
    void asignar_volumen(float volumen);
    float obtener_volumen() const;
    bool esta_reproduciendo() const;
    
    size_t obtener_indice_actual_cola() const;
    int32_t obtener_version_cola() const;
    int32_t obtener_version_biblioteca() const;

    void asignar_usuario_activo(const std::string& nombre_usuario);
    std::string obtener_usuario_activo() const;

    std::vector<TrackC> copiar_snapshot_biblioteca() const;
    std::vector<TrackC> copiar_snapshot_cola() const;
};

#endif