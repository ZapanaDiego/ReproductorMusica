#ifndef LIBRARY_MANAGER_HPP
#define LIBRARY_MANAGER_HPP

/*
===========================================================================
ARCHIVO: LibraryManager.hpp
===========================================================================
*/

#include "Track.hpp"
#include <string>
#include <unordered_map>
#include <map>
#include <vector>

class LibraryManager {
private:
  std::vector<Track> biblioteca;
  std::unordered_map<int32_t, size_t> indice_por_id;
  std::multimap<std::string, size_t> indice_por_titulo;
  int32_t version_biblioteca;

  void reconstruir_indices();

public:
  LibraryManager();

  // Firmas limpias sin implementaciones inline. Ya no reciben ruta por parámetro.
  bool cargar_desde_json();
  bool guardar_en_json();

  size_t obtener_tamanio() const;
  Track *obtener_en_posicion(size_t indice);
  Track *buscar_por_id(int32_t identificador);
  bool asignar_calificacion(int32_t identificador, int32_t estrellas);
  int32_t obtener_version_biblioteca() const;

  std::vector<TrackC> obtener_snapshot() const;
  const std::vector<Track>& obtener_todas_las_canciones() const;
};

#endif