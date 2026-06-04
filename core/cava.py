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
bars = {self.bars}
framerate = 100

[smoothing]
monstercat = 1
gravity = 140

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 1000
"""
        try:
            # Crear configuración temporal
            fd, path = tempfile.mkstemp(suffix='.conf', prefix='cava_')
            with os.fdopen(fd, 'w') as f:
                f.write(config)
            
            # Lanzar el subproceso real
            self.process = subprocess.Popen(
                ['cava', '-p', path],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )
            self._running = True
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()
            logger.info("Subproceso CAVA iniciado correctamente.")
            
        except FileNotFoundError:
            logger.error("Ejecutable 'cava' no encontrado en Linux. Se retornarán datos vacíos.")
        except Exception as e:
            logger.error(f"Error crítico al iniciar CAVA: {e}")

    def _read_loop(self):
        """Lee el stdout crudo constantemente."""
        while self._running and self.process:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                
                # CAVA retorna valores separados por ';'
                values = line.strip().split(';')
                parsed = [min(1.0, int(v) / 1000.0) for v in values if v.isdigit()]
                
                if parsed:
                    if len(parsed) < self.bars:
                        parsed.extend([0.0] * (self.bars - len(parsed)))
                    self.raw_data = parsed[:self.bars]
            except Exception as e:
                logger.error(f"Error procesando el flujo de CAVA: {e}")
                break

    def get_data(self, num_bars: int) -> list:
        """Adapta el arreglo crudo al tamaño requerido por la UI."""
        if not self.raw_data:
            return [0.0] * num_bars
        step = max(1, len(self.raw_data) / num_bars)
        return [self.raw_data[min(int(i * step), len(self.raw_data)-1)] for i in range(num_bars)]