#include "CApi.hpp"
#include "Engine.hpp"
#include <cstring>
#include <algorithm>

extern "C" {

    // --- Funciones de Ciclo de Vida del Motor ---

    void* engine_create() {
        // Instanciamos el motor en el Heap y lo retornamos como un puntero opaco.
        // Python guardara este entero largo de 64 bits y lo enviara de vuelta en cada comando.
        return static_cast<void*>(new Engine());
    }

    void engine_destroy(void* engine_ptr) {
        if (engine_ptr) {
            // Re-convertimos a puntero de tipo Engine para llamar al destructor correcto
            // y liberar de forma limpia hilos, memoria de miniaudio y buffers.
            delete static_cast<Engine*>(engine_ptr);
        }
    }

    int32_t engine_initialize(void* engine_ptr, const char* ruta_json) {
        if (!engine_ptr || !ruta_json) return 0;
        
        Engine* engine = static_cast<Engine*>(engine_ptr);
        // Convertimos el char* plano a un std::string seguro de C++
        return engine->initialize(std::string(ruta_json)) ? 1 : 0;
    }


    // --- Funciones de Control de Reproduccion ---

    void engine_play(void* engine_ptr) {
        if (!engine_ptr) return;
        static_cast<Engine*>(engine_ptr)->play();
    }

    void engine_pause(void* engine_ptr) {
        if (!engine_ptr) return;
        static_cast<Engine*>(engine_ptr)->pause();
    }

    int32_t engine_next(void* engine_ptr) {
        if (!engine_ptr) return 0;
        return static_cast<Engine*>(engine_ptr)->next() ? 1 : 0;
    }

    int32_t engine_previous(void* engine_ptr) {
        if (!engine_ptr) return 0;
        return static_cast<Engine*>(engine_ptr)->previous() ? 1 : 0;
    }

    int32_t engine_jump_to_queue(void* engine_ptr, size_t indice) {
        if (!engine_ptr) return 0;
        return static_cast<Engine*>(engine_ptr)->jump_to_queue(indice) ? 1 : 0;
    }


    // --- Funciones de Modificadores de Estado y Volumen ---

    void engine_set_volume(void* engine_ptr, float volumen) {
        if (!engine_ptr) return;
        static_cast<Engine*>(engine_ptr)->set_volume(volumen);
    }

    float engine_get_volume(void* engine_ptr) {
        if (!engine_ptr) return 0.0f;
        return static_cast<Engine*>(engine_ptr)->get_volume();
    }

    int32_t engine_is_playing(void* engine_ptr) {
        if (!engine_ptr) return 0;
        return static_cast<Engine*>(engine_ptr)->is_playing() ? 1 : 0;
    }

    size_t engine_get_current_index(void* engine_ptr) {
        if (!engine_ptr) return 0;
        return static_cast<Engine*>(engine_ptr)->get_current_index();
    }

    int32_t engine_get_queue_version(void* engine_ptr) {
        if (!engine_ptr) return 0;
        return static_cast<Engine*>(engine_ptr)->get_queue_version();
    }

    int32_t engine_get_library_version(void* engine_ptr) {
        if (!engine_ptr) return 0;
        return static_cast<Engine*>(engine_ptr)->get_library_version();
    }


    // --- Funciones de Logica de Negocio y Calificaciones ---

    void engine_set_rating(void* engine_ptr, int32_t track_id, int32_t estrellas) {
        if (!engine_ptr) return;
        static_cast<Engine*>(engine_ptr)->set_rating(track_id, estrellas);
    }

    void engine_toggle_random(void* engine_ptr) {
        if (!engine_ptr) return;
        static_cast<Engine*>(engine_ptr)->toggle_random();
    }

    void engine_set_active_user(void* engine_ptr, const char* nombre_usuario) {
        if (!engine_ptr || !nombre_usuario) return;
        static_cast<Engine*>(engine_ptr)->set_active_user(std::string(nombre_usuario));
    }

    void engine_get_active_user_name(void* engine_ptr, char* buffer_salida, int32_t longitud_maxima) {
        if (!engine_ptr || !buffer_salida || longitud_maxima <= 0) return;
        
        std::string name = static_cast<Engine*>(engine_ptr)->get_active_user_name();
        
        // Copia segura de cadenas crudas estilo C previniendo desbordamientos
        std::strncpy(buffer_salida, name.c_str(), longitud_maxima - 1);
        buffer_salida[longitud_maxima - 1] = '\0'; // Aseguramos el terminador nulo
    }


    // --- Funciones de Extraccion de Datos (Snapshots para la UI) ---

    int32_t engine_get_library(void* engine_ptr, TrackC* buffer_salida, int32_t capacidad_maxima) {
        if (!engine_ptr || !buffer_salida || capacidad_maxima <= 0) return 0;
        
        Engine* engine = static_cast<Engine*>(engine_ptr);
        // Obtenemos el snapshot interno generado por C++
        std::vector<TrackC> snapshot = engine->get_library_snapshot();
        
        // Determinamos cuantas canciones podemos copiar sin violar los limites de Python
        int32_t cantidad_a_copiar = std::min(static_cast<int32_t>(snapshot.size()), capacidad_maxima);
        
        // Copia de memoria secuencial ultra rápida
        for (int32_t i = 0; i < cantidad_a_copiar; ++i) {
            buffer_salida[i] = snapshot[i];
        }
        
        return cantidad_a_copiar;
    }

    int32_t engine_get_queue(void* engine_ptr, TrackC* buffer_salida, int32_t capacidad_maxima) {
        if (!engine_ptr || !buffer_salida || capacidad_maxima <= 0) return 0;
        
        Engine* engine = static_cast<Engine*>(engine_ptr);
        std::vector<TrackC> snapshot = engine->get_queue_snapshot();
        
        int32_t cantidad_a_copiar = std::min(static_cast<int32_t>(snapshot.size()), capacidad_maxima);
        
        for (int32_t i = 0; i < cantidad_a_copiar; ++i) {
            buffer_salida[i] = snapshot[i];
        }
        
        return cantidad_a_copiar;
    }

}