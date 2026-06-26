#ifndef LIBRARY_MANAGER_HPP
#define LIBRARY_MANAGER_HPP

#include "Track.hpp"
#include <fstream>
#include <iostream>
#include <map>
#include <string>
#include <unordered_map>
#include <vector>

#include "../third_party/nlohmann/json.hpp"

using json = nlohmann::json;
using std::string;

class LibraryManager {
private:
  std::vector<Track> library;
  std::unordered_map<int32_t, size_t> id_index;
  std::multimap<std::string, size_t> titulo_index;

  void rebuild_indexes() {
    id_index.clear();
    titulo_index.clear();
    for (size_t i = 0; i < library.size(); i++) {
      id_index[library[i].id] = i;
      titulo_index.insert({library[i].titulo, i});
    }
  }

public:
  LibraryManager() = default;

  bool load_from_json(const string &path) {
    std::ifstream file(path);
    if (!file.is_open()) {
      return false;
    }

    try {
      json data;
      file >> data;

      library.clear();

      // Mapeo adaptado exactamente a los campos de tu Track.hpp
      for (const auto &item : data) {
        Track t(item.value("id", 0), item.value("titulo", ""),
                item.value("album", ""), item.value("duracion", 0.0),
                item.value("path", ""), item.value("estrellas", 0));
        library.push_back(t);
      }

      rebuild_indexes(); // index tabla hash
      return true;
    } catch (const std::exception &e) {
      std::cerr << "Error al parsear library.json: " << e.what() << std::endl;
      return false;
    }
  }

  bool save_to_json(const string &path) {
    std::ofstream file(path);
    if (!file.is_open()) {
      return false;
    }

    json data = json::array();
    for (const auto &t : library) {
      json item;
      item["id"] = t.id;
      item["titulo"] = t.titulo;
      item["album"] = t.album;
      item["duracion"] = t.duracion;
      item["path"] = t.path;
      item["estrellas"] = t.estrellas;
      data.push_back(item);
    }

    file << data.dump(4); // se itera 4 espacios para legibilidad
    return true;
  }

  // tamanio total de la biblioteca
  size_t size() const { return library.size(); }

  // acceso directo por posicion de fila - vital para datatable de python
  Track *at(size_t index) {
    if (index >= library.size())
      return nullptr;
    return &library[index];
  }

  // busqueda instantanea O(1) usando la tabla hash indexada
  Track *find_by_id(int32_t id) {
    auto it = id_index.find(id);
    if (it == id_index.end()) {
      return nullptr;
    }
    return &library[it->second];
  }

  // actualiza la calificacion de estrellas en memoria y fuerza la persistencia
  bool set_rating(int32_t track_id, int32_t stars) {
    Track *track = find_by_id(track_id);
    if (!track)
      return false;

    track->estrellas = stars;
    return true;
  }

  // genera un snapshot aplanado (vector de structs estaticos TrackC) para
  // enviarlo a Python a traves de ctypes
  std::vector<TrackC> get_snapshot() const {
    std::vector<TrackC> snapshot;
    snapshot.reserve(library.size());
    for (const auto &track : library) {
      snapshot.push_back(track.to_c());
    }
    return snapshot;
  }

  // retorna una referencia constante al contenedor principal
  const std::vector<Track> &get_all_tracks() const { return library; }
};

#endif