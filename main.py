#!/usr/bin/env python3
# ==========================================
# ARCHIVO: main.py
# ==========================================
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Label, ContentSwitcher, DataTable
from pathlib import Path

from core.bridge import MusicBridge
from core.input import InputController
from ui.visualizer import CavaVisualizer
from ui.views import LibraryView, RandomQueueView, DirectoriesView
from ui.player import PlayerBottomBar
from ui.info_panel import InfoPanel

class MusicPlayerApp(App):
    CSS_PATH = Path("styles.tcss")

    def __init__(self, user_data=None):
        super().__init__()
        self.bridge = MusicBridge(user_data)
        self.input_manager = InputController(self.bridge, self)
        
        self.active_tab = "library"
        # Versiones cacheadas: la UI solo repuebla DataTables cuando cambian.
        self.last_queue_version   = -1
        self.last_library_version = -1
        # Estado cacheado para evitar reparsear etiquetas cada tick.
        self._last_track_id = -999
        self._last_playing  = None

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

        # Poblado inicial único. A partir de aquí, las tablas solo se
        # reconstruyen cuando cambia su versión (cola/biblioteca).
        self._populate_initial()
        self.last_queue_version   = self.bridge.get_queue_version()
        self.last_library_version = self.bridge.get_library_version()

        self.set_interval(0.1, self.update_ui)
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
        self.query_one(f"#table-{tab_name}", DataTable).focus()

    def notify_random_mode(self, is_rand: bool):
        # Solo cambia la etiqueta visual; el repintado de la cola lo dispara
        # el cambio de queue_version detectado en update_ui.
        mode_label = "  [I] COLA ALEATORIA (RND)  " if is_rand else "  [I] COLA ALEATORIA  "
        self.query_one("#tab-queue", Label).update(mode_label)

    def play_current_selection(self):
        table = self.query_one(f"#table-{self.active_tab}", DataTable)
        if table.cursor_row is not None:
            self.bridge.play_selection(self.active_tab, table.cursor_row)

    def rate_current_selection(self, stars: int):
        table = self.query_one(f"#table-{self.active_tab}", DataTable)
        if table.cursor_row is not None:
            self.bridge.rate_selection(self.active_tab, table.cursor_row, stars)

    # --- RENDERIZADO Y ACTUALIZACIÓN UI ---

    def _format_row(self, track, is_playing=False):
        title_style = "bold #00FFFF" if is_playing else "bold #FFFFFF"
        indicator = "▶ " if is_playing else "  "
        t_id = Text(f"{track.id:03d}", style="bold #00FFFF" if is_playing else "#707080")
        title = Text(f"{indicator}{track.title}", style=title_style)
        artist = Text(track.artist, style="#FFFFFF" if is_playing else "#707080")
        stars = Text(("★" * track.stars) + ("☆" * (3 - track.stars)), style="bold #FF00FF")
        return (t_id, title, artist, stars)

    def _populate_initial(self):
        """Poblado único de las tres tablas al arrancar."""
        self._repaint_table("#table-library", self.bridge.get_library())
        self._repaint_table("#table-queue", self.bridge.get_queue())

        table_dir = self.query_one("#table-directories", DataTable)
        table_dir.clear()
        for d in self.bridge.get_directories():
            table_dir.add_row(Text(d["Directorio"], style="#FFFFFF"), Text(d["Existe"], style="#00FFFF"))

    def _repaint_table(self, table_id: str, tracks):
        """Reconstruye una tabla de pistas preservando la fila del cursor."""
        table = self.query_one(table_id, DataTable)
        cursor = table.cursor_row
        table.clear()
        for t in tracks:
            table.add_row(*self._format_row(t))
        if cursor is not None and 0 <= cursor < len(table.rows):
            table.move_cursor(row=cursor)

    def update_ui(self):
        """
        Lectura PASIVA del estado: consulta al bridge y pinta.
        No toma decisiones; solo refresca lo que realmente cambió.
        """
        bridge = self.bridge
        track   = bridge.get_current_track()
        playing = bridge.is_playing()

        bar = self.query_one("#bottom-bar", PlayerBottomBar)

        # Progreso: barata y debe avanzar continuamente.
        bar.update_progress(track, bridge.get_progress())

        # Título/estado e info lateral: solo cuando cambian (evita reparsear markup).
        track_id = track.id if track else None
        if track_id != self._last_track_id or playing != self._last_playing:
            self._last_track_id = track_id
            self._last_playing  = playing
            bar.update_track(track, playing)
            self.query_one("#info-panel", InfoPanel).update_info(track)

        # Tablas: reconstruir solo si su versión cambió realmente.
        qv = bridge.get_queue_version()
        if qv != self.last_queue_version:
            self.last_queue_version = qv
            self._repaint_table("#table-queue", bridge.get_queue())

        lv = bridge.get_library_version()
        if lv != self.last_library_version:
            self.last_library_version = lv
            self._repaint_table("#table-library", bridge.get_library())

        # Sincronizar cursor de la cola con la pista en reproducción.
        if self.active_tab == "queue" and track:
            table = self.query_one("#table-queue", DataTable)
            curr_idx = bridge.get_current_index()
            if 0 <= curr_idx < len(table.rows):
                table.move_cursor(row=curr_idx)

if __name__ == "__main__":
    from core.user_manager import bootstrap_system
    user_data = bootstrap_system()
    app = MusicPlayerApp(user_data)
    app.run()