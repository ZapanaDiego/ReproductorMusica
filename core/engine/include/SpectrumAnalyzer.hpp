#ifndef SPECTRUM_ANALYZER_HPP
#define SPECTRUM_ANALYZER_HPP

/*
===========================================================================
ARCHIVO: SpectrumAnalyzer.hpp

PROPÓSITO:
Procesar las frecuencias matemáticas de la música en tiempo real.
Originalmente diseñado para realizar la Transformada Rápida de Fourier (FFT) 
y obtener las bandas de ecualización para la terminal.

CÓMO LO HACE:
Se preveía que leyera el búfer de audio de `AudioPlayer` y calculara las 
frecuencias. Sin embargo, por arquitectura del proyecto y necesidades 
del sistema, la generación de estas barras (CAVA) se mantiene y 
ejecuta exclusivamente desde Python.

VARIABLES PRINCIPALES A USAR:
- N/A (Se delega al subproceso nativo de Cava en Python).
===========================================================================
*/

// Este archivo se mantiene vacío intencionalmente ya que Python 
// gestiona el espectro visual con su propia dependencia (CAVA).

#endif
