#include "../include/LibraryManager.hpp"
#include "../third_party/nlohmann/json.hpp"
#include <fstream>
#include <iostream>
#include <algorithm>

using json = nlohmann::json;

LibraryManager::LibraryManager() : version_biblioteca(1), siguiente_id(1) {}

void LibraryManager::reconstruir_indices() {
    indice_por_id.clear();
    indice_por_titulo.clear();
    for (size_t i = 0; i < biblioteca.size(); i++) {
        indice_por_id[biblioteca[i].identificador] = i;
        indice_por_titulo.insert({biblioteca[i].titulo, i});
    }
}

// Carga el catálogo maestro desde 'database/library.json'.
// MAPEO JSON (llaves en inglés) -> MEMORIA (variables en español):
//   "id"       -> identificador
//   "title"    -> titulo
//   "artist"   -> artista
//   "album"    -> album
//   "duration" -> duracion
//   "path"     -> ruta
// NOTA: 'stars' ya NO se lee ni se escribe aquí. Pertenece a UserManager.
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

        int32_t id_maximo = 0;

        for (const auto &item : datos) {
            Track cancion(
                item.value("id", 0),
                item.value("title", ""),
                item.value("artist", "Desconocido"),
                item.value("album", ""),
                item.value("duration", 0.0),
                item.value("path", "")
            );
            biblioteca.push_back(cancion);

            // Rastrear el ID más alto para asegurar que el generador 
            // secuencial nunca colisione con IDs existentes
            if (cancion.identificador > id_maximo) {
                id_maximo = cancion.identificador;
            }
        }

        siguiente_id = id_maximo + 1;
        reconstruir_indices();
        return true;
    } catch (const std::exception &e) {
        std::cerr << "[LibraryManager] Error al parsear: " << e.what() << std::endl;
        return false;
    }
}

// Guarda el catálogo maestro en JSON.
// MAPEO MEMORIA (español) -> JSON (llaves en inglés):
//   identificador -> "id"
//   titulo        -> "title"
//   artista       -> "artist"
//   album         -> "album"
//   duracion      -> "duration"
//   ruta          -> "path"
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
            item["id"]       = cancion.identificador;
            item["title"]    = cancion.titulo;
            item["artist"]   = cancion.artista;
            item["album"]    = cancion.album;
            item["duration"] = cancion.duracion;
            item["path"]     = cancion.ruta;
            // Sin "stars": las calificaciones pertenecen al UserManager
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

// =========================================================================
// MÉTODOS DE MUTACIÓN PARA EL DIRECTORY SCANNER
// =========================================================================

// Agrega una canción nueva al vector principal y reconstruye los índices
void LibraryManager::agregar_cancion(const Track& nueva_cancion) {
    biblioteca.push_back(nueva_cancion);
    reconstruir_indices();
    version_biblioteca++;
}

// Elimina una canción por su ruta física (cuando el archivo ya no existe en disco)
bool LibraryManager::eliminar_cancion_por_ruta(const std::string& ruta) {
    auto iterador = std::remove_if(biblioteca.begin(), biblioteca.end(),
        [&ruta](const Track& cancion) {
            return cancion.ruta == ruta;
        });
    
    if (iterador == biblioteca.end()) {
        return false; // No se encontró la ruta, no hubo cambios
    }

    biblioteca.erase(iterador, biblioteca.end());
    reconstruir_indices();
    version_biblioteca++;
    return true;
}

// Genera un ID único secuencial para canciones nuevas descubiertas por el escáner
int32_t LibraryManager::obtener_siguiente_id() {
    return siguiente_id++;
}

// Retorna un conjunto rápido O(1) de todas las rutas conocidas en la biblioteca.
// El DirectoryScanner lo usará para comparar contra lo que existe físicamente en disco.
std::unordered_set<std::string> LibraryManager::obtener_conjunto_rutas() const {
    std::unordered_set<std::string> conjunto;
    for (const auto& cancion : biblioteca) {
        conjunto.insert(cancion.ruta);
    }
    return conjunto;
}
