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
from ui.views import LibraryView, RandomQueueView, DirectoriesView, AlbumsView
from ui.player import PlayerBottomBar
from ui.info_panel import InfoPanel
from ui.modals import AlbumInputModal


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
                        yield Label("  [U] BIBLIOTECA  ",     id="tab-library",     classes="tab-label active")
                        yield Label("  [I] COLA ALEATORIA  ", id="tab-queue",        classes="tab-label")
                        yield Label("  [O] DIRECTORIOS  ",    id="tab-directories",  classes="tab-label")
                        yield Label("  [P] ÁLBUMES  ",        id="tab-albums",       classes="tab-label")

                    with ContentSwitcher(initial="library", id="views-switcher"):
                        yield LibraryView(id="library")
                        yield RandomQueueView(id="queue")
                        yield DirectoriesView(id="directories")
                        yield AlbumsView(id="albums")

                # PANEL 2: Info y Atajos
                with Vertical(id="panel-right", classes="glass-panel"):
                    yield InfoPanel(id="info-panel")

            # PANEL 3: Visualizador y Reproductor
            with Vertical(id="panel-bottom", classes="glass-panel"):
                yield CavaVisualizer()
                yield PlayerBottomBar(id="bottom-bar")

    def on_mount(self) -> None:
        self.query_one("#table-library",     DataTable).add_columns("ID", "Música", "Artista", "Calificación")
        self.query_one("#table-queue",       DataTable).add_columns("ID", "Música", "Artista", "Calificación")
        self.query_one("#table-directories", DataTable).add_columns("Directorio Escaneado", "Estado del Sistema")

        # Poblado inicial único. A partir de aquí las tablas solo se
        # reconstruyen cuando cambia su versión (cola/biblioteca).
        self._populate_initial()
        self.last_queue_version   = self.bridge.get_queue_version()
        self.last_library_version = self.bridge.get_library_version()

        # Nombre de usuario en el InfoPanel
        self.query_one("#info-panel", InfoPanel).set_username(
            self.bridge.get_current_username()
        )

        self.set_interval(0.1, self.update_ui)
        # self.bridge.play() # Eliminado auto-play para arrancar en silencio

    def on_key(self, event) -> None:
        """Delega ABSOLUTAMENTE TODO el control de teclado al InputController."""
        self.input_manager.handle_key(event.key.lower())

    # ── COMANDOS EXPUESTOS PARA EL INPUT MANAGER ─────────────────────────

    def switch_tab(self, tab_name: str) -> None:
        self.active_tab = tab_name
        for t in ["library", "queue", "directories", "albums"]:
            self.query_one(f"#tab-{t}", Label).remove_class("active")

        self.query_one(f"#tab-{tab_name}", Label).add_class("active")
        self.query_one("#views-switcher", ContentSwitcher).current = tab_name

        if tab_name == "albums":
            # Carga batch de álbumes al entrar en la pestaña.
            summary = self.bridge.get_albums_summary()
            self.query_one(AlbumsView).populate(summary)
            self.query_one("#table-albums", DataTable).focus()
        else:
            self.query_one(f"#table-{tab_name}", DataTable).focus()

    def notify_random_mode(self, is_rand: bool) -> None:
        # Solo cambia la etiqueta visual; el repintado de la cola lo dispara
        # el cambio de queue_version detectado en update_ui.
        mode_label = "  [I] COLA ALEATORIA (RND)  " if is_rand else "  [I] COLA ALEATORIA  "
        self.query_one("#tab-queue", Label).update(mode_label)

    def play_current_selection(self) -> None:
        """
        Enter en pestaña albums-modo-tracks: inyecta el álbum en la cola y
        reproduce. En cualquier otra pestaña, comportamiento estándar.
        """
        albums_view = self.query_one(AlbumsView)
        if self.active_tab == "albums" and albums_view.mode == "tracks":
            album_name = albums_view.current_album
            if album_name:
                tracks = self.bridge.get_album_tracks(album_name)
                if tracks:
                    # Inyectar el álbum como nueva cola y reproducir.
                    self.bridge.backend.queue = tracks
                    self.bridge.backend.queue_version += 1
                    self.bridge.backend.current_index = 0
                    self.bridge.backend.progress = 0.0
                    self.bridge.play()
            return

        # Comportamiento estándar para library/queue/directories
        if self.active_tab != "albums":
            table = self.query_one(f"#table-{self.active_tab}", DataTable)
            if table.cursor_row is not None:
                self.bridge.play_selection(self.active_tab, table.cursor_row)
        else:
            # En albums modo "albums", Enter abre el álbum (delega a open_album_at_cursor).
            self.open_album_at_cursor()

    def open_album_at_cursor(self) -> None:
        """Abre el álbum seleccionado en el cursor (Estado 1 → Estado 2)."""
        albums_view = self.query_one(AlbumsView)
        album_name = albums_view.get_selected_album_name()
        if album_name:
            tracks = self.bridge.get_album_tracks(album_name)
            curr = self.bridge.get_current_track()
            albums_view.open_album(album_name, tracks, curr.id if curr else None)
            self.query_one("#table-albums", DataTable).focus()

    def albums_go_back(self) -> None:
        """Regresa de Estado 2 (canciones) a Estado 1 (lista de álbumes)."""
        albums_view = self.query_one(AlbumsView)
        summary = self.bridge.get_albums_summary()
        albums_view.populate(summary)
        self.query_one("#table-albums", DataTable).focus()

    def rate_current_selection(self, stars: int) -> None:
        if self.active_tab not in ("library", "queue"):
            return
        table = self.query_one(f"#table-{self.active_tab}", DataTable)
        if table.cursor_row is not None:
            self.bridge.rate_selection(self.active_tab, table.cursor_row, stars)

    # ── ACCIÓN: Añadir canción a álbum (tecla A) ─────────────────────────

    def action_add_to_album(self) -> None:
        """
        Abre el modal para escribir el nombre del álbum.
        Crea el álbum si no existe, luego añade la pista seleccionada.
        """
        # Obtener la pista activa en la vista actual
        track_id = self._get_selected_track_id()
        if track_id is None:
            self.notify("Selecciona una canción primero.", severity="warning")
            return

        def _on_modal_close(album_name: str) -> None:
            if not album_name:
                return
            # Crear el álbum si no existe (crea + ignora si ya existe)
            self.bridge.create_album(album_name)
            # Añadir la pista
            added = self.bridge.add_track_to_album(album_name, track_id)
            if added:
                self.notify(f"Canción añadida a «{album_name}».", severity="information")
            else:
                self.notify(f"La canción ya estaba en «{album_name}».", severity="warning")
            # Si estamos viendo el álbum afectado, refrescar
            av = self.query_one(AlbumsView)
            if self.active_tab == "albums" and av.mode == "tracks" and av.current_album == album_name:
                tracks = self.bridge.get_album_tracks(album_name)
                curr = self.bridge.get_current_track()
                av.open_album(album_name, tracks, curr.id if curr else None)

        summary = self.bridge.get_albums_summary()
        existing_names = [a["name"] for a in summary]
        self.push_screen(AlbumInputModal(existing_albums=existing_names), _on_modal_close)

    # ── ACCIÓN: Eliminar (tecla D / delete) ──────────────────────────────

    def action_delete(self) -> None:
        """
        Modo "albums" → elimina el álbum seleccionado.
        Modo "tracks" → elimina la canción seleccionada del álbum actual.
        """
        albums_view = self.query_one(AlbumsView)

        if self.active_tab != "albums":
            return

        if albums_view.mode == "albums":
            album_name = albums_view.get_selected_album_name()
            if album_name:
                removed = self.bridge.remove_album(album_name)
                if removed:
                    self.notify(f"Álbum «{album_name}» eliminado.", severity="information")
                    summary = self.bridge.get_albums_summary()
                    albums_view.populate(summary)

        elif albums_view.mode == "tracks":
            track_id = albums_view.get_selected_track_id()
            album_name = albums_view.current_album
            if track_id and album_name:
                removed = self.bridge.remove_track_from_album(album_name, track_id)
                if removed:
                    self.notify(f"Canción eliminada de «{album_name}».", severity="information")
                    tracks = self.bridge.get_album_tracks(album_name)
                    albums_view.open_album(album_name, tracks)

    def _get_selected_track_id(self) -> int | None:
        """Retorna el track_id de la fila seleccionada en la vista activa."""
        albums_view = self.query_one(AlbumsView)

        if self.active_tab == "albums" and albums_view.mode == "tracks":
            return albums_view.get_selected_track_id()

        if self.active_tab in ("library", "queue"):
            table = self.query_one(f"#table-{self.active_tab}", DataTable)
            row = table.cursor_row
            if row is not None:
                # La primera columna es el ID (Text formateado "001").
                row_key = table.coordinate_to_cell_key((row, 0)).row_key
                cell = table.get_cell(row_key, table.ordered_columns[0].key)
                try:
                    return int(str(cell))
                except (ValueError, TypeError):
                    pass
        return None

    # ── RENDERIZADO Y ACTUALIZACIÓN UI ───────────────────────────────────

    def _format_row(self, track, is_playing=False):
        if is_playing:
            t_id   = Text(f"{track.id:03d}", style="bold #00FF00")
            title  = Text(f"▶ 🎵 {track.title}", style="bold #00FF00")
            artist = Text(track.artist, style="bold #00FF00")
            stars  = Text(("★" * track.stars) + ("☆" * (3 - track.stars)), style="bold #FF00FF")
        else:
            t_id   = Text(f"{track.id:03d}", style="#707080")
            title  = Text(f"  {track.title}", style="bold #FFFFFF")
            artist = Text(track.artist, style="#707080")
            stars  = Text(("★" * track.stars) + ("☆" * (3 - track.stars)), style="bold #FF00FF")
        return (t_id, title, artist, stars)

    def _populate_initial(self):
        """Poblado único de las tres tablas al arrancar."""
        curr = self.bridge.get_current_track()
        t_id = curr.id if curr else None
        
        self._repaint_table("#table-library", self.bridge.get_library(), playing_track_id=t_id)
        self._repaint_table("#table-queue",   self.bridge.get_queue(), playing_track_id=t_id)

        table_dir = self.query_one("#table-directories", DataTable)
        table_dir.clear()
        for d in self.bridge.get_directories():
            table_dir.add_row(
                Text(d["Directorio"], style="#FFFFFF"),
                Text(d["Existe"], style="#00FFFF")
            )

    def _repaint_table(self, table_id: str, tracks, playing_track_id=None):
        """Reconstruye una tabla de pistas preservando la fila del cursor."""
        table  = self.query_one(table_id, DataTable)
        cursor = table.cursor_row
        table.clear()
        for t in tracks:
            table.add_row(*self._format_row(t, is_playing=(t.id == playing_track_id)))
        if cursor is not None and 0 <= cursor < len(table.rows):
            table.move_cursor(row=cursor)

    def update_ui(self):
        """
        Lectura PASIVA del estado: consulta al bridge y pinta.
        No toma decisiones; solo refresca lo que realmente cambió.
        """
        bridge  = self.bridge
        track   = bridge.get_current_track()
        playing = bridge.is_playing()

        bar = self.query_one("#bottom-bar", PlayerBottomBar)

        # Progreso: barata y debe avanzar continuamente.
        bar.update_progress(track, bridge.get_progress())

        # Título/estado e info lateral: solo cuando cambian (evita reparsear markup).
        track_id = track.id if track else None
        
        # BUG 1 CORREGIDO: Medir si cambió ANTES de asignar el nuevo ID
        track_changed = (track_id != self._last_track_id)
        state_changed = (playing != self._last_playing)
        
        if track_changed or state_changed:
            self._last_track_id = track_id
            self._last_playing  = playing
            bar.update_track(track, playing)
            self.query_one("#info-panel", InfoPanel).update_info(track)

        # Tablas: reconstruir si su versión cambió o cambió la pista activa
        force_repaint = track_changed
            
        qv = bridge.get_queue_version()
        if qv != self.last_queue_version or force_repaint:
            self.last_queue_version = qv
            self._repaint_table("#table-queue", bridge.get_queue(), playing_track_id=track_id)

        lv = bridge.get_library_version()
        if lv != self.last_library_version or force_repaint:
            self.last_library_version = lv
            self._repaint_table("#table-library", bridge.get_library(), playing_track_id=track_id)

        # Refrescar vista de álbumes si cambió la pista y estamos viéndola.
        if force_repaint:
            av = self.query_one(AlbumsView)
            if av.mode == "tracks" and av.current_album:
                tracks_album = bridge.get_album_tracks(av.current_album)
                av.open_album(av.current_album, tracks_album, track_id)

        # Sincronizar cursor de la tabla inteligentemente cuando la pista cambia.
        if force_repaint and track_id is not None:
            table_id = f"#table-{self.active_tab}"
            if self.active_tab in ["library", "queue"] or (self.active_tab == "albums" and self.query_one(AlbumsView).mode == "tracks"):
                table = self.query_one(table_id, DataTable)
                # Buscar fila con el track_id para fijar el cursor ahí
                try:
                    for idx in range(len(table.rows)):
                        row_key = table.coordinate_to_cell_key((idx, 0)).row_key
                        cell = table.get_cell(row_key, table.ordered_columns[0].key)
                        if int(str(cell)) == track_id:
                            table.move_cursor(row=idx)
                            break
                except Exception:
                    pass


if __name__ == "__main__":
    from core.user_manager import bootstrap_system
    user_data = bootstrap_system()
    app = MusicPlayerApp(user_data)
    app.run()