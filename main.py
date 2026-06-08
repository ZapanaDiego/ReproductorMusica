#!/usr/bin/env python3
# ==========================================
# ARCHIVO: main.py
# ==========================================
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Label, ContentSwitcher, DataTable

from core.bridge import MusicBridge
from core.input import InputController
from ui.visualizer import CavaVisualizer
from ui.views import LibraryView, RandomQueueView, DirectoriesView
from ui.player import PlayerBottomBar
from ui.info_panel import InfoPanel

class MusicPlayerApp(App):
    CSS_PATH = "styles.tcss"

    def __init__(self):
        super().__init__()
        self.bridge = MusicBridge()
        self.input_manager = InputController(self.bridge, self)
        
        self.active_tab = "library"
        self.last_queue_version = -1

    def compose(self) -> ComposeResult:
        with Container(id="main-layout"):
            
            # SECCIÓN SUPERIOR (70% Tablas / 30% Info)
            with Horizontal(id="top-section"):
                
                # PANEL 1: Tablas
                with Vertical(id="panel-left", classes="glass-panel"):
                    with Horizontal(id="top-tabs"):
                        yield Label("  [U] BIBLIOTECA  ", id="tab-library", classes="tab-label active")
                        yield Label("  [I] COLA ALEATORIA  ", id="tab-queue", classes="tab-label")
                        yield Label("  [O] DIRECTORIOS  ", id="tab-directories", classes="tab-label")

                    with ContentSwitcher(initial="library", id="views-switcher"):
                        yield LibraryView(id="library")
                        yield RandomQueueView(id="queue")
                        yield DirectoriesView(id="directories")
                
                # PANEL 2: Info y Atajos
                with Vertical(id="panel-right", classes="glass-panel"):
                    yield InfoPanel(id="info-panel")
            
            # PANEL 3: Visualizador y Reproductor
            with Vertical(id="panel-bottom", classes="glass-panel"):
                yield CavaVisualizer()
                yield PlayerBottomBar(id="bottom-bar")

    def on_mount(self) -> None:
        self.query_one("#table-library", DataTable).add_columns("ID", "Música", "Artista", "Calificación")
        self.query_one("#table-queue", DataTable).add_columns("ID", "Música", "Artista", "Calificación")
        self.query_one("#table-directories", DataTable).add_columns("Directorio Escaneado", "Estado del Sistema")

        self.set_interval(0.1, self.update_ui)
        self._populate_all()
        self.bridge.play()

    def on_key(self, event) -> None:
        """Delega ABSOLUTAMENTE TODO el control de teclado al InputController."""
        self.input_manager.handle_key(event.key.lower())

    # --- COMANDOS EXPUESTOS PARA EL INPUT MANAGER ---

    def switch_tab(self, tab_name: str):
        self.active_tab = tab_name
        for t in ["library", "queue", "directories"]:
            self.query_one(f"#tab-{t}", Label).remove_class("active")

        self.query_one(f"#tab-{tab_name}", Label).add_class("active")
        self.query_one("#views-switcher", ContentSwitcher).current = tab_name
        
        table = self.query_one(f"#table-{tab_name}", DataTable)
        table.focus()
        self.force_queue_repaint()

    def notify_random_mode(self, is_rand: bool):
        mode_label = "  [I] COLA ALEATORIA (RND)  " if is_rand else "  [I] COLA ALEATORIA  "
        self.query_one("#tab-queue", Label).update(mode_label)
        self._populate_all()
        self.force_queue_repaint()

    def play_current_selection(self):
        table = self.query_one(f"#table-{self.active_tab}", DataTable)
        if table.cursor_row is not None:
            if self.active_tab == "queue":
                self.bridge.jump_to_index(table.cursor_row)
            elif self.active_tab == "library":
                track = self.bridge.get_library()[table.cursor_row]
                for i, t in enumerate(self.bridge.get_queue()):
                    if t.id == track.id:
                        self.bridge.jump_to_index(i)
                        break
            self.force_queue_repaint()

    def rate_current_selection(self, stars: int):
        table = self.query_one(f"#table-{self.active_tab}", DataTable)
        if table.cursor_row is not None:
            track = None
            if self.active_tab == "library":
                track = self.bridge.get_library()[table.cursor_row]
            elif self.active_tab == "queue":
                track = self.bridge.get_queue()[table.cursor_row]
            
            if track:
                self.bridge.set_rating(track.id, stars)
                self._populate_all()
                table.move_cursor(row=table.cursor_row)

    def force_queue_repaint(self):
        self.last_queue_version = -1

    # --- RENDERIZADO Y ACTUALIZACIÓN UI ---

    def _format_row(self, track, is_playing=False):
        title_style = "bold #00FFFF" if is_playing else "bold #FFFFFF"
        indicator = "▶ " if is_playing else "  "
        t_id = Text(f"{track.id:03d}", style="bold #00FFFF" if is_playing else "#707080")
        title = Text(f"{indicator}{track.title}", style=title_style)
        artist = Text(track.artist, style="#FFFFFF" if is_playing else "#707080")
        stars = Text(("★" * track.stars) + ("☆" * (3 - track.stars)), style="bold #FF00FF")
        return (t_id, title, artist, stars)

    def _populate_all(self):
        table_lib = self.query_one("#table-library", DataTable)
        table_lib.clear()
        for t in self.bridge.get_library():
            table_lib.add_row(*self._format_row(t))

        table_que = self.query_one("#table-queue", DataTable)
        table_que.clear()
        for t in self.bridge.get_queue():
            table_que.add_row(*self._format_row(t))

        table_dir = self.query_one("#table-directories", DataTable)
        table_dir.clear()
        for d in self.bridge.get_directories():
            table_dir.add_row(Text(d["Directorio"], style="#FFFFFF"), Text(d["Existe"], style="#00FFFF"))

    def update_ui(self):
        track = self.bridge.get_current_track()
        self.query_one("#bottom-bar", PlayerBottomBar).update_status(
            track, self.bridge.is_playing(), self.bridge.get_progress()
        )
        self.query_one("#info-panel", InfoPanel).update_info(track)

        curr_version = self.bridge.get_queue_version()
        if curr_version != self.last_queue_version:
            self.last_queue_version = curr_version
            table_que = self.query_one("#table-queue", DataTable)
            table_que.clear()
            for t in self.bridge.get_queue():
                table_que.add_row(*self._format_row(t))

        if self.active_tab == "queue" and track:
            table = self.query_one("#table-queue", DataTable)
            curr_idx = self.bridge.get_current_index()
            if 0 <= curr_idx < len(table.rows):
                table.move_cursor(row=curr_idx)

if __name__ == "__main__":
    app = MusicPlayerApp()
    app.run()