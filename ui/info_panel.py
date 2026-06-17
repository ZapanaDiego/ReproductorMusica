# ==========================================
# ARCHIVO: ui/info_panel.py  (v2 — Rediseño bi-zona)
# ==========================================
from rich.text import Text
from textual.containers import Vertical
from textual.widgets import Label


class InfoPanel(Vertical):
    """Panel lateral derecho: metadatos de pista activa + mapa de atajos completo."""

    def compose(self):
        # ── ZONA 1: Metadatos de la pista ───────────────────────────────────
        yield Label(
            "[bold #8A2BE2]♪  REPRODUCIENDO AHORA  ♪[/]",
            markup=True, id="info-header"
        )
        yield Label(
            "[#404060]────────────────────────────[/]", markup=True
        )
        yield Label("Sin título", id="info-title", classes="info-title")
        yield Label("Artista: —",   id="info-artist",   classes="info-meta")
        yield Label("Álbum:   —",   id="info-album",    classes="info-meta")
        yield Label("Dur:     —",   id="info-duration", classes="info-meta")
        yield Label("Rating:  —",   id="info-rating",   classes="info-meta")
        yield Label(
            "[#404060]────────────────────────────[/]", markup=True
        )

        # ── ZONA 2: Atajos — Reproducción ───────────────────────────────────
        yield Label(
            "[bold #FFFFFF]  CONTROLES DE REPRODUCCIÓN[/]", markup=True
        )
        yield Label("  [bold #00FFFF]Espacio[/]  Pause / Play",  markup=True)
        yield Label("  [bold #00FFFF]← →[/]      Pista ant/sig", markup=True)
        yield Label("  [bold #FF00FF]1  2  3[/]  Calificar ★",   markup=True)
        yield Label("  [bold #FF00FF]R[/]        Modo Aleatorio", markup=True)
        yield Label(
            "[#404060]────────────────────────────[/]", markup=True
        )

        # ── ZONA 3: Atajos — Vistas ─────────────────────────────────────────
        yield Label(
            "[bold #FFFFFF]  VISTAS  &  ÁLBUMES[/]", markup=True
        )
        yield Label("  [bold #8A2BE2]U I O P[/]  Cambiar vista",    markup=True)
        yield Label("  [bold #8A2BE2]Enter[/]    Abrir / Tocar",     markup=True)
        yield Label("  [bold #8A2BE2]A[/]        Añadir a álbum",    markup=True)
        yield Label("  [bold #8A2BE2]D / Supr[/] Eliminar álbum",    markup=True)
        yield Label("  [bold #8A2BE2]Esc[/]      Volver al listado", markup=True)
        yield Label(
            "[#404060]────────────────────────────[/]", markup=True
        )

        # ── ZONA 4: Usuario activo ───────────────────────────────────────────
        yield Label("  [bold #8A2BE2]♦[/] [bold #FFFFFF]SESIÓN:[/] —", markup=True, id="info-user")

    # ── API pública ────────────────────────────────────────────────────────

    def update_info(self, track) -> None:
        """Actualiza los metadatos de la pista. Llamar solo cuando cambia la pista."""
        if track:
            m, s = divmod(int(track.duration), 60)
            stars = ("★" * track.stars) + ("☆" * (3 - track.stars))
            self.query_one("#info-title",    Label).update(
                f"[bold #FFFFFF]{track.title}[/]"
            )
            self.query_one("#info-artist",   Label).update(
                f"  [#707080]Artista:[/] [#CCCCCC]{track.artist}[/]"
            )
            self.query_one("#info-album",    Label).update(
                f"  [#707080]Álbum:  [/] [#CCCCCC]{track.album}[/]"
            )
            self.query_one("#info-duration", Label).update(
                f"  [#707080]Dur:    [/] [#CCCCCC]{m:02d}:{s:02d}[/]"
            )
            self.query_one("#info-rating",   Label).update(
                f"  [#707080]Rating: [/] [bold #FF00FF]{stars}[/]"
            )

    def set_username(self, name: str) -> None:
        """Muestra el nombre del usuario activo en la zona 4."""
        self.query_one("#info-user", Label).update(
            f"  [bold #8A2BE2]♦[/] [bold #FFFFFF]SESIÓN:[/] [bold #00FFFF]{name}[/]"
        )
