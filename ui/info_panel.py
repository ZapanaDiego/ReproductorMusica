# ==========================================
# ARCHIVO: ui_info_panel.py
# ==========================================
from rich.text import Text
from textual.containers import Vertical
from textual.widgets import Label

class InfoPanel(Vertical):
    """Panel lateral derecho para información de pista y atajos."""
    
    def compose(self):
        # Mitad superior: Metadatos
        yield Label("Ninguna pista activa", id="info-title", classes="info-title")
        yield Label("Artista: -", id="info-artist", classes="info-meta")
        yield Label("Calificación: -", id="info-rating", classes="info-meta")
        
        # Espaciador
        yield Label(" ")
        
        # Mitad inferior: Atajos Neón
        yield Label("[bold #FFFFFF]-- ATAJOS --[/]", markup=True)
        yield Label("[bold #00FFFF]Espacio:[/] Pause/Play", markup=True)
        yield Label("[bold #00FFFF]Flechas:[/] Navegar", markup=True)
        yield Label("[bold #FF00FF]1,2,3:[/] Calificar", markup=True)
        yield Label("[bold #FF00FF]R:[/] Aleatorio", markup=True)
        yield Label("[bold #8A2BE2]U,I,O:[/] Vistas", markup=True)

    def update_info(self, track):
        if track:
            self.query_one("#info-title", Label).update(f"[bold #FFFFFF]{track.title}[/]")
            self.query_one("#info-artist", Label).update(f"[bold #707080]Artista:[/] {track.artist}")
            stars = ("★" * track.stars) + ("☆" * (3 - track.stars))
            self.query_one("#info-rating", Label).update(f"[bold #707080]Rating:[/] [bold #FF00FF]{stars}[/]")
