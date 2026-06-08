# ==========================================
# ARCHIVO: core/bridge.py
# ==========================================
# Abstracción estricta entre el frontend (UI Textual) y el backend.
# El visualizador ahora consume get_audio_bars() en lugar de CAVA.
# Ningún módulo de UI importa ni conoce MockBackend directamente.
# ==========================================

from core.backend import MockBackend


class MusicBridge:
    """
    Fachada pura (Facade Pattern) entre el frontend y el backend.

    Política de diseño — capa de abstracción intermedia y SIN lógica propia:
    - Traduce señales de la UI en comandos del backend.
    - Recibe las estructuras de datos crudas del backend y las entrega tal cual.
    - No posee estado ni recursos: ni audio, ni hilos, ni CAVA. Todo eso vive
      en el backend. Cuando este se reescriba en C++, solo cambia `self.backend`;
      esta fachada permanece idéntica.
    """

    def __init__(self):
        self.backend = MockBackend()

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

    # ── Comandos de alto nivel (la UI solo manda pestaña + fila) ──────────
    def play_selection(self, tab, row):        self.backend.play_selection(tab, row)
    def rate_selection(self, tab, row, stars): self.backend.rate_selection(tab, row, stars)

    # ── Biblioteca y cola ────────────────────────────────────────────────
    def get_library(self):           return self.backend.library
    def get_queue(self):             return self.backend.queue
    def get_queue_version(self):     return self.backend.queue_version
    def get_library_version(self):   return self.backend.library_version
    def get_directories(self):       return self.backend.get_directories()

    # ── Configuración ────────────────────────────────────────────────────
    def toggle_random(self):         return self.backend.toggle_random()
    def is_random_mode(self):        return self.backend.is_random_mode
    def set_rating(self, track_id, stars): self.backend.set_rating(track_id, stars)

    # ── Espectro visual ──────────────────────────────────────────────────
    def get_audio_bars(self, num_bars: int) -> list[float]:
        """Entrega el espectro calculado por el backend (que posee CAVA)."""
        return self.backend.get_audio_bars(num_bars)

    def get_acoustic_dna(self) -> dict:
        """Huella acústica de la pista activa (semilla, perfil, color ambiental)."""
        return self.backend.get_acoustic_dna()