# ==========================================
# ARCHIVO: ui_views.py
# ==========================================
from rich.text import Text
from textual.containers import Container
from textual.widgets import DataTable

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
            path_txt = Text(d["Directorio"], style="#FFFFFF")
            exists_txt = Text(d["Existe"], style="bold #00FFFF" if d["Existe"] == "SÍ" else "bold #FF00FF")
            table.add_row(path_txt, exists_txt)