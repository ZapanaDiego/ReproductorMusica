#ifndef TRACK_HPP
#define TRACK_HPP

#include <cstdint>

#define MAX_STR_LEN 256

/*
La estructura que python podrà leer directamente
*/

struct TrackC{
    int32_t id;
    char titulo[MAX_STR_LEN];
    double duracion;
    char path[MAX_STR_LEN];
    int32_t estrellas;

};

class Track{
public:
    int32_t id;
    const char* titulo;
    double duracion;
    const char* path;
    int32_t estrellas;

    
};

#endif