#ifndef USER_MANAGER_HPP
#define USER_MANAGER_HPP

/*
===========================================================================
ARCHIVO: UserManager.hpp

PROPÓSITO:
Administrar perfiles de usuarios locales, sus favoritos, álbumes 
personalizados y CALIFICACIONES POR PISTA.

REFACTORIZACIÓN v2.0:
Se añadió 'calificaciones_pistas' (std::unordered_map<int32_t, int32_t>)
al PerfilUsuario. Cada usuario ahora posee su propio diccionario de
calificaciones {ID_canción -> estrellas}, aislando completamente los 
gustos de un usuario respecto a los demás.

JSON en disco (llaves en inglés):
  "ratings": { "42": 3, "17": 2, ... }

Memoria en C++ (variables en español):
  calificaciones_pistas[42] = 3
  calificaciones_pistas[17] = 2
===========================================================================
*/

#include <cstdint>
#include <string>
#include <vector>
#include <unordered_map>
#include <set>
#include <map>

struct PerfilUsuario {
    int32_t identificador;
    std::string nombre;
    std::set<int32_t> pistas_favoritas;
    std::map<std::string, std::vector<int32_t>> albumes_personalizados;
    std::unordered_map<int32_t, int32_t> calificaciones_pistas; // {ID_cancion -> estrellas}
};

class UserManager {
private:
    std::unordered_map<std::string, PerfilUsuario> tabla_usuarios;
    PerfilUsuario* usuario_activo;
    int32_t siguiente_id_usuario; // Generador secuencial para nuevos perfiles

public:
    UserManager();
    ~UserManager() = default;

    bool cargar_usuarios_desde_json();
    bool guardar_usuarios_en_json();

    // Gestión de perfiles
    bool crear_usuario(const std::string& nombre_usuario);
    void asignar_usuario_activo(const std::string& nombre_usuario);
    std::string obtener_usuario_activo() const;
    bool hay_usuarios_registrados() const;
    std::vector<std::string> obtener_nombres_usuarios() const;

    // Favoritos (likes)
    bool gustar_pista(int32_t pista_id);
    bool es_pista_favorita(int32_t pista_id) const;

    // Calificaciones por usuario (antes globales en Track, ahora aisladas)
    bool asignar_calificacion(int32_t pista_id, int32_t estrellas);
    int32_t obtener_calificacion(int32_t pista_id) const;
    std::unordered_map<int32_t, int32_t> obtener_todas_calificaciones() const;

    // Álbumes personalizados
    bool crear_album(const std::string& nombre_album);
    bool eliminar_album(const std::string& nombre_album);
    bool agregar_pista_a_album(const std::string& nombre_album, int32_t pista_id);
    bool eliminar_pista_de_album(const std::string& nombre_album, int32_t pista_id);
    std::vector<std::pair<std::string, size_t>> obtener_resumen_albumes() const;
    std::vector<int32_t> obtener_pistas_de_album(const std::string& nombre_album) const;
};

#endif
