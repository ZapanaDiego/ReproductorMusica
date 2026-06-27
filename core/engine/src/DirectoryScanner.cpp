#include "../include/DirectoryScanner.hpp"
#include <filesystem>
#include <iostream>
#include <algorithm>
#include <cctype>

namespace fs = std::filesystem;

DirectoryScanner::DirectoryScanner() {
    // Extensiones de audio soportadas por miniaudio y formatos comunes
    extensiones_soportadas = {".mp3", ".wav", ".flac", ".ogg", ".m4a"};
}

// Detecta el directorio home del usuario según el sistema operativo.
// En Linux/Mac usa la variable de entorno $HOME.
// En Windows usa %USERPROFILE%.
std::string DirectoryScanner::obtener_directorio_home() const {
    const char* home = nullptr;

    // Intentar primero la variable estándar de Linux/Mac
    home = std::getenv("HOME");
    if (home != nullptr) {
        return std::string(home);
    }

    // Fallback para Windows
    home = std::getenv("USERPROFILE");
    if (home != nullptr) {
        return std::string(home);
    }

    std::cerr << "[DirectoryScanner] No se pudo detectar el directorio home del usuario." << std::endl;
    return "";
}

// Convierte un string a minúsculas para comparación tolerante de nombres
static std::string a_minusculas(const std::string& texto) {
    std::string resultado = texto;
    std::transform(resultado.begin(), resultado.end(), resultado.begin(),
        [](unsigned char c) { return std::tolower(c); });
    return resultado;
}

// Verifica si el nombre de una carpeta coincide con variaciones comunes
// del directorio de música del usuario.
// Nombres detectados: Music, music, Musica, musica, Música, música, muscia, etc.
bool DirectoryScanner::es_nombre_carpeta_musica(const std::string& nombre_carpeta) const {
    std::string nombre_normalizado = a_minusculas(nombre_carpeta);

    // Lista exhaustiva de variaciones conocidas (todas en minúsculas)
    static const std::vector<std::string> variaciones = {
        "music",     // Inglés estándar
        "musica",    // Español sin tilde
        "música",    // Español con tilde (codificación UTF-8)
        "muscia",    // Error tipográfico común
        "musik",     // Alemán
        "musique",   // Francés
        "muzica",    // Rumano
        "muziek",    // Holandés
    };

    for (const auto& variacion : variaciones) {
        if (nombre_normalizado == variacion) {
            return true;
        }
    }
    return false;
}

// Verifica si el archivo tiene una extensión de audio reconocida
bool DirectoryScanner::es_archivo_audio(const std::string& nombre_archivo) const {
    // Extraer la extensión y convertirla a minúsculas
    size_t posicion_punto = nombre_archivo.rfind('.');
    if (posicion_punto == std::string::npos) {
        return false;
    }

    std::string extension = a_minusculas(nombre_archivo.substr(posicion_punto));
    return extensiones_soportadas.count(extension) > 0;
}

// Extrae un título legible del nombre del archivo:
// "/home/diego/Music/Mi Cancion Favorita.mp3" -> "Mi Cancion Favorita"
std::string DirectoryScanner::extraer_titulo(const std::string& nombre_archivo) const {
    // Obtener solo el nombre del archivo sin la ruta
    fs::path ruta(nombre_archivo);
    std::string solo_nombre = ruta.stem().string(); // Sin extensión

    // Reemplazar guiones bajos y guiones por espacios para legibilidad
    std::replace(solo_nombre.begin(), solo_nombre.end(), '_', ' ');
    std::replace(solo_nombre.begin(), solo_nombre.end(), '-', ' ');

    return solo_nombre;
}

// Busca en el directorio home del usuario todas las carpetas que 
// coincidan con variaciones de "Música" y almacena sus rutas.
void DirectoryScanner::buscar_directorios_musica() {
    directorios_musica.clear();

    std::string directorio_home = obtener_directorio_home();
    if (directorio_home.empty()) {
        return;
    }

    try {
        // Iterar solo el primer nivel del home (no recursivo aquí)
        for (const auto& entrada : fs::directory_iterator(directorio_home)) {
            if (!entrada.is_directory()) {
                continue;
            }

            std::string nombre_carpeta = entrada.path().filename().string();

            if (es_nombre_carpeta_musica(nombre_carpeta)) {
                directorios_musica.push_back(entrada.path().string());
                std::cout << "[DirectoryScanner] Directorio de musica encontrado: "
                          << entrada.path().string() << std::endl;
            }
        }
    } catch (const fs::filesystem_error& e) {
        std::cerr << "[DirectoryScanner] Error al explorar el home: " << e.what() << std::endl;
    }

    if (directorios_musica.empty()) {
        std::cout << "[DirectoryScanner] No se encontraron directorios de musica en: "
                  << directorio_home << std::endl;
    }
}

