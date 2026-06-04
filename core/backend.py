# ==========================================
# ARCHIVO: core_backend.py
# ==========================================
import os
import json
import time
import random
import threading
from pathlib import Path
from core.logger import get_logger

logger = get_logger("Backend")

try:
    import pygame
    HAS_PYGAME = True
    pygame.mixer.init()
    logger.info("Motor de audio Pygame inicializado.")
except Exception:
    HAS_PYGAME = False
    logger.warning("Pygame no disponible. Modo simulación activado.")

class Track:
    def __init__(self, id, title, artist, album, duration, path, stars=1):
        self.id = id
        self.title = title
        self.artist = artist
        self.album = album
        self.duration = duration
        self.path = path
        self.stars = stars

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class MockBackend:
    """Núcleo del negocio. Sin interfaces. Solo datos y reproducción."""
    def __init__(self):
        self.library = []
        self.queue = []
        self.current_index = -1
        self.is_playing = False
        self.progress = 0.0
        self.queue_version = 0
        
        self._lock = threading.Lock()
        self.db_path = "library.json"
        
        self._init_library()
        self.is_random_mode = False
        self.generate_queue()
        
        self._running = True
        self._last_tick = time.time()
        self._thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._thread.start()
        logger.info("Backend instanciado y bucle de audio iniciado.")

    def _init_library(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.library = [Track.from_dict(t) for t in json.load(f)]
                logger.info(f"Base de datos cargada. {len(self.library)} pistas.")
                if self.library:
                    return
            except Exception as e:
                logger.error(f"Error leyendo JSON: {e}")
        self._scan_and_populate()

    def _scan_and_populate(self):
        logger.info("Escaneando directorios de música...")
        self.library = []
        paths_to_check = [Path.home() / "Música", Path.home() / "Music"]
        track_id = 1
        
        for p in paths_to_check:
            if p.exists() and p.is_dir():
                for root, _, files in os.walk(p):
                    for file in files:
                        if file.endswith(('.mp3', '.wav', '.ogg', '.flac')):
                            self.library.append(Track(
                                track_id, file.rsplit('.', 1)[0][:35],
                                "Artista Local", "Local", random.randint(150, 280),
                                os.path.join(root, file), 1
                            ))
                            track_id += 1
        
        if len(self.library) < 5:
            logger.info("Pocas canciones detectadas. Inyectando Dummies Cyberpunk.")
            for t, a, d in [("Grid de Neon", "SynthWeaver", 210), ("Fallo de Nucleo", "Hacker.exe", 185), ("Lluvia Sintetica", "Replicant", 305)]:
                self.library.append(Track(track_id, t, a, "Cyber", d, f"/mock/{t}.mp3", random.randint(1, 3)))
                track_id += 1
                
        self._save_library()

    def _save_library(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self.library], f, indent=4)
        logger.info("library.json sobreescrito con éxito.")

    def generate_queue(self):
        with self._lock:
            if self.is_random_mode:
                pool = []
                for t in self.library:
                    pool.extend([t] * (1 if t.stars == 1 else 3 if t.stars == 2 else 6))
                random.shuffle(pool)
                self.queue = pool
                logger.info(f"Cola aleatoria generada: {len(self.queue)} elementos.")
            else:
                self.queue = list(self.library)
            
            self.current_index = 0 if self.queue else -1
            self.progress = 0.0
            self.queue_version += 1
            if self.is_playing: self._play_current_real()

    def toggle_random(self):
        self.is_random_mode = not self.is_random_mode
        logger.info(f"Modo Random alternado a: {self.is_random_mode}")
        self.generate_queue()
        return self.is_random_mode

    def get_current_track(self):
        if self.queue and 0 <= self.current_index < len(self.queue):
            return self.queue[self.current_index]
        return None

    def get_directories(self):
        paths = [str(Path.home() / "Música"), str(Path.home() / "Music")]
        return [{"Directorio": p, "Existe": "SÍ" if os.path.exists(p) else "NO"} for p in paths]

    def _play_current_real(self):
        if not HAS_PYGAME: return
        track = self.get_current_track()
        if track and os.path.exists(track.path):
            try:
                pygame.mixer.music.load(track.path)
                pygame.mixer.music.play()
            except Exception as e:
                logger.error(f"Fallo al reproducir en Pygame: {e}")

    def play(self):
        if self.queue:
            self.is_playing = True
            logger.info("Reproducción INICIADA.")
            if HAS_PYGAME:
                if not pygame.mixer.music.get_busy(): self._play_current_real()
                else: pygame.mixer.music.unpause()

    def pause(self):
        self.is_playing = False
        logger.info("Reproducción PAUSADA.")
        if HAS_PYGAME: pygame.mixer.music.pause()

    def toggle_play(self):
        if self.is_playing: self.pause()
        else: self.play()

    def next_track(self):
        with self._lock:
            if self.queue:
                self.current_index = (self.current_index + 1) % len(self.queue)
                self.progress = 0.0
                self.is_playing = True
                logger.info("Salto a pista SIGUIENTE.")
                self._play_current_real()

    def prev_track(self):
        with self._lock:
            if self.progress > 3.0:
                self.progress = 0.0
            elif self.queue:
                self.current_index = (self.current_index - 1) % len(self.queue)
                self.progress = 0.0
            self.is_playing = True
            logger.info("Salto a pista ANTERIOR.")
            self._play_current_real()

    def jump_to_queue_index(self, index):
        with self._lock:
            if 0 <= index < len(self.queue):
                self.current_index = index
                self.progress = 0.0
                self.is_playing = True
                logger.info(f"Salto directo al índice: {index}.")
                self._play_current_real()

    def set_rating(self, track_id, stars):
        target = next((t for t in self.library if t.id == track_id), None)
        if target and 1 <= stars <= 3:
            target.stars = stars
            logger.info(f"Rating actualizado: Pista {track_id} -> {stars} Estrellas.")
            self._save_library()
            self.queue_version += 1
            for t in self.queue:
                if t.id == track_id: t.stars = stars

    def _playback_loop(self):
        """Calcula el progreso matemáticamente preciso."""
        while self._running:
            time.sleep(0.05)
            now = time.time()
            dt = now - self._last_tick
            self._last_tick = now

            with self._lock:
                if self.is_playing and self.queue:
                    current_track = self.queue[self.current_index]
                    self.progress += dt
                    
                    if self.progress >= current_track.duration:
                        self.progress = 0.0
                        self._lock.release()
                        self.next_track()
                        self._lock.acquire()