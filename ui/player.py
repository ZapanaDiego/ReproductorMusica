# ==========================================
# ARCHIVO: ui_player.py
# ==========================================
from rich.text import Text
from textual.containers import Vertical, Horizontal
from textual.widgets import Label, ProgressBar

class PlayerBottomBar(Horizontal):
    """Barra inferior minimalista flotante de Musikcube."""
    def compose(self):
        yield Label("▶ SONANDO AHORA", id="play-state")
        with Vertical(id="track-info-container"):
            yield Label("Ninguna pista activa", id="track-title")
            yield ProgressBar(total=100, show_eta=False, id="progress-bar")
        yield Label("00:00 / 00:00", id="time-info")

    def format_time(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    def update_track(self, track, is_playing: bool):
        """Refresca estado y título. Llamar solo cuando la pista/estado cambian."""
        if track:
            state = "▶ SONANDO AHORA" if is_playing else "⏸ EN PAUSA"
            self.query_one("#play-state", Label).update(state)
            self.query_one("#track-title", Label).update(
                Text.assemble((track.title, "bold #FFFFFF"), (" - ", "#707080"), (track.artist, "#707080"))
            )

    def update_progress(self, track, progress: float):
        """Refresca barra y tiempo. Barato; se llama en cada tick."""
        if track:
            self.query_one("#progress-bar", ProgressBar).update(total=track.duration, progress=progress)
            self.query_one("#time-info", Label).update(
                f"{self.format_time(progress)} / {self.format_time(track.duration)}"
            )