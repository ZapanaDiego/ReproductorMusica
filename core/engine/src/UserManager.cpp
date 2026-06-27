#include "../include/UserManager.hpp"
#include "../third_party/nlohmann/json.hpp"
#include <fstream>
#include <iostream>
#include <algorithm>

using json = nlohmann::json;

UserManager::UserManager() : usuario_activo(nullptr), siguiente_id_usuario(1) {}

// Carga los usuarios desde 'database/users_db.json'.
// MAPEO JSON (llaves en inglés) -> MEMORIA (variables en español):
//   "id"             -> identificador
//   "name"           -> nombre
//   "liked_tracks"   -> pistas_favoritas (std::set)
//   "custom_albums"  -> albumes_personalizados (std::map)
//   "ratings"        -> calificaciones_pistas (std::unordered_map)
bool UserManager::cargar_usuarios_desde_json() {
    std::string ruta_base_datos = "database/users_db.json";
    std::ifstream archivo(ruta_base_datos);
    if (!archivo.is_open()) {
        // Si el archivo no existe, no es un error fatal: simplemente no hay usuarios
        std::cerr << "[UserManager] Archivo de usuarios no encontrado: " << ruta_base_datos
                  << ". Se iniciará con base de datos vacía." << std::endl;
        return true;
    }

    try {
        json datos;
        archivo >> datos;

        tabla_usuarios.clear();
        usuario_activo = nullptr;
        int32_t id_maximo = 0;

        if (datos.contains("users") && datos["users"].is_array()) {
            for (const auto& item_usuario : datos["users"]) {
                PerfilUsuario perfil;
                perfil.identificador = item_usuario.value("id", 0);
                perfil.nombre = item_usuario.value("name", "");

                // Rastrear ID máximo para el generador secuencial
                if (perfil.identificador > id_maximo) {
                    id_maximo = perfil.identificador;
                }

                // Mapeo: "liked_tracks" -> pistas_favoritas
                if (item_usuario.contains("liked_tracks") && item_usuario["liked_tracks"].is_array()) {
                    for (const auto& pista_id : item_usuario["liked_tracks"]) {
                        perfil.pistas_favoritas.insert(pista_id.get<int32_t>());
                    }
                }

                // Mapeo: "custom_albums" -> albumes_personalizados
                if (item_usuario.contains("custom_albums") && item_usuario["custom_albums"].is_object()) {
                    for (auto it = item_usuario["custom_albums"].begin(); it != item_usuario["custom_albums"].end(); ++it) {
                        std::string nombre_album = it.key();
                        std::vector<int32_t> pistas_album;
                        if (it.value().is_array()) {
                            for (const auto& pista_id : it.value()) {
                                pistas_album.push_back(pista_id.get<int32_t>());
                            }
                        }
                        perfil.albumes_personalizados[nombre_album] = pistas_album;
                    }
                }

                // NUEVO: Mapeo "ratings" -> calificaciones_pistas
                // El JSON guarda las llaves como strings ("42": 3).
                // En memoria usamos int32_t -> int32_t para O(1) de consulta.
                if (item_usuario.contains("ratings") && item_usuario["ratings"].is_object()) {
                    for (auto it = item_usuario["ratings"].begin(); it != item_usuario["ratings"].end(); ++it) {
                        int32_t id_cancion = std::stoi(it.key());
                        int32_t estrellas = it.value().get<int32_t>();
                        perfil.calificaciones_pistas[id_cancion] = estrellas;
                    }
                }

                tabla_usuarios[perfil.nombre] = perfil;
            }
        }

        siguiente_id_usuario = id_maximo + 1;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "[UserManager] Error al parsear usuarios: " << e.what() << std::endl;
        return false;
    }
}

