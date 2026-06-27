#include "../include/CApi.hpp"
#include "../include/Engine.hpp"
#include <cstring>
#include <algorithm>

extern "C" {

    void* engine_create() {
        return static_cast<void*>(new Engine());
    }

    void engine_destroy(void* puntero_motor) {
        if (puntero_motor) {
            delete static_cast<Engine*>(puntero_motor);
        }
    }

    int32_t engine_initialize(void* puntero_motor, const char* ruta_json) {
        // 'ruta_json' desde Python se ignora intencionalmente porque 
        // ahora el motor C++ fuerza la arquitectura a buscar en "database/" de manera autónoma.
        if (!puntero_motor) return 0;
        return static_cast<Engine*>(puntero_motor)->inicializar() ? 1 : 0;
    }

    void engine_play(void* puntero_motor) {
        if (!puntero_motor) return;
        static_cast<Engine*>(puntero_motor)->reproducir();
    }

    void engine_pause(void* puntero_motor) {
        if (!puntero_motor) return;
        static_cast<Engine*>(puntero_motor)->pausar();
    }

    int32_t engine_next(void* puntero_motor) {
        if (!puntero_motor) return 0;
        return static_cast<Engine*>(puntero_motor)->avanzar_siguiente() ? 1 : 0;
    }

    int32_t engine_previous(void* puntero_motor) {
        if (!puntero_motor) return 0;
        return static_cast<Engine*>(puntero_motor)->retroceder_anterior() ? 1 : 0;
    }

    int32_t engine_jump_to_queue(void* puntero_motor, size_t indice) {
        if (!puntero_motor) return 0;
        return static_cast<Engine*>(puntero_motor)->saltar_a_posicion_cola(indice) ? 1 : 0;
    }

    void engine_set_volume(void* puntero_motor, float volumen) {
        if (!puntero_motor) return;
        static_cast<Engine*>(puntero_motor)->asignar_volumen(volumen);
    }

    float engine_get_volume(void* puntero_motor) {
        if (!puntero_motor) return 0.0f;
        return static_cast<Engine*>(puntero_motor)->obtener_volumen();
    }

    int32_t engine_is_playing(void* puntero_motor) {
        if (!puntero_motor) return 0;
        return static_cast<Engine*>(puntero_motor)->esta_reproduciendo() ? 1 : 0;
    }

    size_t engine_get_current_index(void* puntero_motor) {
        if (!puntero_motor) return 0;
        return static_cast<Engine*>(puntero_motor)->obtener_indice_actual_cola();
    }

    int32_t engine_get_queue_version(void* puntero_motor) {
        if (!puntero_motor) return 0;
        return static_cast<Engine*>(puntero_motor)->obtener_version_cola();
    }

    int32_t engine_get_library_version(void* puntero_motor) {
        if (!puntero_motor) return 0;
        return static_cast<Engine*>(puntero_motor)->obtener_version_biblioteca();
    }

    void engine_set_rating(void* puntero_motor, int32_t identificador_pista, int32_t estrellas) {
        if (!puntero_motor) return;
        static_cast<Engine*>(puntero_motor)->asignar_calificacion_pista(identificador_pista, estrellas);
    }

    void engine_toggle_random(void* puntero_motor) {
        if (!puntero_motor) return;
        static_cast<Engine*>(puntero_motor)->alternar_modo_aleatorio();
    }

    void engine_set_active_user(void* puntero_motor, const char* nombre_usuario) {
        if (!puntero_motor || !nombre_usuario) return;
        static_cast<Engine*>(puntero_motor)->asignar_usuario_activo(std::string(nombre_usuario));
    }

    void engine_get_active_user_name(void* puntero_motor, char* buffer_salida, int32_t longitud_maxima) {
        if (!puntero_motor || !buffer_salida || longitud_maxima <= 0) return;
        
        std::string nombre = static_cast<Engine*>(puntero_motor)->obtener_usuario_activo();
        std::strncpy(buffer_salida, nombre.c_str(), longitud_maxima - 1);
        buffer_salida[longitud_maxima - 1] = '\0';
    }

    int32_t engine_get_library(void* puntero_motor, TrackC* buffer_salida, int32_t capacidad_maxima) {
        if (!puntero_motor || !buffer_salida || capacidad_maxima <= 0) return 0;
        
        std::vector<TrackC> instantanea = static_cast<Engine*>(puntero_motor)->copiar_snapshot_biblioteca();
        int32_t cantidad_a_copiar = std::min(static_cast<int32_t>(instantanea.size()), capacidad_maxima);
        
        for (int32_t i = 0; i < cantidad_a_copiar; ++i) {
            buffer_salida[i] = instantanea[i];
        }
        return cantidad_a_copiar;
    }

    int32_t engine_get_queue(void* puntero_motor, TrackC* buffer_salida, int32_t capacidad_maxima) {
        if (!puntero_motor || !buffer_salida || capacidad_maxima <= 0) return 0;
        
        std::vector<TrackC> instantanea = static_cast<Engine*>(puntero_motor)->copiar_snapshot_cola();
        int32_t cantidad_a_copiar = std::min(static_cast<int32_t>(instantanea.size()), capacidad_maxima);
        
        for (int32_t i = 0; i < cantidad_a_copiar; ++i) {
            buffer_salida[i] = instantanea[i];
        }
        return cantidad_a_copiar;
    }

}