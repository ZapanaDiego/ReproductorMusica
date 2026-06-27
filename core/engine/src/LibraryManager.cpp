#include "../include/LibraryManager.hpp"
#include "../third_party/nlohmann/json.hpp"
#include <fstream>
#include <iostream>
#include <algorithm>

using json = nlohmann::json;

LibraryManager::LibraryManager() : version_biblioteca(1) {}

void LibraryManager::reconstruir_indices() {
    indice_por_id.clear();
    indice_por_titulo.clear();
    for (size_t i = 0; i < biblioteca.size(); i++) {
        indice_por_id[biblioteca[i].identificador] = i;
        indice_por_titulo.insert({biblioteca[i].titulo, i});
    }
}

// Carga la biblioteca apuntando estrictamente al directorio local 'database/'
bool LibraryManager::cargar_desde_json() {
    std::string ruta_archivo = "database/library.json";
    std::ifstream archivo(ruta_archivo);
    if (!archivo.is_open()) {
        std::cerr << "[LibraryManager] No se pudo abrir JSON local: " << ruta_archivo << std::endl;
        return false;
    }

    try {
        json datos;
        archivo >> datos;
        biblioteca.clear();

        for (const auto &item : datos) {
            Track cancion(
                item.value("id", 0),
                item.value("title", ""),
                item.value("artist", "Desconocido"),
                item.value("album", ""),
                item.value("duration", 0.0),
                item.value("path", ""),
                item.value("stars", 1)
            );
            biblioteca.push_back(cancion);
        }

        reconstruir_indices();
        return true;
    } catch (const std::exception &e) {
        std::cerr << "[LibraryManager] Error al parsear: " << e.what() << std::endl;
        return false;
    }
}

bool LibraryManager::guardar_en_json() {
    std::string ruta_archivo = "database/library.json";
    std::ofstream archivo(ruta_archivo);
    if (!archivo.is_open()) {
        std::cerr << "[LibraryManager] Error de escritura local en: " << ruta_archivo << std::endl;
        return false;
    }

    try {
        json datos = json::array();
        for (const auto &cancion : biblioteca) {
            json item;
            item["id"] = cancion.identificador;
            item["title"] = cancion.titulo;
            item["artist"] = cancion.artista;
            item["album"] = cancion.album;
            item["duration"] = cancion.duracion;
            item["path"] = cancion.ruta;
            item["stars"] = cancion.estrellas;
            datos.push_back(item);
        }

        archivo << datos.dump(4);
        return true;
    } catch (const std::exception &e) {
        std::cerr << "[LibraryManager] Fallo de guardado: " << e.what() << std::endl;
        return false;
    }
}

size_t LibraryManager::obtener_tamanio() const {
    return biblioteca.size();
}

Track* LibraryManager::obtener_en_posicion(size_t indice) {
    if (indice >= biblioteca.size()) return nullptr;
    return &biblioteca[indice];
}

Track* LibraryManager::buscar_por_id(int32_t identificador) {
    auto iterador = indice_por_id.find(identificador);
    if (iterador == indice_por_id.end()) return nullptr;
    return &biblioteca[iterador->second];
}

bool LibraryManager::asignar_calificacion(int32_t identificador, int32_t estrellas) {
    Track* cancion = buscar_por_id(identificador);
    if (!cancion) return false;

    cancion->estrellas = estrellas;
    version_biblioteca++; 
    return true;
}

int32_t LibraryManager::obtener_version_biblioteca() const {
    return version_biblioteca;
}

std::vector<TrackC> LibraryManager::obtener_snapshot() const {
    std::vector<TrackC> instantanea;
    instantanea.reserve(biblioteca.size());
    for (const auto &cancion : biblioteca) {
        instantanea.push_back(cancion.a_estructura_c());
    }
    return instantanea;
}

const std::vector<Track>& LibraryManager::obtener_todas_las_canciones() const {
    return biblioteca;
}