// Guarda los perfiles.
// MAPEO MEMORIA (español) -> JSON (llaves en inglés):
//   identificador           -> "id"
//   nombre                  -> "name"
//   pistas_favoritas        -> "liked_tracks"
//   albumes_personalizados  -> "custom_albums"
//   calificaciones_pistas   -> "ratings"
bool UserManager::guardar_usuarios_en_json() {
    std::string ruta_base_datos = "database/users_db.json";
    std::ofstream archivo(ruta_base_datos);
    if (!archivo.is_open()) {
        std::cerr << "[UserManager] No se pudo escribir en: " << ruta_base_datos << std::endl;
        return false;
    }

    try {
        json datos;
        json lista_usuarios = json::array();

        for (const auto& par : tabla_usuarios) {
            const PerfilUsuario& perfil = par.second;
            json item_usuario;

            item_usuario["id"] = perfil.identificador;
            item_usuario["name"] = perfil.nombre;

            // Mapeo: pistas_favoritas -> "liked_tracks"
            json arr_favoritos = json::array();
            for (int32_t pista_id : perfil.pistas_favoritas) {
                arr_favoritos.push_back(pista_id);
            }
            item_usuario["liked_tracks"] = arr_favoritos;

            // Mapeo: albumes_personalizados -> "custom_albums"
            json obj_albumes = json::object();
            for (const auto& par_album : perfil.albumes_personalizados) {
                json arr_pistas = json::array();
                for (int32_t pista_id : par_album.second) {
                    arr_pistas.push_back(pista_id);
                }
                obj_albumes[par_album.first] = arr_pistas;
            }
            item_usuario["custom_albums"] = obj_albumes;

            // NUEVO: Mapeo calificaciones_pistas -> "ratings"
            // Las llaves del JSON son strings del ID de la canción
            json obj_calificaciones = json::object();
            for (const auto& par_cal : perfil.calificaciones_pistas) {
                obj_calificaciones[std::to_string(par_cal.first)] = par_cal.second;
            }
            item_usuario["ratings"] = obj_calificaciones;

            lista_usuarios.push_back(item_usuario);
        }

        datos["users"] = lista_usuarios;
        archivo << datos.dump(4);
        return true;
    } catch (const std::exception& e) {
        std::cerr << "[UserManager] Error al guardar usuarios: " << e.what() << std::endl;
        return false;
    }
}

// Crea un perfil de usuario nuevo con ID secuencial y lo persiste
bool UserManager::crear_usuario(const std::string& nombre_usuario) {
    // Verificar si ya existe un usuario con ese nombre
    if (tabla_usuarios.count(nombre_usuario) > 0) {
        std::cerr << "[UserManager] El usuario '" << nombre_usuario << "' ya existe." << std::endl;
        return false;
    }

    PerfilUsuario nuevo_perfil;
    nuevo_perfil.identificador = siguiente_id_usuario++;
    nuevo_perfil.nombre = nombre_usuario;
    // pistas_favoritas, albumes_personalizados y calificaciones_pistas inician vacíos

    tabla_usuarios[nombre_usuario] = nuevo_perfil;
    guardar_usuarios_en_json();
    return true;
}

void UserManager::asignar_usuario_activo(const std::string& nombre_usuario) {
    auto iterador = tabla_usuarios.find(nombre_usuario);
    if (iterador != tabla_usuarios.end()) {
        usuario_activo = &(iterador->second);
    } else {
        usuario_activo = nullptr;
    }
}

std::string UserManager::obtener_usuario_activo() const {
    if (usuario_activo != nullptr) return usuario_activo->nombre;
    return "Invitado";
}

// Consulta crítica para que Python sepa si debe mostrar el flujo de onboarding
bool UserManager::hay_usuarios_registrados() const {
    return !tabla_usuarios.empty();
}

std::vector<std::string> UserManager::obtener_nombres_usuarios() const {
    std::vector<std::string> nombres;
    for (const auto& par : tabla_usuarios) {
        nombres.push_back(par.first);
    }
    return nombres;
}

// =========================================================================
// CALIFICACIONES POR USUARIO (Trasladadas desde el antiguo Track.estrellas)
// =========================================================================

// Asigna o actualiza la calificación de una pista para el usuario activo
bool UserManager::asignar_calificacion(int32_t pista_id, int32_t estrellas) {
    if (usuario_activo == nullptr) return false;

    // Validar rango (1-3 estrellas, 0 para borrar calificación)
    if (estrellas < 0 || estrellas > 3) return false;

    if (estrellas == 0) {
        // Borrar la calificación si se envía 0
        usuario_activo->calificaciones_pistas.erase(pista_id);
    } else {
        usuario_activo->calificaciones_pistas[pista_id] = estrellas;
    }

    guardar_usuarios_en_json();
    return true;
}

