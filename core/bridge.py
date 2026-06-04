# ==========================================
# ARCHIVO: core_bridge.py
# ==========================================
from core.backend import MockBackend
from core.cava import CavaSubprocess

class MusicBridge:
    """
    Abstracción Estricta. El Frontend solo puede invocar comandos a través de aquí.
    """
    def __init__(self):
        self.backend = MockBackend()
        self.cava = CavaSubprocess()

    def play(self): self.backend.play()
    def pause(self): self.backend.pause()
    def toggle_play(self): self.backend.toggle_play()
    def next(self): self.backend.next_track()
    def prev(self): self.backend.prev_track()
    
    def get_current_track(self): return self.backend.get_current_track()
    def get_progress(self): return self.backend.progress
    def is_playing(self): return self.backend.is_playing
    def get_current_index(self): return self.backend.current_index
    def jump_to_index(self, index): self.backend.jump_to_queue_index(index)
    
    def get_library(self): return self.backend.library
    def get_queue(self): return self.backend.queue
    def get_queue_version(self): return self.backend.queue_version
    def get_directories(self): return self.backend.get_directories()
    
    def toggle_random(self): return self.backend.toggle_random()
    def is_random_mode(self): return self.backend.is_random_mode
    def set_rating(self, track_id, stars): self.backend.set_rating(track_id, stars)

    def get_cava_data(self, num_bars):
        # Si está pausado, las frecuencias caen a 0
        if not self.is_playing():
            return [0.0] * num_bars
        return self.cava.get_data(num_bars)