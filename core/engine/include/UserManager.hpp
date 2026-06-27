#ifndef USER_MANAGER_HPP
#define USER_MANAGER_HPP

/*
===========================================================================
ARCHIVO: UserManager.hpp
===========================================================================
*/

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
};

class UserManager {
private:
    std::unordered_map<std::string, PerfilUsuario> tabla_usuarios;
    PerfilUsuario* usuario_activo;

public:
    UserManager();
    ~UserManager() = default;

    // Métodos limpios sin parámetros de ruta. Todo es interno.
    bool cargar_usuarios_desde_json();
    bool guardar_usuarios_en_json();

    void asignar_usuario_activo(const std::string& nombre_usuario);
    std::string obtener_usuario_activo() const;

    bool gustar_pista(int32_t pista_id);
    bool es_pista_favorita(int32_t pista_id) const;

    bool crear_album(const std::string& nombre_album);
    bool eliminar_album(const std::string& nombre_album);
    bool agregar_pista_a_album(const std::string& nombre_album, int32_t pista_id);
    bool eliminar_pista_de_album(const std::string& nombre_album, int32_t pista_id);

    std::vector<std::string> obtener_nombres_usuarios() const;
    std::vector<std::pair<std::string, size_t>> obtener_resumen_albumes() const;
    std::vector<int32_t> obtener_pistas_de_album(const std::string& nombre_album) const;
};

#endif
