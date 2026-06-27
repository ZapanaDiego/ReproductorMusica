#ifndef PLAYBACK_STATE_HPP
#define PLAYBACK_STATE_HPP

/*
===========================================================================
ARCHIVO: PlaybackState.hpp

PROPÓSITO:
Mantener el estado concurrente del reproductor de audio de manera segura.
Existe porque el decodificador de música (miniaudio) corre en un hilo de 
muy alta prioridad, distinto al hilo principal de control.

CÓMO LO HACE:
Utilizaría variables atómicas (std::atomic) para permitir que varios hilos 
lean y escriban información (como si la música terminó o si se pausó), 
sin usar bloqueos pesados (mutex) que arruinarían el flujo de audio.

VARIABLES PRINCIPALES A USAR:
- pista_terminada (std::atomic<bool>): Bandera que el decodificador enciende al terminar la canción.
- progreso_segundos (std::atomic<double>): Tiempo transcurrido de la canción activa.
===========================================================================
*/

// Archivo actualmente preparado para futura implementación atómica.

#endif