// Retorna la calificación del usuario activo para una pista. 0 si no existe.
int32_t UserManager::obtener_calificacion(int32_t pista_id) const {
    if (usuario_activo == nullptr) return 0;

    auto iterador = usuario_activo->calificaciones_pistas.find(pista_id);
    if (iterador != usuario_activo->calificaciones_pistas.end()) {
        return iterador->second;
    }
    return 0; // Sin calificación = peso por defecto
}

// Retorna el mapa completo de calificaciones del usuario activo.
// QueueManager lo necesita para su algoritmo de barajado ponderado.
std::unordered_map<int32_t, int32_t> UserManager::obtener_todas_calificaciones() const {
    if (usuario_activo == nullptr) return {};
    return usuario_activo->calificaciones_pistas;
}

// =========================================================================
// FAVORITOS (LIKES)
// =========================================================================

bool UserManager::gustar_pista(int32_t pista_id) {
    if (usuario_activo == nullptr) return false;

    auto iterador = usuario_activo->pistas_favoritas.find(pista_id);
    bool se_agrego;
    if (iterador != usuario_activo->pistas_favoritas.end()) {
        usuario_activo->pistas_favoritas.erase(iterador);
        se_agrego = false;
    } else {
        usuario_activo->pistas_favoritas.insert(pista_id);
        se_agrego = true;
    }

    guardar_usuarios_en_json();
    return se_agrego;
}

bool UserManager::es_pista_favorita(int32_t pista_id) const {
    if (usuario_activo == nullptr) return false;
    return usuario_activo->pistas_favoritas.count(pista_id) > 0;
}

// =========================================================================
// ÁLBUMES PERSONALIZADOS
// =========================================================================

bool UserManager::crear_album(const std::string& nombre_album) {
    if (usuario_activo == nullptr) return false;
    if (usuario_activo->albumes_personalizados.count(nombre_album) > 0) return false;

    usuario_activo->albumes_personalizados[nombre_album] = std::vector<int32_t>();
    guardar_usuarios_en_json();
    return true;
}

bool UserManager::eliminar_album(const std::string& nombre_album) {
    if (usuario_activo == nullptr) return false;
    auto iterador = usuario_activo->albumes_personalizados.find(nombre_album);
    if (iterador == usuario_activo->albumes_personalizados.end()) return false;

    usuario_activo->albumes_personalizados.erase(iterador);
    guardar_usuarios_en_json();
    return true;
}

bool UserManager::agregar_pista_a_album(const std::string& nombre_album, int32_t pista_id) {
    if (usuario_activo == nullptr) return false;
    auto iterador = usuario_activo->albumes_personalizados.find(nombre_album);
    if (iterador == usuario_activo->albumes_personalizados.end()) return false;

    auto& pistas = iterador->second;
    if (std::find(pistas.begin(), pistas.end(), pista_id) == pistas.end()) {
        pistas.push_back(pista_id);
        guardar_usuarios_en_json();
        return true;
    }
    return false;
}

bool UserManager::eliminar_pista_de_album(const std::string& nombre_album, int32_t pista_id) {
    if (usuario_activo == nullptr) return false;
    auto iterador = usuario_activo->albumes_personalizados.find(nombre_album);
    if (iterador == usuario_activo->albumes_personalizados.end()) return false;

    auto& pistas = iterador->second;
    auto iterador_pista = std::find(pistas.begin(), pistas.end(), pista_id);
    if (iterador_pista != pistas.end()) {
        pistas.erase(iterador_pista);
        guardar_usuarios_en_json();
        return true;
    }
    return false;
}

std::vector<std::pair<std::string, size_t>> UserManager::obtener_resumen_albumes() const {
    std::vector<std::pair<std::string, size_t>> resumen;
    if (usuario_activo == nullptr) return resumen;

    for (const auto& par : usuario_activo->albumes_personalizados) {
        resumen.push_back({par.first, par.second.size()});
    }
    return resumen;
}

std::vector<int32_t> UserManager::obtener_pistas_de_album(const std::string& nombre_album) const {
    if (usuario_activo == nullptr) return std::vector<int32_t>();

    auto iterador = usuario_activo->albumes_personalizados.find(nombre_album);
    if (iterador != usuario_activo->albumes_personalizados.end()) {
        return iterador->second;
    }
    return std::vector<int32_t>();
}
