# ==========================================
# ARCHIVO: ui/modals.py
# ==========================================
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal
from textual.widgets import Label, Input, Button, OptionList


class AlbumInputModal(ModalScreen[str]):
    """
    Ventana flotante para ingresar el nombre de un álbum.

    Retorna el nombre escrito (str) al cerrarse con Confirm,
    o retorna "" si el usuario cancela (Escape / botón Cancelar).

    El resultado se recibe en el callback del push_screen() del App.
    """

    def __init__(self, existing_albums: list[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.existing_albums = existing_albums or []

    DEFAULT_CSS = """
    AlbumInputModal {
        align: center middle;
    }
    AlbumInputModal > Vertical {
        width: 52;
        height: auto;
        border: double #8A2BE2;
        background: #0d0d1a;
        padding: 1 2;
    }
    AlbumInputModal #modal-title {
        text-align: center;
        color: #8A2BE2;
        text-style: bold;
        margin-bottom: 1;
    }
    AlbumInputModal #modal-hint {
        color: #707080;
        margin-bottom: 1;
    }
    AlbumInputModal Input {
        border: solid #8A2BE2;
        background: #1a1a2e;
        color: #FFFFFF;
    }
    AlbumInputModal Input:focus {
        border: solid #00FFFF;
    }
    AlbumInputModal #btn-row {
        margin-top: 1;
        align: center middle;
        height: auto;
    }
    AlbumInputModal Button {
        margin: 0 1;
    }
    AlbumInputModal #btn-confirm {
        background: #2a0050;
        border: solid #8A2BE2;
        color: #FFFFFF;
    }
    AlbumInputModal #btn-cancel {
        background: #200010;
        border: solid #FF00FF;
        color: #FFFFFF;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("♦  AÑADIR A ÁLBUM  ♦", id="modal-title", markup=False)
            if self.existing_albums:
                yield Label("Selecciona uno existente:", id="modal-hint-2")
                yield OptionList(*self.existing_albums, id="album-options")
            yield Label("O escribe un nombre nuevo:", id="modal-hint")
            yield Input(placeholder="Ej: Favoritos de Rock…", id="album-input")
            with Horizontal(id="btn-row"):
                yield Button("✔ Confirmar", id="btn-confirm", variant="primary")
                yield Button("✘ Cancelar",  id="btn-cancel",  variant="error")

    def on_mount(self) -> None:
        if self.existing_albums:
            self.query_one("#album-options", OptionList).focus()
        else:
            self.query_one("#album-input", Input).focus()

    # ── Respuesta a botones ───────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm":
            self._submit()
        else:
            self.dismiss("")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Rellena el input con el álbum seleccionado."""
        self.query_one("#album-input", Input).value = str(event.option.prompt)
        self.query_one("#album-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Permite confirmar con Enter directamente desde el campo."""
        event.stop()  # Detiene el bubbling del evento Enter
        self._submit()

    def _submit(self) -> None:
        value = self.query_one("#album-input", Input).value.strip()
        self.dismiss(value)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss("")
        # Detener la propagación del evento Key ("enter", "d", "a", etc.) hacia el App principal
        event.stop()
