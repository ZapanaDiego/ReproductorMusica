#ifndef TRACK_HPP
#define TRACK_HPP

#include <cstdint>
#include <string>
#include <cstring> // Para strncpy

#define MAX_STR_LEN 256

/*
La estructura que python podrà leer directamente
*/

struct TrackC{
    int32_t id;
    char titulo[MAX_STR_LEN];
    char album[MAX_STR_LEN];
    double duracion;
    char path[MAX_STR_LEN];
    int32_t estrellas;

};

class Track{
public:
    int32_t id;
    std::string titulo;
    std::string album;
    double duracion;
    std::string path;
    int32_t estrellas;

    //constructor por defecto
    Track() : id(0), duracion(0.0), estrellas(0){}

    //constructor completo
    Track(int32_t _id, std::string _titulo, std::string _album, double _duracion, std::string _path, int32_t _estrellas) 
    : id(_id), titulo(_titulo), album(_album), duracion(_duracion), path(_path), estrellas(_estrellas) {}
    
    TrackC to_c() const {
        TrackC c;
        c.id = this->id;
        c.duracion = duracion;
        c.estrellas = estrellas;

        std::strncpy(c.titulo, titulo.c_str(), MAX_STR_LEN - 1);
        std::strncpy(c.album, album.c_str(), MAX_STR_LEN -1);
        std::strncpy(c.path, path.c_str(), MAX_STR_LEN -1);

        c.titulo[MAX_STR_LEN -1] = '\0';
        c.album[MAX_STR_LEN -1] = '\0';
        c.path[MAX_STR_LEN -1] = '\0';

        return c;
    }

    
};

#endif