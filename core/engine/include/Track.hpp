#ifndef TRACK_HPP
#define TRACK_HPP

/*
===========================================================================
ARCHIVO: Track.hpp

PROPÓSITO:
Define la entidad principal del dominio: la canción (pista).
Estandariza cómo se almacenan y transfieren los metadatos de la música 
entre el motor C++ y la interfaz Python.

REFACTORIZACIÓN v2.0:
Se eliminó la variable 'estrellas' de esta estructura. Las calificaciones
ahora pertenecen exclusivamente al perfil de cada usuario en UserManager,
garantizando el aislamiento total de datos por perfil.

VARIABLES:
- identificador (int32_t): ID único de la canción.
- titulo (string/char[]): Nombre de la canción.
- artista (string/char[]): Creador de la canción.
- album (string/char[]): Álbum al que pertenece.
- duracion (double): Longitud en segundos.
- ruta (string/char[]): Dirección física en el disco duro.
===========================================================================
*/

#include <cstdint>
#include <cstring>
#include <string>

// Tamaño de búfer para cadenas de texto enviadas a Python
#define LONGITUD_MAXIMA_CADENA 512

/*
Estructura plana (POD) que Python lee directamente a través de ctypes.
Sin 'estrellas': las calificaciones viven en UserManager.
*/
struct TrackC {
  int32_t identificador;
  char titulo[LONGITUD_MAXIMA_CADENA];
  char artista[LONGITUD_MAXIMA_CADENA];
  char album[LONGITUD_MAXIMA_CADENA];
  double duracion;
  char ruta[LONGITUD_MAXIMA_CADENA];
};

class Track {
public:
  int32_t identificador;
  std::string titulo;
  std::string artista;
  std::string album;
  double duracion;
  std::string ruta;

  // Constructor por defecto
  Track() : identificador(0), duracion(0.0) {}

  // Constructor completo (sin estrellas)
  Track(int32_t _identificador, std::string _titulo, std::string _artista,
        std::string _album, double _duracion, std::string _ruta)
      : identificador(_identificador), titulo(_titulo), artista(_artista),
        album(_album), duracion(_duracion), ruta(_ruta) {}

  TrackC a_estructura_c() const {
    TrackC c;
    c.identificador = this->identificador;
    c.duracion = this->duracion;

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