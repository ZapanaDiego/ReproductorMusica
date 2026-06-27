#include "../include/AudioPlayer.hpp"
#include <iostream>
#include <cstring>

// Implementación del hardware de Audio usando miniaudio

AudioPlayer::AudioPlayer() : 
    dispositivo_inicializado(false), 
    decodificador_inicializado(false), 
    reproduciendo(false), 
    volumen(0.8f),
    cancion_terminada(nullptr) {}

AudioPlayer::~AudioPlayer() {
    desinicializar();
}

void AudioPlayer::asociar_bandera_fin(std::atomic<bool>* bandera) {
    cancion_terminada = bandera;
}

void AudioPlayer::desinicializar() {
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

bool AudioPlayer::cargar_archivo(const std::string& ruta_archivo) {
    desinicializar();

    ma_decoder_config config_decod = ma_decoder_config_init(ma_format_f32, 2, 44100);
    ma_result resultado = ma_decoder_init_file(ruta_archivo.c_str(), &config_decod, &decodificador);
    if (resultado != MA_SUCCESS) {
        std::cerr << "[AudioPlayer] Error al inicializar el decodificador para: " << ruta_archivo << std::endl;
        return false;
    }
    decodificador_inicializado = true;

    ma_device_config config_disp = ma_device_config_init(ma_device_type_playback);
    config_disp.playback.format   = decodificador.outputFormat;
    config_disp.playback.channels = decodificador.outputChannels;
    config_disp.sampleRate        = decodificador.outputSampleRate;
    config_disp.dataCallback      = callback_audio;
    config_disp.pUserData         = this;

    resultado = ma_device_init(nullptr, &config_disp, &dispositivo);
    if (resultado != MA_SUCCESS) {
        std::cerr << "[AudioPlayer] Error al inicializar el dispositivo de salida." << std::endl;
        ma_decoder_uninit(&decodificador);
        decodificador_inicializado = false;
        return false;
    }
    dispositivo_inicializado = true;

    ma_device_set_master_volume(&dispositivo, volumen);
    if (cancion_terminada) {
        *cancion_terminada = false;
    }
    return true;
}

void AudioPlayer::reproducir() {
    if (!dispositivo_inicializado) return;
    if (!reproduciendo) {
        ma_device_start(&dispositivo);
        reproduciendo = true;
    }
}

void AudioPlayer::pausar() {
    if (!dispositivo_inicializado) return;
    if (reproduciendo) {
        ma_device_stop(&dispositivo);
        reproduciendo = false;
    }
}

void AudioPlayer::asignar_volumen(float nuevo_volumen) {
    volumen = nuevo_volumen;
    if (volumen < 0.0f) volumen = 0.0f;
    if (volumen > 1.0f) volumen = 1.0f;
    
    if (dispositivo_inicializado) {
        ma_device_set_master_volume(&dispositivo, volumen);
    }
}

bool AudioPlayer::esta_reproduciendo() const {
    return reproduciendo;
}

float AudioPlayer::obtener_volumen() const {
    return volumen;
}

// CALLBACK DE ALTA PRIORIDAD (Ejecutado por el hilo de miniaudio)
void AudioPlayer::procesar_audio(void* puntero_salida, ma_uint32 conteo_marcos) {
    size_t bytes_por_marco = ma_get_bytes_per_frame(decodificador.outputFormat, decodificador.outputChannels);

    // REGLA ANTI-FALLAS 1: Si está pausado o no inicializado, llenar de ceros absolutos
    if (!decodificador_inicializado || !reproduciendo) {
        std::memset(puntero_salida, 0, conteo_marcos * bytes_por_marco);
        return;
    }

    // Leemos del archivo físico
    ma_uint32 marcos_leidos = (ma_uint32)ma_decoder_read_pcm_frames(&decodificador, puntero_salida, conteo_marcos, nullptr);

    // REGLA ANTI-FALLAS 2: EOF o fin de canción -> llenar el sobrante y notificar atómicamente
    if (marcos_leidos < conteo_marcos) {
        reproduciendo = false;
        char* puntero_salida_bytes = static_cast<char*>(puntero_salida);
        std::memset(puntero_salida_bytes + (marcos_leidos * bytes_por_marco), 0, (conteo_marcos - marcos_leidos) * bytes_por_marco);
        
        if (cancion_terminada) {
            *cancion_terminada = true; // Notifica al Engine para avanzar al siguiente track automáticamente
        }
    }
}

void AudioPlayer::callback_audio(ma_device* puntero_dispositivo, void* puntero_salida, const void* puntero_entrada, ma_uint32 conteo_marcos) {
    AudioPlayer* reproductor = static_cast<AudioPlayer*>(puntero_dispositivo->pUserData);
    if (reproductor != nullptr) {
        reproductor->procesar_audio(puntero_salida, conteo_marcos);
    }
    (void)puntero_entrada;
}
