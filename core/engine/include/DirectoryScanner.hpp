#ifndef DIRECTORY_SCANNER_HPP
#define DIRECTORY_SCANNER_HPP

/*
===========================================================================
ARCHIVO: DirectoryScanner.hpp

PROPÓSITO:
Escanear automáticamente el sistema de archivos del usuario al arrancar
el programa, buscando directorios de música y sincronizando el catálogo
maestro (LibraryManager) con los archivos físicos que realmente existen.

CÓMO LO HACE:
1. Detecta el directorio raíz del usuario ($HOME en Linux/Mac).
2. Busca carpetas que coincidan con variaciones del nombre "Música"
   (Music, music, Musica, muscia, Música, etc.).
3. Escanea recursivamente esas carpetas buscando archivos de audio
   con extensiones soportadas (.mp3, .wav, .flac, .ogg, .m4a).
4. Compara las rutas encontradas en disco contra las existentes en
   el LibraryManager mediante conjuntos (std::unordered_set) para
   una diferenciación eficiente en O(N).
5. Agrega canciones nuevas y elimina las que ya no existen en disco.
6. Solo persiste cambios si realmente los hubo (ahorro de I/O).

VARIABLES PRINCIPALES:
- directorios_musica (std::vector<std::string>): Carpetas encontradas.
- extensiones_soportadas (std::unordered_set<std::string>): Tipos de archivo válidos.
===========================================================================
*/

#include "LibraryManager.hpp"
#include <string>
#include <vector>
#include <unordered_set>

class DirectoryScanner {
private:
    std::vector<std::string> directorios_musica;
    std::unordered_set<std::string> extensiones_soportadas;

    // Detecta el directorio home del usuario según el SO
    std::string obtener_directorio_home() const;

    // Verifica si un nombre de carpeta coincide con variaciones de "Música"
    bool es_nombre_carpeta_musica(const std::string& nombre_carpeta) const;

    // Verifica si un archivo tiene una extensión de audio soportada
    bool es_archivo_audio(const std::string& nombre_archivo) const;

    // Extrae el nombre legible del archivo sin extensión ni ruta
    std::string extraer_titulo(const std::string& nombre_archivo) const;

public:
    DirectoryScanner();
    ~DirectoryScanner() = default;

    // Busca y almacena las carpetas de música encontradas en el home del usuario
    void buscar_directorios_musica();

    // Sincroniza los archivos físicos con el catálogo en memoria.
    // Retorna true si hubo cambios (canciones nuevas o eliminadas).
    bool sincronizar_biblioteca(LibraryManager& biblioteca);

    // Retorna las carpetas de música descubiertas (para depuración/UI)
    const std::vector<std::string>& obtener_directorios_encontrados() const;
};

#endif
