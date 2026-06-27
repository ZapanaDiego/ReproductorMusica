#ifndef C_API_HPP
#define C_API_HPP

/*
===========================================================================
ARCHIVO: CApi.hpp

PROPÓSITO:
Servir como la frontera C-API (C Application Programming Interface) entre 
el motor C++ y el puente de Python (ctypes).

CÓMO LO HACE:
Define funciones globales (extern "C") que toman un puntero opaco `void*`. 
Estas firmas deben estar ESTRICTAMENTE EN INGLÉS para mantener la compatibilidad
con la UI de Python existente, aunque internamente traduzcan a la lógica C++ 
escrita en español.
===========================================================================
*/

#include <cstdint>
#include <cstddef>

struct TrackC; // Declaración anticipada

extern "C" {
    void* engine_create();
    void engine_destroy(void* puntero_motor);
    int32_t engine_initialize(void* puntero_motor, const char* ruta_json);

    void engine_play(void* puntero_motor);
    void engine_pause(void* puntero_motor);
    int32_t engine_next(void* puntero_motor);
    int32_t engine_previous(void* puntero_motor);
    int32_t engine_jump_to_queue(void* puntero_motor, size_t indice);

    void engine_set_volume(void* puntero_motor, float volumen);
    float engine_get_volume(void* puntero_motor);
    int32_t engine_is_playing(void* puntero_motor);
    size_t engine_get_current_index(void* puntero_motor);
    int32_t engine_get_queue_version(void* puntero_motor);
    int32_t engine_get_library_version(void* puntero_motor);

    void engine_set_rating(void* puntero_motor, int32_t identificador_pista, int32_t estrellas);
    void engine_toggle_random(void* puntero_motor);
    void engine_set_active_user(void* puntero_motor, const char* nombre_usuario);
    void engine_get_active_user_name(void* puntero_motor, char* buffer_salida, int32_t longitud_maxima);

    int32_t engine_get_library(void* puntero_motor, TrackC* buffer_salida, int32_t capacidad_maxima);
    int32_t engine_get_queue(void* puntero_motor, TrackC* buffer_salida, int32_t capacidad_maxima);
}

#endif