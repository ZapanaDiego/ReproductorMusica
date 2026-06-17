# ==========================================
# ARCHIVO: core/input.py
# ==========================================
from core.logger import get_logger

logger = get_logger("InputManager")

class InputController:
    """
    Mapeador Exclusivo.
    Capta la tecla Textual y envía el comando abstracto al Bridge o a la UI.
    """
    def __init__(self, bridge, ui_app):
        self.bridge  = bridge
        self.ui_app  = ui_app

    def handle_key(self, key: str):
        logger.info(f"Tecla presionada por el usuario: [{key}]")

        # ── Controles de Reproducción ───────────────────────────────────────
        if key == "space":
            self.bridge.toggle_play()
        elif key == "left":
            self.bridge.prev()
        elif key == "right":
            self.bridge.next()
        elif key == "r":
            is_rand = self.bridge.toggle_random()
            self.ui_app.notify_random_mode(is_rand)

        # ── Navegación de Vistas ────────────────────────────────────────────
        elif key in ["u", "i", "o", "p"]:
            tab_map = {"u": "library", "i": "queue", "o": "directories", "p": "albums"}
            self.ui_app.switch_tab(tab_map[key])

        # ── Navegación interna de la pestaña Álbumes ────────────────────────
        elif key == "escape":
            # Retrocede de Estado 2 (canciones) a Estado 1 (lista de álbumes)
            # solo cuando la pestaña activa es álbumes. En otro contexto,
            # Textual maneja Escape de forma nativa (cierra modals, etc.).
            from ui.views import AlbumsView
            av = self.ui_app.query_one(AlbumsView)
            if self.ui_app.active_tab == "albums" and av.mode == "tracks":
                self.ui_app.albums_go_back()

        # ── Interacción general ─────────────────────────────────────────────
        elif key in ["1", "2", "3"]:
            self.ui_app.rate_current_selection(int(key))

        elif key == "enter":
            from ui.views import AlbumsView
            av = self.ui_app.query_one(AlbumsView)
            if self.ui_app.active_tab == "albums" and av.mode == "albums":
                # Estado 1 → Abre el álbum seleccionado.
                self.ui_app.open_album_at_cursor()
            else:
                # Comportamiento estándar: reproducir selección o tocar álbum.
                self.ui_app.play_current_selection()

        # ── Gestión de Álbumes ──────────────────────────────────────────────
        elif key == "a":
            self.ui_app.action_add_to_album()

        elif key in ["d", "delete"]:
            self.ui_app.action_delete()

        # ── Salida ──────────────────────────────────────────────────────────
        elif key == "q":
            logger.info("Secuencia de salida iniciada por el usuario.")
            self.ui_app.exit()