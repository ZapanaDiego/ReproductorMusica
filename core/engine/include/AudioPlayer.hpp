#ifndef AUDIO_PLAYER_HPP
#define AUDIO_PLAYER_HPP

/*
===========================================================================
ARCHIVO: AudioPlayer.hpp

PROPÓSITO:
Actuar como la capa de abstracción del hardware de audio del sistema.
Existe para inicializar la tarjeta de sonido, decodificar archivos de música 
físicos (MP3, WAV, etc.) y enviar los fragmentos de audio a los altavoces.

CÓMO LO HACE:
Utiliza la librería de bajo nivel `miniaudio.h`. Configura un decodificador 
para leer el archivo y un dispositivo de salida. Provee un `callback_audio` 
que se ejecuta en un hilo secundario de muy alta prioridad en tiempo real, 
alimentando la tarjeta de sonido con marcos (frames) de audio.

VARIABLES PRINCIPALES A USAR:
- decodificador (ma_decoder): Objeto nativo de miniaudio que traduce audio a bytes crudos.
- dispositivo (ma_device): Representa la tarjeta de sonido del usuario.
- reproduciendo (bool): Bandera que indica si la música fluye o está silenciada.
- volumen (float): Volumen maestro (de 0.0 a 1.0).
- cancion_terminada (std::atomic<bool>*): Puntero a una bandera atómica del motor para notificar el fin de pista.
===========================================================================
*/

#include <string>
#include <atomic>
#include "../third_party/miniaudio.h"

class AudioPlayer {
private:
    ma_decoder decodificador;
    ma_device dispositivo;
    bool dispositivo_inicializado;
    bool decodificador_inicializado;
    bool reproduciendo;
    float volumen;
    std::atomic<bool>* cancion_terminada; // Puntero a la bandera atómica compartida con el Engine

    void procesar_audio(void* puntero_salida, ma_uint32 conteo_marcos);

public:
    static void callback_audio(ma_device* puntero_dispositivo, void* puntero_salida, const void* puntero_entrada, ma_uint32 conteo_marcos);

    AudioPlayer();
    ~AudioPlayer();

    void desinicializar();
    bool cargar_archivo(const std::string& ruta_archivo);
    void reproducir();
    void pausar();
    void asignar_volumen(float nuevo_volumen);
    bool esta_reproduciendo() const;
    float obtener_volumen() const;

    void asociar_bandera_fin(std::atomic<bool>* bandera);
};

#endif