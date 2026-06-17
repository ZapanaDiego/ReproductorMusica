# ==========================================
# ARCHIVO: ui/views.py
# ==========================================
from rich.text import Text
from textual.containers import Container
from textual.widgets import DataTable, Label


class LibraryView(Container):
    """Pestaña de Biblioteca que muestra todas las canciones de library.json."""
    def compose(self):
        yield DataTable(id="table-library", cursor_type="row")

    def populate(self, library_tracks, format_row_fn) -> None:
        table = self.query_one("#table-library", DataTable)
        table.clear()
        for track in library_tracks:
            table.add_row(*format_row_fn(track))


class RandomQueueView(Container):
    """Pestaña de Cola Aleatoria ponderada físicamente por estrellas."""
    def compose(self):
        yield DataTable(id="table-queue", cursor_type="row")

    def populate(self, queue_tracks, format_row_fn) -> None:
        table = self.query_one("#table-queue", DataTable)
        table.clear()
        for track in queue_tracks:
            table.add_row(*format_row_fn(track))


class DirectoriesView(Container):
    """Pestaña de Directorios y Carpetas del sistema."""
    def compose(self):
        yield DataTable(id="table-directories", cursor_type="row")

    def populate(self, directories) -> None:
        table = self.query_one("#table-directories", DataTable)
        table.clear()
        for d in directories:
            path_txt   = Text(d["Directorio"], style="#FFFFFF")
            exists_txt = Text(
                d["Existe"],
                style="bold #00FFFF" if d["Existe"] == "SÍ" else "bold #FF00FF"
            )
            table.add_row(path_txt, exists_txt)


class AlbumsView(Container):
    """
    Pestaña de Álbumes Personalizados — Máquina de 2 estados.

    Estado "albums": Lista todos los álbumes del usuario (resumen).
    Estado "tracks": Muestra las canciones dentro del álbum seleccionado.

    La misma DataTable sirve para ambos estados; las columnas se reconstruyen
    en cada transición de modo mediante clear() + add_columns().
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Estado interno: "albums" o "tracks"
        self._mode: str = "albums"
        # Nombre del álbum abierto en modo "tracks"
        self._current_album: str | None = None

    def compose(self):
        yield Label(
            "[bold #8A2BE2]  ♦  MIS ÁLBUMES[/]",
            id="albums-breadcrumb", markup=True
        )
        yield DataTable(id="table-albums", cursor_type="row")

    # ── Getters de estado ─────────────────────────────────────────────────

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def current_album(self) -> str | None:
        return self._current_album

    # ── Estado 1: Lista de álbumes ────────────────────────────────────────

    def populate(self, albums_summary: list[dict]) -> None:
        """Modo "albums": renderiza el resumen de todos los álbumes en batch."""
        self._mode = "albums"
        self._current_album = None

        self.query_one("#albums-breadcrumb", Label).update(
            "[bold #8A2BE2]  ♦  MIS ÁLBUMES[/]"
        )

        table = self.query_one("#table-albums", DataTable)
        table.clear(columns=True)       # limpia filas Y columnas para re-definirlas
        table.add_columns("Álbum", "Canciones")

        # Batch completo: un solo evento de invalidación al compositor de Textual.
        rows = [
            (Text(album["name"], style="bold #00FFFF"),
             Text(str(album["count"]), style="#FF00FF"))
            for album in albums_summary
        ]
        if rows:
            table.add_rows(rows)

    # ── Estado 2: Canciones dentro de un álbum ────────────────────────────

    def open_album(self, album_name: str, tracks: list, playing_track_id: int | None = None) -> None:
        """Modo "tracks": renderiza las canciones del álbum seleccionado."""
        self._mode = "tracks"
        self._current_album = album_name

        self.query_one("#albums-breadcrumb", Label).update(
            f"[bold #8A2BE2]  ♦  MIS ÁLBUMES[/] [#707080]›[/] "
            f"[bold #00FFFF]{album_name}[/]  "
            f"[#707080](Esc = volver)[/]"
        )

        table = self.query_one("#table-albums", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Título", "Artista")

        rows = []
        for t in tracks:
            if t.id == playing_track_id:
                t_id   = Text(f"{t.id:03d}", style="bold #00FF00")
                title  = Text(f"▶ 🎵 {t.title}", style="bold #00FF00")
                artist = Text(t.artist, style="bold #00FF00")
            else:
                t_id   = Text(f"{t.id:03d}", style="#707080")
                title  = Text(f"  {t.title}", style="bold #FFFFFF")
                artist = Text(t.artist, style="#707080")
            rows.append((t_id, title, artist))

        if rows:
            table.add_rows(rows)

    # ── Utilidades ────────────────────────────────────────────────────────

    def get_selected_album_name(self) -> str | None:
        """En modo 'albums', retorna el nombre del álbum en la fila del cursor."""
        table = self.query_one("#table-albums", DataTable)
        if table.cursor_row is None:
            return None
        row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key
        cell = table.get_cell(row_key, table.ordered_columns[0].key)
        # cell es un Rich Text; extraemos el texto plano.
        return str(cell) if cell is not None else None

    def get_selected_track_id(self) -> int | None:
        """En modo 'tracks', retorna el track_id de la fila seleccionada."""
        table = self.query_one("#table-albums", DataTable)
        if table.cursor_row is None:
            return None
        row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key
        cell = table.get_cell(row_key, table.ordered_columns[0].key)
        try:
            return int(str(cell))
        except (ValueError, TypeError):
            return None