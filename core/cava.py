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
        self._interp_cache = {}   # (num_bars, n_raw) -> [(idx_int, frac), ...]
        self._start_cava()

    def _start_cava(self):
        import platform
        import os

        # 1. Detección ESTRICTA (Sin buscar archivos para evitar falsos positivos en Linux)
        is_windows = platform.system() == "Windows" or os.name == "nt"

        # 2. El target de salida binaria varía ligeramente según el sistema
        raw_target = "stdout" if is_windows else "/dev/stdout"

        config_lines = [
            "[general]",
            "framerate = 30",
            f"bars = {self.bars}",
            "autosens = 1",
            "",
            "[smoothing]",
            "monstercat = 1",
            "gravity = 150",
            "ignore = 0",
            "",
            "[output]",
            "method = raw",
            "raw_target = " + raw_target,
            "data_format = binary",
            "bit_format = 8bit"
        ]

        # 3. Inyección WASAPI Loopback solo si estamos verdaderamente en Windows
        if is_windows:
            config_lines.insert(0, "[input]\nmethod = wasapi\nsource = loopback\n")

        config = "\n".join(config_lines)

        try:
            fd, path = tempfile.mkstemp(suffix='.conf', prefix='cava_')
            
            # 4. Escribir y CERRAR explícitamente el archivo para evitar bloqueos en Windows
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(config)
            
            # --- AQUÍ EL ARCHIVO YA ESTÁ CERRADO Y LIBRE ---

            cava_exe = './cava.exe' if is_windows else 'cava'
            
            entorno = "WINDOWS (WASAPI Activado)" if is_windows else "LINUX (Nativo)"
            logger.info(f"Lanzando CAVA en modo: {entorno}")
            logger.info(f"Configuración inyectada:\n{config}")
            
            # 5. Lanzar el proceso de forma segura
            self.process = subprocess.Popen(
                [cava_exe, '-p', path],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            self._running = True
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()
            
        except FileNotFoundError:
            logger.error(f"Ejecutable '{cava_exe}' no encontrado. Se retornarán datos vacíos.")
        except Exception as e:
            logger.error(f"Error crítico al iniciar CAVA: {e}")

    def _read_loop(self):
        """
        Lee el stdout binario en modo BLOQUEANTE.

        ``os.read`` duerme en el kernel hasta que CAVA emite un frame, por lo
        que el hilo consume ~0% de CPU en reposo (antes hacía polling activo a
        ~200 Hz con sleeps). Seguimos quedándonos solo con el último frame
        disponible para eliminar el buffer bloat sin coste extra.
        """
        bars = self.bars
        fd = self.process.stdout.fileno()
        buffer = bytearray()

        while self._running and self.process:
            try:
                chunk = os.read(fd, 4096)   # bloqueante: cede la CPU hasta tener datos
                if not chunk:
                    break
                buffer.extend(chunk)

                frames_available = len(buffer) // bars
                if frames_available > 0:
                    last_frame_start = (frames_available - 1) * bars
                    last_frame = buffer[last_frame_start : last_frame_start + bars]
                    del buffer[: frames_available * bars]

                    parsed = [b / 255.0 for b in last_frame]

                    # Autoganancia extrema (techo 5x)
                    max_val = max(parsed)
                    if max_val > 0.01:
                        gain = min(1.0 / max_val, 5.0)
                        parsed = [v * gain if v * gain < 1.0 else 1.0 for v in parsed]

                    self.raw_data = parsed
            except Exception as e:
                logger.error(f"Error procesando el flujo de CAVA: {e}")
                break

    def _interp_map(self, num_bars: int, n_raw: int) -> list:
        """
        Mapa de interpolación (idx_int, frac) precalculado UNA vez por tamaño.

        El nº de barras crudas de CAVA es fijo, así que estos índices no cambian
        entre frames: cachearlos elimina una división + resta por barra en cada
        uno de los ~25-33 frames/seg del visualizador.
        """
        key = (num_bars, n_raw)
        cached = self._interp_cache.get(key)
        if cached is not None:
            return cached

        last = n_raw - 1
        denom = max(1, num_bars - 1)
        table = []
        for i in range(num_bars):
            idx_float = i * last / denom
            idx_int = int(idx_float)
            if idx_int >= last:
                table.append((last, 0.0))
            else:
                table.append((idx_int, idx_float - idx_int))
        self._interp_cache[key] = table
        return table

    def get_data(self, num_bars: int) -> list:
        """Adapta el arreglo crudo al tamaño pedido por interpolación lineal."""
        raw = self.raw_data
        if not raw or num_bars <= 0:
            return [0.0] * num_bars

        n_raw = len(raw)
        if n_raw == 1:
            return [raw[0]] * num_bars

        table = self._interp_map(num_bars, n_raw)
        # frac==0.0 -> devuelve raw[i] directo y nunca indexa i+1 (seguro en el borde)
        return [
            raw[i] + frac * (raw[i + 1] - raw[i]) if frac else raw[i]
            for (i, frac) in table
        ]