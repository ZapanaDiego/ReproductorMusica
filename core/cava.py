# ==========================================
# ARCHIVO: core_cava.py
# ==========================================
import os
import subprocess
import threading
import tempfile
from core.logger import get_logger

logger = get_logger("CavaBridge")

class CavaSubprocess:
    """
    Gestiona el subproceso del ecualizador CAVA de Linux.
    Genera un archivo de configuración temporal en modo 'raw ascii',
    lo ejecuta y captura las frecuencias puras mediante un hilo en segundo plano.
    """
    def __init__(self, bars=128):
        self.bars = bars
        self.raw_data = [0.0] * bars
        self.process = None
        self._running = False
        self._thread = None
        self._start_cava()

    def _start_cava(self):
        config = f"""
[general]
framerate = 60
bars = {self.bars}
autosens = 1

[smoothing]
monstercat = 1
gravity = 150
ignore = 0

[output]
method = raw
raw_target = /dev/stdout
data_format = binary
bit_format = 8bit
"""
        try:
            # Crear configuración temporal
            fd, path = tempfile.mkstemp(suffix='.conf', prefix='cava_')
            with os.fdopen(fd, 'w') as f:
                f.write(config)
            
            # Lanzar el subproceso real (sin text=True para leer binario)
            self.process = subprocess.Popen(
                ['cava', '-p', path],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            self._running = True
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()
            logger.info("Subproceso CAVA iniciado correctamente en modo binario de cero latencia.")
            
        except FileNotFoundError:
            logger.error("Ejecutable 'cava' no encontrado en Linux. Se retornarán datos vacíos.")
        except Exception as e:
            logger.error(f"Error crítico al iniciar CAVA: {e}")

    def _read_loop(self):
        """Lee el stdout binario crudo y elimina el buffer bloat."""
        import time
        fd = self.process.stdout.fileno()
        os.set_blocking(fd, False)
        
        buffer = bytearray()
        
        while self._running and self.process:
            try:
                chunk = os.read(fd, 4096)
                if not chunk:
                    break
                buffer.extend(chunk)
                
                # Extraemos solo el último frame disponible (Buffer Bloat fix)
                frames_available = len(buffer) // self.bars
                if frames_available > 0:
                    last_frame_start = (frames_available - 1) * self.bars
                    last_frame = buffer[last_frame_start : last_frame_start + self.bars]
                    buffer = buffer[frames_available * self.bars :]
                    
                    # Convertir bytes (0-255) a floats (0.0-1.0)
                    parsed = [b / 255.0 for b in last_frame]
                    
                    # Autoganancia extrema
                    max_val = max(parsed) if parsed else 0.0
                    if max_val > 0.01:
                        gain = min(1.0 / max_val, 5.0) # Ganancia máxima de 5x
                        parsed = [min(1.0, v * gain) for v in parsed]
                        
                    self.raw_data = parsed
            except BlockingIOError:
                time.sleep(0.005)
            except Exception as e:
                logger.error(f"Error procesando el flujo de CAVA: {e}")
                break

    def get_data(self, num_bars: int) -> list:
        """Adapta el arreglo crudo al tamaño requerido mediante interpolación matemática real."""
        if not self.raw_data or num_bars <= 0:
            return [0.0] * num_bars
            
        n_raw = len(self.raw_data)
        if n_raw == 1:
            return [self.raw_data[0]] * num_bars
            
        result = []
        for i in range(num_bars):
            # Mapeo posicional fraccional
            idx_float = i * (n_raw - 1) / max(1, num_bars - 1)
            idx_int = int(idx_float)
            frac = idx_float - idx_int
            
            if idx_int >= n_raw - 1:
                result.append(self.raw_data[-1])
            else:
                # Interpolar linealmente entre el índice actual y el siguiente
                v1 = self.raw_data[idx_int]
                v2 = self.raw_data[idx_int + 1]
                result.append(v1 + frac * (v2 - v1))
                
        return result