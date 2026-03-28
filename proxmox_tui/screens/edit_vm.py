from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static
from textual.containers import Horizontal, Vertical
from textual import work

from .. import api


class EditVMScreen(ModalScreen[dict]):
    """Modal to edit vCPU, memory and disk size of an existing VM.
    Dismisses with a dict of changed values, or an empty dict on cancel.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    EditVMScreen {
        align: center middle;
    }
    #dialog {
        border: round $accent;
        padding: 2 4;
        width: 56;
        height: auto;
        background: $surface;
    }
    .section {
        color: $accent;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }
    .row {
        layout: horizontal;
        height: auto;
    }
    .row Input {
        margin-right: 1;
    }
    .row Input:last-of-type {
        margin-right: 0;
    }
    .field {
        height: auto;
    }
    .field Label {
        margin-top: 1;
        margin-bottom: 0;
    }
    #buttons {
        layout: horizontal;
        height: auto;
        margin-top: 2;
        align: right middle;
    }
    #buttons Button {
        margin: 0 1;
    }
    #error {
        height: 1;
        margin-top: 1;
        color: $error;
    }
    """

    @staticmethod
    def _to_gb(size_str: str) -> int:
        """Convert a Proxmox size string to GB (e.g. '4296M' -> 4, '10G' -> 10, '1T' -> 1024).
        Returns 0 only if parsing truly fails."""
        s = size_str.strip()
        try:
            if s.endswith("T"):
                return max(1, int(float(s[:-1]) * 1024))
            if s.endswith("G"):
                return max(1, int(float(s[:-1])))
            if s.endswith("M"):
                # Use int() truncation, not round(), to never overshoot actual size
                return max(1, int(float(s[:-1]) / 1024))
            if s.endswith("K"):
                return 1
            # Raw bytes
            return max(1, int(int(s) / 1024 ** 3))
        except (ValueError, AttributeError):
            return 0

    def __init__(self, vmid: int, name: str) -> None:
        super().__init__()
        self._vmid = vmid
        self._name = name
        self._original: dict = {}
        self._original_disk_gb: int = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(f"[bold]Edit VM — {self._name} ({self._vmid})[/]")
            yield Static("── Hardware ──────────────────────────── optional ─", classes="section")
            with Horizontal(classes="row"):
                with Vertical(classes="field"):
                    yield Label("vCPU")
                    yield Input(placeholder="loading…", id="cores")
                with Vertical(classes="field"):
                    yield Label("Memory (MB)")
                    yield Input(placeholder="loading…", id="memory")
                with Vertical(classes="field"):
                    yield Label("Disk (GB)")
                    yield Input(placeholder="loading…", id="disk-size")
            yield Label("", id="error")
            with Horizontal(id="buttons"):
                yield Button("Apply", variant="warning", id="btn-ok")
                yield Button("Cancel", variant="default", id="btn-cancel")

    def on_mount(self) -> None:
        self._load_settings()

    @work(thread=True)
    def _load_settings(self) -> None:
        try:
            s = api.get_vm_settings(self._vmid)
            self.app.call_from_thread(self._prefill, s)
        except Exception as e:
            self.app.call_from_thread(
                self.query_one("#error", Label).update,
                f"[red]Could not load settings: {e}[/]",
            )

    def _prefill(self, s: dict) -> None:
        self._original = s
        self.query_one("#cores", Input).value = str(s["cores"])
        self.query_one("#memory", Input).value = str(s["memory"])
        if s["disk"] and s["disk_size"] != "?":
            disk_gb = self._to_gb(s["disk_size"])
            if disk_gb:
                self._original_disk_gb = disk_gb
                self.query_one("#disk-size", Input).value = str(disk_gb)
            else:
                self.query_one("#disk-size", Input).placeholder = s["disk_size"]
        else:
            self.query_one("#disk-size", Input).placeholder = "none"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss({})
        elif event.button.id == "btn-ok":
            self._submit()

    def _submit(self) -> None:
        cores_str = self.query_one("#cores", Input).value.strip()
        memory_str = self.query_one("#memory", Input).value.strip()
        disk_str = self.query_one("#disk-size", Input).value.strip()

        if cores_str and not cores_str.isdigit():
            self.query_one("#error", Label).update("vCPU must be a positive integer")
            return
        if memory_str and not memory_str.isdigit():
            self.query_one("#error", Label).update("Memory must be a positive integer (MB)")
            return
        if disk_str and not disk_str.isdigit():
            self.query_one("#error", Label).update("Disk size must be a positive integer (GB)")
            return

        result = {}
        if cores_str and int(cores_str) != self._original.get("cores"):
            result["cores"] = int(cores_str)
        if memory_str and int(memory_str) != self._original.get("memory"):
            result["memory"] = int(memory_str)
        if disk_str and int(disk_str) != self._original_disk_gb:
            result["disk_size"] = f"{disk_str}G"
        self.dismiss(result)

    def action_cancel(self) -> None:
        self.dismiss({})
