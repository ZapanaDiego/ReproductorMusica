#ifndef ENGINE_HPP
#define ENGINE_HPP

#include "Track.hpp"
#include "LibraryManager.hpp"
#include "QueueManager.hpp"
#include "AudioPlayer.hpp"
#include <string>
#include <vector>

class Engine {
private:
    LibraryManager administrador_biblioteca;
    QueueManager administrador_cola;
    AudioPlayer reproductor_audio;
    
    std::string ruta_json_actual;
    std::string nombre_usuario_activo;
    bool inicializado;

    bool cargar_tema_actual() {
        Track* cancion_actual = administrador_cola.obtener_cancion_actual();
        if (cancion_actual == nullptr) {
            return false;
        }
        return reproductor_audio.cargar_archivo(cancion_actual->path);
    }

public:
    Engine() : nombre_usuario_activo("Invitado"), inicializado(false) {}

    ~Engine() {
        finalizar();
    }

    bool inicializar(const std::string& ruta_json) {
        ruta_json_actual = ruta_json;
        
        if (!administrador_biblioteca.load_from_json(ruta_json)) {
            std::cout << "[Engine] Error fatal al cargar el archivo JSON de biblioteca." << std::endl;
            return false;
        }

        std::vector<TrackC> snapshot_inicial = administrador_biblioteca.get_snapshot();
        std::vector<Track> biblioteca_nativa;
        biblioteca_nativa.reserve(snapshot_inicial.size());
        
        for (size_t i = 0; i < snapshot_inicial.size(); ++i) {
            Track* t = administrador_biblioteca.at(i);
            if (t != nullptr) {
                biblioteca_nativa.push_back(*t);
            }
        }

        administrador_cola.inicializa_secuencial(biblioteca_nativa);
        inicializado = true;
        return true;
    }

    void finalizar() {
        reproductor_audio.desinicializar();
        administrador_cola.limpiar_cola();
        inicializado = false;
    }

    void reproducir() {
        if (!inicializado) return;
        
        if (!reproductor_audio.esta_reproduciendo() && reproductor_audio.obtener_volumen() >= 0.0f) {
            if (reproductor_audio.esta_reproduciendo() == false) {
                cargar_tema_actual();
            }
        }
        reproductor_audio.reproducir();
    }

    void pausar() {
        if (!inicializado) return;
        reproductor_audio.pausar();
    }

    bool avanzar_siguiente() {
        if (!inicializado) return false;
        
        bool movido = administrador_cola.avanzar_siguiente();
        if (movido) {
            reproductor_audio.pausar();
            cargar_tema_actual();
            reproductor_audio.reproducir();
            return true;
        }
        return false;
    }

    bool retroceder_anterior() {
        if (!inicializado) return false;
        
        bool movido = administrador_cola.retroceder_anterior();
        if (movido) {
            reproductor_audio.pausar();
            cargar_tema_actual();
            reproductor_audio.reproducir();
            return true;
        }
        return false;
    }

    bool saltar_a_posicion_cola(size_t indice) {
        if (!inicializado) return false;
        
        bool movido = administrador_cola.saltar_a_posicion(indice);
        if (movido) {
            reproductor_audio.pausar();
            cargar_tema_actual();
            reproductor_audio.reproducir();
            return true;
        }
        return false;
    }

    void asignar_calificacion_pista(int32_t track_id, int32_t estrellas) {
        if (!inicializado) return;
        
        administrador_biblioteca.set_rating(track_id, estrellas);
        administrador_biblioteca.save_to_json(ruta_json_actual);
        std::cout << "[Engine] Calificacion actualizada para ID: " << track_id << " a " << estrellas << " estrellas." << std::endl;
    }

    void alternar_modo_aleatorio() {
        if (!inicializado) return;

        std::vector<Track> canciones_totales;
        for (size_t i = 0; i < administrador_biblioteca.size(); ++i) {
            Track* t = administrador_biblioteca.at(i);
            if (t != nullptr) {
                canciones_totales.push_back(*t);
            }
        }
        
        administrador_cola.alternar_modo_aleatorio(canciones_totales);
        cargar_tema_actual();
        reproductor_audio.reproducir();
    }

    void asignar_volumen(float volumen) {
        reproductor_audio.asignar_volumen(volumen);
    }

    float obtener_volumen() const {
        return reproductor_audio.obtener_volumen();
    }

    bool esta_reproduciendo() const {
        return reproductor_audio.esta_reproduciendo();
    }

    size_t obtener_indice_actual_cola() const {
        return administrador_cola.obtener_indice_actual();
    }

    int32_t obtener_version_cola() const {
        return administrador_cola.obtener_version_cola();
    }

    int32_t obtener_version_biblioteca() const {
        return static_cast<int32_t>(administrador_biblioteca.size());
    }

    void asignar_usuario_activo(const std::string& nombre_usuario) {
        nombre_usuario_activo = nombre_usuario;
    }

    std::string obtener_usuario_activo() const {
        return nombre_usuario_activo;
    }

    std::vector<TrackC> copiar_snapshot_biblioteca() const {
        return administrador_biblioteca.get_snapshot();
    }

    std::vector<TrackC> copiar_snapshot_cola() const {
        return administrador_cola.obtener_snapshot_cola();
    }
};

#endif