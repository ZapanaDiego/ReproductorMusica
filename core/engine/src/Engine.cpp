#include "../include/Engine.hpp"
#include <iostream>
#include <chrono>

Engine::Engine() : inicializado(false), esta_pausado(false), ejecutando_hilo(true), cancion_terminada(false) {
    reproductor_audio.asociar_bandera_fin(&cancion_terminada);
    hilo_monitoreo = std::thread(&Engine::ciclo_monitoreo_pistas, this);
}

Engine::~Engine() {
    finalizar();
    ejecutando_hilo = false;
    if (hilo_monitoreo.joinable()) {
        hilo_monitoreo.join();
    }
}

void Engine::ciclo_monitoreo_pistas() {
    while (ejecutando_hilo) {
        if (cancion_terminada) {
            std::lock_guard<std::mutex> seguro(mutex_motor);
            cancion_terminada = false;
            avanzar_siguiente(); 
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
}

// Inicialización delegada a los managers que buscan en "database/" internamente
bool Engine::inicializar() {
    std::lock_guard<std::mutex> seguro(mutex_motor);
    
    if (!administrador_biblioteca.cargar_desde_json()) {
        std::cerr << "[Engine] Fallo al inicializar LibraryManager desde base de datos." << std::endl;
        return false;
    }
    
    // Inicializar perfiles de usuario
    administrador_usuarios.cargar_usuarios_desde_json();

    administrador_cola.inicializa_secuencial(administrador_biblioteca.obtener_todas_las_canciones());
    inicializado = true;
    return true;
}

void Engine::finalizar() {
    std::lock_guard<std::mutex> seguro(mutex_motor);
    reproductor_audio.desinicializar();
    administrador_cola.limpiar_cola();
    inicializado = false;
    esta_pausado = false;
}

bool Engine::cargar_tema_actual() {
    Track* cancion_actual = administrador_cola.obtener_cancion_actual();
    if (cancion_actual == nullptr) return false;
    return reproductor_audio.cargar_archivo(cancion_actual->ruta);
}

void Engine::reproducir() {
    std::lock_guard<std::mutex> seguro(mutex_motor);
    if (!inicializado) return;
    
    if (esta_pausado) {
        esta_pausado = false;
        reproductor_audio.reproducir();
        return;
    }

    if (!reproductor_audio.esta_reproduciendo()) {
        cargar_tema_actual();
        esta_pausado = false;
    }
    
    reproductor_audio.reproducir();
}

void Engine::pausar() {
    std::lock_guard<std::mutex> seguro(mutex_motor);
    if (!inicializado) return;
    reproductor_audio.pausar();
    esta_pausado = true;
}

bool Engine::avanzar_siguiente() {
    if (!inicializado) return false;
    
    bool movido = administrador_cola.avanzar_siguiente();
    if (movido) {
        reproductor_audio.pausar();
        esta_pausado = false;
        cargar_tema_actual();
        reproductor_audio.reproducir();
        return true;
    }
    return false;
}

bool Engine::retroceder_anterior() {
    std::lock_guard<std::mutex> seguro(mutex_motor);
    if (!inicializado) return false;
    
    bool movido = administrador_cola.retroceder_anterior();
    if (movido) {
        reproductor_audio.pausar();
        esta_pausado = false;
        cargar_tema_actual();
        reproductor_audio.reproducir();
        return true;
    }
    return false;
}

bool Engine::saltar_a_posicion_cola(size_t indice) {
    std::lock_guard<std::mutex> seguro(mutex_motor);
    if (!inicializado) return false;
    
    bool movido = administrador_cola.saltar_a_posicion(indice);
    if (movido) {
        reproductor_audio.pausar();
        esta_pausado = false;
        cargar_tema_actual();
        reproductor_audio.reproducir();
        return true;
    }
    return false;
}

void Engine::asignar_calificacion_pista(int32_t identificador_pista, int32_t estrellas) {
    std::lock_guard<std::mutex> seguro(mutex_motor);
    if (!inicializado) return;
    
    administrador_biblioteca.asignar_calificacion(identificador_pista, estrellas);
    administrador_biblioteca.guardar_en_json(); // Llama directo a la ruta interna "database/"
}

void Engine::alternar_modo_aleatorio() {
    std::lock_guard<std::mutex> seguro(mutex_motor);
    if (!inicializado) return;
    administrador_cola.alternar_modo_aleatorio(administrador_biblioteca.obtener_todas_las_canciones());
}

void Engine::asignar_volumen(float volumen) {
    std::lock_guard<std::mutex> seguro(mutex_motor);
    reproductor_audio.asignar_volumen(volumen);
}

float Engine::obtener_volumen() const {
    return reproductor_audio.obtener_volumen();
}

bool Engine::esta_reproduciendo() const {
    return reproductor_audio.esta_reproduciendo();
}

size_t Engine::obtener_indice_actual_cola() const {
    return administrador_cola.obtener_indice_actual();
}

int32_t Engine::obtener_version_cola() const {
    return administrador_cola.obtener_version_cola();
}

int32_t Engine::obtener_version_biblioteca() const {
    return administrador_biblioteca.obtener_version_biblioteca();
}

void Engine::asignar_usuario_activo(const std::string& nombre_usuario) {
    std::lock_guard<std::mutex> seguro(mutex_motor);
    administrador_usuarios.asignar_usuario_activo(nombre_usuario);
}

std::string Engine::obtener_usuario_activo() const {
    return administrador_usuarios.obtener_usuario_activo();
}

std::vector<TrackC> Engine::copiar_snapshot_biblioteca() const {
    std::lock_guard<std::mutex> seguro(mutex_motor);
    return administrador_biblioteca.obtener_snapshot();
}

std::vector<TrackC> Engine::copiar_snapshot_cola() const {
    std::lock_guard<std::mutex> seguro(mutex_motor);
    return administrador_cola.obtener_snapshot_cola();
}
