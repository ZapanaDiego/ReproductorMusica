# ==========================================
# ARCHIVO: core_input.py
# ==========================================
from core.logger import get_logger

logger = get_logger("InputManager")

class InputController:
    """
    Mapeador Exclusivo. 
    Capta la tecla Textual y envía el comando abstracto al Bridge o a la UI.
    """
    def __init__(self, bridge, ui_app):
        self.bridge = bridge
        self.ui_app = ui_app

    def handle_key(self, key: str):
        logger.info(f"Tecla presionada por el usuario: [{key}]")
        
        # --- Controles de Reproducción ---
        if key == "space":
            self.bridge.toggle_play()
        elif key == "left":
            self.bridge.prev()
        elif key == "right":
            self.bridge.next()
        elif key == "r":
            is_rand = self.bridge.toggle_random()
            self.ui_app.notify_random_mode(is_rand)
            
        # --- Navegación de Vistas ---
        elif key in ["u", "i", "o"]:
            tab_map = {"u": "library", "i": "queue", "o": "directories"}
            self.ui_app.switch_tab(tab_map[key])
            
        # --- Interacción ---
        elif key in ["1", "2", "3"]:
            self.ui_app.rate_current_selection(int(key))
        elif key == "enter":
            self.ui_app.play_current_selection()
        elif key == "q":
            logger.info("Secuencia de salida iniciada por el usuario.")
            self.ui_app.exit()