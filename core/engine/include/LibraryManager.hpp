#ifndef LIBRARY_MANAGER_HPP
#define LIBRARY_MANAGER_HPP

/*
===========================================================================
ARCHIVO: LibraryManager.hpp

PROPÓSITO:
Base de datos en memoria del catálogo maestro de canciones.
Lee y escribe 'database/library.json' con los metadatos estáticos
(id, título, artista, álbum, duración, ruta).

REFACTORIZACIÓN v2.0:
- Se eliminó 'asignar_calificacion' (las estrellas ahora viven en UserManager).
- Se añadieron métodos de mutación para el DirectoryScanner:
  agregar_cancion(), eliminar_cancion_por_ruta(), obtener_siguiente_id(),
  obtener_conjunto_rutas().
===========================================================================
*/

#include "Track.hpp"
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <map>
#include <vector>

class LibraryManager {
private:
  std::vector<Track> biblioteca;
  std::unordered_map<int32_t, size_t> indice_por_id;
  std::multimap<std::string, size_t> indice_por_titulo;
  int32_t version_biblioteca;
  int32_t siguiente_id;  // Generador secuencial de IDs para canciones nuevas

  void reconstruir_indices();

public:
  LibraryManager();

  bool cargar_desde_json();
  bool guardar_en_json();

  size_t obtener_tamanio() const;
  Track *obtener_en_posicion(size_t indice);
  Track *buscar_por_id(int32_t identificador);
  int32_t obtener_version_biblioteca() const;

  std::vector<TrackC> obtener_snapshot() const;
  const std::vector<Track>& obtener_todas_las_canciones() const;

  // Métodos de mutación para el DirectoryScanner
  void agregar_cancion(const Track& nueva_cancion);
  bool eliminar_cancion_por_ruta(const std::string& ruta);
  int32_t obtener_siguiente_id();
  std::unordered_set<std::string> obtener_conjunto_rutas() const;
};

#endif