# ==========================================
# ARCHIVO: core/bridge.py
# ==========================================
# Abstracción estricta entre el frontend (UI Textual) y el backend.
# El visualizador ahora consume get_audio_bars() en lugar de CAVA.
# Ningún módulo de UI importa ni conoce MockBackend directamente.
# ==========================================

from core.backend import MockBackend
from core.cava import CavaSubprocess


class MusicBridge:
    """
    Fachada de acceso único al backend.

    Política de diseño:
    - El frontend solo puede invocar comandos a través de aquí.
    - Oculta completamente la implementación interna del backend.
    - get_audio_bars() delega al generador espectral nativo del backend,
      eliminando cualquier dependencia de CAVA u otro subproceso externo.
    """

    def __init__(self):
        self.backend = MockBackend()
        self.cava = CavaSubprocess()

    # ── Controles de reproducción ────────────────────────────────────────
    def play(self):                  self.backend.play()
    def pause(self):                 self.backend.pause()
    def toggle_play(self):           self.backend.toggle_play()
    def next(self):                  self.backend.next_track()
    def prev(self):                  self.backend.prev_track()

    # ── Consultas de estado ──────────────────────────────────────────────
    def get_current_track(self):     return self.backend.get_current_track()
    def get_progress(self):          return self.backend.progress
    def is_playing(self):            return self.backend.is_playing
    def get_current_index(self):     return self.backend.current_index
    def jump_to_index(self, index):  self.backend.jump_to_queue_index(index)

    # ── Biblioteca y cola ────────────────────────────────────────────────
    def get_library(self):           return self.backend.library
    def get_queue(self):             return self.backend.queue
    def get_queue_version(self):     return self.backend.queue_version
    def get_directories(self):       return self.backend.get_directories()

    # ── Configuración ────────────────────────────────────────────────────
    def toggle_random(self):         return self.backend.toggle_random()
    def is_random_mode(self):        return self.backend.is_random_mode
    def set_rating(self, track_id, stars): self.backend.set_rating(track_id, stars)

    # ── Espectro visual (reemplaza get_cava_data) ────────────────────────
    def get_audio_bars(self, num_bars: int) -> list[float]:
        """
        Delega al generador espectral CAVA nativo.

        Si el reproductor está en pausa o no hay pista activa, retorna
        directamente una lista de ceros, garantizando que el
        visualizador decaiga a silencio sin latencia adicional.

        Args:
            num_bars: número de barras que solicita el widget visualizador.

        Returns:
            Lista de floats en [0.0, 1.0] con la energía por banda.
        """
        if not self.is_playing():
            return [0.0] * num_bars
        return self.cava.get_data(num_bars)

    def get_acoustic_dna(self) -> dict:
        """Huella acústica de la pista activa (semilla, perfil, color ambiental)."""
        return self.backend.get_acoustic_dna()