// SINCRONIZACIÓN INTELIGENTE (DIFERENCIAL):
// Compara lo que existe físicamente en disco contra lo que está en el LibraryManager.
// 1. Si hay archivos nuevos en disco -> los agrega al catálogo.
// 2. Si hay canciones en el catálogo cuyo archivo ya no existe -> las elimina.
// 3. Si no hay cambios -> no toca el JSON (ahorro de ciclos de I/O).
// Retorna true si hubo al menos un cambio.
bool DirectoryScanner::sincronizar_biblioteca(LibraryManager& biblioteca) {
    if (directorios_musica.empty()) {
        std::cout << "[DirectoryScanner] Sin directorios de musica. Ejecute buscar_directorios_musica() primero." << std::endl;
        return false;
    }

    bool hubo_cambios = false;

    // PASO 1: Recopilar TODAS las rutas de archivos de audio que existen en disco
    std::unordered_set<std::string> rutas_en_disco;

    for (const auto& directorio : directorios_musica) {
        try {
            // Iteración RECURSIVA: busca en todas las subcarpetas del directorio
            for (const auto& entrada : fs::recursive_directory_iterator(directorio,
                    fs::directory_options::skip_permission_denied)) {
                
                if (!entrada.is_regular_file()) {
                    continue;
                }

                std::string ruta_absoluta = entrada.path().string();

                if (es_archivo_audio(ruta_absoluta)) {
                    rutas_en_disco.insert(ruta_absoluta);
                }
            }
        } catch (const fs::filesystem_error& e) {
            std::cerr << "[DirectoryScanner] Error al escanear " << directorio
                      << ": " << e.what() << std::endl;
        }
    }

    // PASO 2: Obtener las rutas que ya conoce el LibraryManager
    std::unordered_set<std::string> rutas_en_biblioteca = biblioteca.obtener_conjunto_rutas();

    // PASO 3: DETECTAR CANCIONES NUEVAS (existen en disco pero no en biblioteca)
    for (const auto& ruta_disco : rutas_en_disco) {
        if (rutas_en_biblioteca.count(ruta_disco) == 0) {
            // Canción nueva descubierta -> generar Track y agregar
            Track nueva_cancion;
            nueva_cancion.identificador = biblioteca.obtener_siguiente_id();
            nueva_cancion.titulo = extraer_titulo(ruta_disco);
            nueva_cancion.artista = "Desconocido";
            nueva_cancion.album = "";
            nueva_cancion.duracion = 0.0; // Se puede extraer con miniaudio en el futuro
            nueva_cancion.ruta = ruta_disco;

            biblioteca.agregar_cancion(nueva_cancion);
            hubo_cambios = true;

            std::cout << "[DirectoryScanner] + Nueva cancion: " << nueva_cancion.titulo
                      << " (" << ruta_disco << ")" << std::endl;
        }
    }

    // PASO 4: DETECTAR CANCIONES HUÉRFANAS (existen en biblioteca pero no en disco)
    for (const auto& ruta_bib : rutas_en_biblioteca) {
        if (rutas_en_disco.count(ruta_bib) == 0) {
            biblioteca.eliminar_cancion_por_ruta(ruta_bib);
            hubo_cambios = true;

            std::cout << "[DirectoryScanner] - Cancion eliminada (archivo borrado del disco): "
                      << ruta_bib << std::endl;
        }
    }

    // PASO 5: Solo persistir si hubo diferencias reales
    if (hubo_cambios) {
        biblioteca.guardar_en_json();
        std::cout << "[DirectoryScanner] Base de datos sincronizada. Total canciones: "
                  << biblioteca.obtener_tamanio() << std::endl;
    } else {
        std::cout << "[DirectoryScanner] Sin cambios detectados. JSON intacto." << std::endl;
    }

    return hubo_cambios;
}

const std::vector<std::string>& DirectoryScanner::obtener_directorios_encontrados() const {
    return directorios_musica;
}
