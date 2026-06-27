#ifndef TRACK_HPP
#define TRACK_HPP

/*
===========================================================================
ARCHIVO: Track.hpp

PROPÓSITO:
Este archivo define la entidad principal del dominio del reproductor: la 
canción (o pista). Existe para estandarizar cómo se almacenan y transfieren 
los metadatos de la música entre el motor de audio en C++ y la interfaz en Python.

CÓMO LO HACE:
Define dos estructuras relacionadas:
1. `TrackC`: Una estructura plana (Plain Old Data) optimizada para ser 
   enviada a Python a través de la memoria usando `ctypes`.
2. `Track`: Una clase orientada a objetos para el uso interno en C++, que 
   utiliza `std::string` para mayor seguridad y comodidad. Incluye un método 
   para convertirse a `TrackC`.

VARIABLES PRINCIPALES A USAR:
- identificador (int32_t): El ID único de la canción.
- titulo (string/char[]): El nombre de la canción.
- artista (string/char[]): El nombre del creador de la canción.
- album (string/char[]): El álbum al que pertenece.
- duracion (double): La longitud de la canción en segundos.
- ruta (string/char[]): La dirección física en el disco duro (ej. /home/user/musica.mp3).
- estrellas (int32_t): Calificación asignada por el usuario (1 a 3).
===========================================================================
*/

#include <cstdint>
#include <cstring>
#include <string>

// Incrementado a 512 para soportar rutas de archivos largas en Linux
#define LONGITUD_MAXIMA_CADENA 512

/*
La estructura que Python podrá leer directamente a través de ctypes
*/
struct TrackC {
  int32_t identificador;
  char titulo[LONGITUD_MAXIMA_CADENA];
  char artista[LONGITUD_MAXIMA_CADENA];
  char album[LONGITUD_MAXIMA_CADENA];
  double duracion;
  char ruta[LONGITUD_MAXIMA_CADENA];
  int32_t estrellas;
};

class Track {
public:
  int32_t identificador;
  std::string titulo;
  std::string artista;
  std::string album;
  double duracion;
  std::string ruta;
  int32_t estrellas;

  // constructor por defecto
  Track() : identificador(0), duracion(0.0), estrellas(0) {}

  // constructor completo
  Track(int32_t _identificador, std::string _titulo, std::string _artista, std::string _album, double _duracion,
        std::string _ruta, int32_t _estrellas)
      : identificador(_identificador), titulo(_titulo), artista(_artista), album(_album), duracion(_duracion),
        ruta(_ruta), estrellas(_estrellas) {}

  TrackC a_estructura_c() const {
    TrackC c;
    c.identificador = this->identificador;
    c.duracion = this->duracion;
    c.estrellas = this->estrellas;

    std::strncpy(c.titulo, titulo.c_str(), LONGITUD_MAXIMA_CADENA - 1);
    std::strncpy(c.artista, artista.c_str(), LONGITUD_MAXIMA_CADENA - 1);
    std::strncpy(c.album, album.c_str(), LONGITUD_MAXIMA_CADENA - 1);
    std::strncpy(c.ruta, ruta.c_str(), LONGITUD_MAXIMA_CADENA - 1);

    c.titulo[LONGITUD_MAXIMA_CADENA - 1] = '\0';
    c.artista[LONGITUD_MAXIMA_CADENA - 1] = '\0';
    c.album[LONGITUD_MAXIMA_CADENA - 1] = '\0';
    c.ruta[LONGITUD_MAXIMA_CADENA - 1] = '\0';

    return c;
  }
};

#endif