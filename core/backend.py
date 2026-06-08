# ==========================================
# ARCHIVO: core/backend.py
# ==========================================
# Módulo de núcleo de negocio del reproductor de música.
# Contiene: gestión de biblioteca, cola de reproducción,
# control de Pygame y el generador espectral matemático nativo.
# ==========================================

import os
import json
import math
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


# ---------------------------------------------------------------------------
# MODELO DE DATOS: Track
# Representa una pista de audio con sus metadatos esenciales.
# ---------------------------------------------------------------------------

class Track:
    def __init__(self, id, title, artist, album, duration, path, stars=1):
        self.id       = id
        self.title    = title
        self.artist   = artist
        self.album    = album
        self.duration = duration
        self.path     = path
        self.stars    = stars

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


# ---------------------------------------------------------------------------
# NÚCLEO DE NEGOCIO: MockBackend
# Gestiona la biblioteca, la cola, el progreso y el
# ANALIZADOR ESPECTRAL MATEMÁTICO NATIVO SÍNCRONO.
# ---------------------------------------------------------------------------

class MockBackend:
    """
    Núcleo del negocio. Sin interfaces. Solo datos y reproducción.

    El generador espectral (get_audio_bars) es 100% nativo:
    no depende de subprocesos externos (CAVA). Calcula frecuencias
    combinando ondas sinusoidales armónicas, ruido algorítmico y
    envolventes rítmicas derivadas del estado del reproductor.
    """

    def __init__(self):
        self.library        = []
        self.queue          = []
        self.current_index  = -1
        self.is_playing     = False
        self.progress       = 0.0
        self.queue_version  = 0

        self._lock      = threading.Lock()
        self.db_path    = "library.json"

        self._init_library()
        self.is_random_mode = False
        self.generate_queue()

        self._running   = True
        self._last_tick = time.time()
        self._thread    = threading.Thread(target=self._playback_loop, daemon=True)
        self._thread.start()
        logger.info("Backend instanciado y bucle de audio iniciado.")

    # -----------------------------------------------------------------------
    # INICIALIZACIÓN DE LA BIBLIOTECA
    # -----------------------------------------------------------------------

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
            for t, a, d in [
                ("Grid de Neon",      "SynthWeaver", 210),
                ("Fallo de Nucleo",   "Hacker.exe",  185),
                ("Lluvia Sintetica",  "Replicant",   305),
            ]:
                self.library.append(Track(
                    track_id, t, a, "Cyber", d,
                    f"/mock/{t}.mp3", random.randint(1, 3)
                ))
                track_id += 1

        self._save_library()

    def _save_library(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self.library], f, indent=4)
        logger.info("library.json sobreescrito con éxito.")

    # -----------------------------------------------------------------------
    # GESTIÓN DE COLA Y CONTROL DE REPRODUCCIÓN
    # -----------------------------------------------------------------------

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
            self.progress      = 0.0
            self.queue_version += 1
            if self.is_playing:
                self._play_current_real()

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
        if not HAS_PYGAME:
            return
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
                if not pygame.mixer.music.get_busy():
                    self._play_current_real()
                else:
                    pygame.mixer.music.unpause()

    def pause(self):
        self.is_playing = False
        logger.info("Reproducción PAUSADA.")
        if HAS_PYGAME:
            pygame.mixer.music.pause()

    def toggle_play(self):
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def next_track(self):
        with self._lock:
            if self.queue:
                self.current_index = (self.current_index + 1) % len(self.queue)
                self.progress      = 0.0
                self.is_playing    = True
                logger.info("Salto a pista SIGUIENTE.")
                self._play_current_real()

    def prev_track(self):
        with self._lock:
            if self.progress > 3.0:
                self.progress = 0.0
            elif self.queue:
                self.current_index = (self.current_index - 1) % len(self.queue)
                self.progress      = 0.0
            self.is_playing = True
            logger.info("Salto a pista ANTERIOR.")
            self._play_current_real()

    def jump_to_queue_index(self, index):
        with self._lock:
            if 0 <= index < len(self.queue):
                self.current_index = index
                self.progress      = 0.0
                self.is_playing    = True
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
                if t.id == track_id:
                    t.stars = stars

    # -----------------------------------------------------------------------
    # BUCLE DE PROGRESO DE REPRODUCCIÓN
    # Actualiza `self.progress` con precisión de reloj del sistema.
    # -----------------------------------------------------------------------

    def _playback_loop(self):
        """Calcula el progreso matemáticamente preciso."""
        while self._running:
            time.sleep(0.05)
            now = time.time()
            dt  = now - self._last_tick
            self._last_tick = now

            with self._lock:
                if self.is_playing and self.queue:
                    current_track    = self.queue[self.current_index]
                    self.progress   += dt

                    if self.progress >= current_track.duration:
                        self.progress = 0.0
                        self._lock.release()
                        self.next_track()
                        self._lock.acquire()

    # Paleta nocturna compartida con la UI (una atmósfera por perfil de ADN).
    AMBIENT_PALETTE = ("#0c0014", "#001014", "#001408")

    @staticmethod
    def _acoustic_seed_from_track(track) -> int:
        """
        Genera la semilla entera determinista del ADN Acústico.

        Fórmula de mapeo (hash por suma ponderada ASCII):
            seed = Σ ord(c_i) × (i + 1)
        donde c_i recorre la cadena ``"{title}-{artist}-{id}"``.

        La ponderación por índice evita colisiones triviales entre pistas
        con los mismos caracteres en distinto orden.
        """
        if track is None:
            return 0
        title = track.title if getattr(track, "title", None) else "Unknown"
        artist = track.artist if getattr(track, "artist", None) else "Unknown"
        track_id_str = str(getattr(track, "id", 0))
        seed_string = f"{title}-{artist}-{track_id_str}"
        return sum(ord(c) * (i + 1) for i, c in enumerate(seed_string))

    def get_acoustic_dna(self) -> dict:
        """
        Huella acústica de la pista activa para sincronizar backend y UI.

        Retorna seed, perfil espectral (0=bass, 1=mid, 2=treble) y el
        color ambiental nocturno exclusivo de esa canción.
        """
        track = self.get_current_track()
        if track is None:
            return {
                "seed": 0,
                "profile": 0,
                "ambient_hex": "#000000",
                "bass_mult": 1.0,
                "mid_mult": 1.0,
                "treble_mult": 1.0,
            }
        seed = self._acoustic_seed_from_track(track)
        profile = seed % 3
        mults = [(1.25, 0.85, 0.85), (0.85, 1.25, 0.85), (0.85, 0.85, 1.25)]
        bass_mult, mid_mult, treble_mult = mults[profile]
        return {
            "seed": seed,
            "profile": profile,
            "ambient_hex": self.AMBIENT_PALETTE[profile],
            "bass_mult": bass_mult,
            "mid_mult": mid_mult,
            "treble_mult": treble_mult,
        }

    def get_audio_bars(self, num_bars: int) -> list[float]:
        """
        Espectro rítmico bass-centric: un único pulso ``beat_impact`` sincroniza
        todo el ecualizador. Picos afilados hasta 1.0; sin ondas sinusoidales
        independientes que aplanen la energía.
        """
        track = self.get_current_track()
        if not self.is_playing or track is None:
            return [0.0] * num_bars

        seed = self._acoustic_seed_from_track(track)
        bpm_hz = (80 + (seed * 17) % 80) / 60.0
        t = time.time()

        # Pulso de bajo: subida/caida rápida, pico exacto en 1.0.
        beat_impact = math.pow(abs(math.sin(t * bpm_hz * math.pi)), 4)

        bass_end = max(1, int(num_bars * 0.40))
        bars: list[float] = []

        for i in range(num_bars):
            if i < bass_end:
                noise = ((seed + i * 13 + int(t * 60)) & 0xFF) / 255.0 * 0.08
                value = min(1.0, beat_impact + noise)
            else:
                pos = (i - bass_end) / max(num_bars - bass_end - 1, 1)
                fraction = 0.85 - pos * 0.55
                value = beat_impact * max(0.15, fraction)

            bars.append(max(0.0, min(1.0, value)))

        return bars