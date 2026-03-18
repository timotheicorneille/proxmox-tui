from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Label
from textual.containers import Horizontal, Vertical


class ConfirmDeleteScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("escape,n", "cancel", "No", show=False),
        Binding("y", "confirm", "Yes", show=False),
    ]

    DEFAULT_CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }
    #dialog {
        border: round $error;
        padding: 2 4;
        width: 50;
        height: auto;
        background: $surface;
    }
    #buttons {
        layout: horizontal;
        height: auto;
        margin-top: 2;
        align: center middle;
    }
    #buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, vmid: int, name: str) -> None:
        super().__init__()
        self._vmid = vmid
        self._name = name

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"[bold red]Delete VM {self._vmid} — {self._name}?[/]\n\nThis cannot be undone.")
            with Horizontal(id="buttons"):
                yield Button("Yes, delete", variant="error", id="btn-yes")
                yield Button("Cancel", variant="default", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-yes")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
