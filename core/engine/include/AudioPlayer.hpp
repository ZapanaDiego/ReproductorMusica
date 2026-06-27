#ifndef AUDIO_PLAYER_HPP
#define AUDIO_PLAYER_HPP

#include <string>
#include <vector>
#include <iostream>
#include <algorithm>

#include "../third_party/miniaudio.h"

class AudioPlayer {
private:
    ma_decoder decodificador;
    ma_device dispositivo;
    bool dispositivo_inicializado;
    bool decodificador_inicializado;
    bool reproduciendo;
    float volumen;

    // Metodo interno donde el hilo de audio secundario extrae la musica del archivo fisico
    void procesar_audio(void* pSalida, ma_uint32 conteo_marcos) {
        if (!decodificador_inicializado || !reproduciendo) {
            return;
        }

        // Lee los marcos de audio directamente desde el archivo a traves del decodificador
        ma_uint32 marcos_leidos = (ma_uint32)ma_decoder_read_pcm_frames(&decodificador, pSalida, conteo_marcos, nullptr);

        // Si el decodificador lee menos marcos de los solicitados, la cancion ha terminado
        if (marcos_leidos < conteo_marcos) {
            reproduciendo = false;
        }
    }

public:
    // Funcion estatica intermediaria requerida por la firma en C de miniaudio
    static void callback_audio(ma_device* pDispositivo, void* pSalida, const void* pEntrada, ma_uint32 conteo_marcos) {
        AudioPlayer* reproductor = static_cast<AudioPlayer*>(pDispositivo->pUserData);
        if (reproductor != nullptr) {
            reproductor->procesar_audio(pSalida, conteo_marcos);
        }
        (void)pEntrada; // Evita advertencias de variables no usadas en la compilacion
    }

    AudioPlayer() : 
        dispositivo_inicializado(false), 
        decodificador_inicializado(false), 
        reproduciendo(false), 
        volumen(0.8f) {} // Volumen por defecto al 80%

    ~AudioPlayer() {
        desinicializar();
    }

    // Libera de forma segura los recursos del hardware de sonido y archivos abiertos
    void desinicializar() {
        if (dispositivo_inicializado) {
            ma_device_uninit(&dispositivo);
            dispositivo_inicializado = false;
        }
        if (decodificador_inicializado) {
            ma_decoder_uninit(&decodificador);
            decodificador_inicializado = false;
        }
        reproduciendo = false;
    }

    // Carga un archivo (.mp3, .wav, etc.) y prepara la tarjeta de sonido
    bool cargar_archivo(const std::string& ruta_archivo) {
        desinicializar();

        // 1. Configurar y abrir el decodificador de archivos de audio nativo
        ma_decoder_config configuracion_decodificador = ma_decoder_config_init(ma_format_f32, 2, 44100);
        ma_result resultado = ma_decoder_init_file(ruta_archivo.c_str(), &configuracion_decodificador, &decodificador);
        if (resultado != MA_SUCCESS) {
            std::cout << "[Error] No se pudo abrir o decodificar el archivo: " << ruta_archivo << std::endl;
            return false;
        }
        decodificador_inicializado = true;

        // 2. Configurar el dispositivo de reproduccion segun las propiedades detectadas del audio
        ma_device_config configuracion_dispositivo = ma_device_config_init(ma_device_type_playback);
        configuracion_dispositivo.playback.format   = decodificador.outputFormat;
        configuracion_dispositivo.playback.channels = decodificador.outputChannels;
        configuracion_dispositivo.sampleRate        = decodificador.outputSampleRate;
        configuracion_dispositivo.dataCallback      = callback_audio;
        configuracion_dispositivo.pUserData         = this;

        resultado = ma_device_init(nullptr, &configuracion_dispositivo, &dispositivo);
        if (resultado != MA_SUCCESS) {
            std::cout << "[Error] No se pudo inicializar el hardware de salida de audio." << std::endl;
            ma_decoder_uninit(&decodificador);
            decodificador_inicializado = false;
            return false;
        }
        dispositivo_inicializado = true;

        ma_device_set_master_volume(&dispositivo, volumen);
        return true;
    }

    void reproducir() {
        if (!dispositivo_inicializado) return;
        if (!reproduciendo) {
            ma_device_start(&dispositivo);
            reproduciendo = true;
        }
    }

    void pausar() {
        if (!dispositivo_inicializado) return;
        if (reproduciendo) {
            ma_device_stop(&dispositivo);
            reproduciendo = false;
        }
    }

    void asignar_volumen(float nuevo_volumen) {
        volumen = nuevo_volumen;
        if (volumen < 0.0f) volumen = 0.0f;
        if (volumen > 1.0f) volumen = 1.0f;
        
        if (dispositivo_inicializado) {
            ma_device_set_master_volume(&dispositivo, volumen);
        }
    }

    bool esta_reproduciendo() const {
        return reproduciendo;
    }

    float obtener_volumen() const {
        return volumen;
    }
};

#endif