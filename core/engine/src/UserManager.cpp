#include "../include/UserManager.hpp"
#include "../third_party/nlohmann/json.hpp"
#include <fstream>
#include <iostream>
#include <algorithm>

using json = nlohmann::json;

UserManager::UserManager() : usuario_activo(nullptr) {}

bool UserManager::cargar_usuarios_desde_json() {
    std::string ruta_base_datos = "database/users_db.json";
    std::ifstream archivo(ruta_base_datos);
    if (!archivo.is_open()) {
        std::cerr << "[UserManager] No se pudo abrir JSON de usuarios: " << ruta_base_datos << std::endl;
        return false;
    }

    try {
        json datos;
        archivo >> datos;

        tabla_usuarios.clear();
        usuario_activo = nullptr;

        if (datos.contains("users") && datos["users"].is_array()) {
            for (const auto& item_usuario : datos["users"]) {
                PerfilUsuario perfil;
                perfil.identificador = item_usuario.value("id", 0);
                perfil.nombre = item_usuario.value("name", "");

                if (item_usuario.contains("liked_tracks") && item_usuario["liked_tracks"].is_array()) {
                    for (const auto& pista_id : item_usuario["liked_tracks"]) {
                        perfil.pistas_favoritas.insert(pista_id.get<int32_t>());
                    }
                }

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

                tabla_usuarios[perfil.nombre] = perfil;
            }
        }
        return true;
    } catch (const std::exception& e) {
        std::cerr << "[UserManager] Error al parsear usuarios: " << e.what() << std::endl;
        return false;
    }
}

bool UserManager::guardar_usuarios_en_json() {
    std::string ruta_base_datos = "database/users_db.json";
    std::ofstream archivo(ruta_base_datos);
    if (!archivo.is_open()) {
        std::cerr << "[UserManager] No se pudo escribir localmente en: " << ruta_base_datos << std::endl;
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

            json arr_favoritos = json::array();
            for (int32_t pista_id : perfil.pistas_favoritas) {
                arr_favoritos.push_back(pista_id);
            }
            item_usuario["liked_tracks"] = arr_favoritos;

            json obj_albumes = json::object();
            for (const auto& par_album : perfil.albumes_personalizados) {
                json arr_pistas = json::array();
                for (int32_t pista_id : par_album.second) {
                    arr_pistas.push_back(pista_id);
                }
                obj_albumes[par_album.first] = arr_pistas;
            }
            item_usuario["custom_albums"] = obj_albumes;

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

std::vector<std::string> UserManager::obtener_nombres_usuarios() const {
    std::vector<std::string> nombres;
    for (const auto& par : tabla_usuarios) {
        nombres.push_back(par.first);
    }
    return nombres;
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
