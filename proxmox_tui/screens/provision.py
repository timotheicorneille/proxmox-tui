from __future__ import annotations

import time

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static
from textual.containers import Horizontal, Vertical
from textual import work

from .. import api


class ProvisionScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ProvisionScreen {
        align: center middle;
    }
    #form {
        border: round $accent;
        padding: 2 4;
        width: 64;
        height: auto;
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
    #status {
        height: 1;
        margin-top: 1;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="form"):
            yield Static("[bold]Provision new VM[/]")

            yield Static("── Identity ──────────────────────────── required ─", classes="section")
            yield Label("Template *")
            yield Select([], id="template-select", prompt="Loading templates…")
            with Horizontal(classes="row"):
                with Vertical(classes="field"):
                    yield Label("VM ID *")
                    yield Input(placeholder="e.g. 104", id="vmid")
                with Vertical(classes="field"):
                    yield Label("Name *")
                    yield Input(placeholder="e.g. vm-foo", id="name")

            yield Static("── Network ───────────────────────────── required ─", classes="section")
            with Horizontal(classes="row"):
                with Vertical(classes="field"):
                    yield Label("IP / CIDR *")
                    yield Input(placeholder="192.168.1.104/24", id="ip")
                with Vertical(classes="field"):
                    yield Label("Gateway *")
                    yield Input(placeholder="192.168.1.1", id="gateway")
            yield Label("DNS")
            yield Input(placeholder="1.1.1.1  (optional)", id="dns")

            yield Static("── Hardware ──────────────────────────── optional ─", classes="section")
            with Horizontal(classes="row"):
                with Vertical(classes="field"):
                    yield Label("vCPU")
                    yield Input(placeholder="e.g. 2", id="cores")
                with Vertical(classes="field"):
                    yield Label("Memory (MB)")
                    yield Input(placeholder="e.g. 2048", id="memory")
                with Vertical(classes="field"):
                    yield Label("Disk (GB)")
                    yield Input(placeholder="e.g. 20", id="disk-size")

            with Horizontal(id="buttons"):
                yield Button("Create", variant="success", id="btn-create")
                yield Button("Cancel", variant="default", id="btn-cancel")
            yield Label("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._load_templates()
        self._load_next_id()

    @work(thread=True)
    def _load_templates(self) -> None:
        try:
            templates = api.list_templates()
            options = [(f"{t['vmid']} — {t.get('name', '?')}", str(t["vmid"])) for t in templates]
            self.app.call_from_thread(self.query_one("#template-select", Select).set_options, options)
        except Exception as e:
            self.app.call_from_thread(self._set_status, f"[red]Could not load templates: {e}[/]")

    @work(thread=True)
    def _load_next_id(self) -> None:
        try:
            vmid = api.next_vmid()
            self.app.call_from_thread(self._set_vmid, vmid)
        except Exception:
            pass

    def _set_vmid(self, vmid: int) -> None:
        self.query_one("#vmid", Input).value = str(vmid)

    def _set_status(self, msg: str) -> None:
        self.query_one("#status", Label).update(msg)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-create":
            self._submit()

    def _submit(self) -> None:
        sel = self.query_one("#template-select", Select)
        vmid_str = self.query_one("#vmid", Input).value.strip()
        name = self.query_one("#name", Input).value.strip()
        ip = self.query_one("#ip", Input).value.strip()
        gateway = self.query_one("#gateway", Input).value.strip()
        dns = self.query_one("#dns", Input).value.strip()
        cores_str = self.query_one("#cores", Input).value.strip()
        memory_str = self.query_one("#memory", Input).value.strip()
        disk_size_str = self.query_one("#disk-size", Input).value.strip()

        if sel.value is Select.BLANK:
            self._set_status("[red]Select a template[/]")
            return
        if not vmid_str.isdigit():
            self._set_status("[red]VM ID must be a number[/]")
            return
        if not name:
            self._set_status("[red]Name is required[/]")
            return
        if not ip:
            self._set_status("[red]IP is required[/]")
            return
        if not gateway:
            self._set_status("[red]Gateway is required[/]")
            return
        if cores_str and not cores_str.isdigit():
            self._set_status("[red]vCPU must be a number[/]")
            return
        if memory_str and not memory_str.isdigit():
            self._set_status("[red]Memory must be a number (MB)[/]")
            return
        if disk_size_str and not disk_size_str.isdigit():
            self._set_status("[red]Disk size must be a number (GB)[/]")
            return

        disk_size = f"{disk_size_str}G" if disk_size_str else ""
        self._do_clone(
            int(sel.value), int(vmid_str), name, ip, gateway, dns,
            disk_size=disk_size,
            cores=int(cores_str) if cores_str else 0,
            memory=int(memory_str) if memory_str else 0,
        )

    @work(thread=True)
    def _do_clone(
        self,
        template_id: int,
        new_id: int,
        name: str,
        ip: str,
        gateway: str,
        dns: str,
        disk_size: str = "",
        cores: int = 0,
        memory: int = 0,
    ) -> None:
        self.app.call_from_thread(self._set_status, "[yellow]Cloning…[/]")
        try:
            api.clone_vm(
                template_id, new_id, name, ip, gateway, dns,
                disk_size=disk_size, cores=cores, memory=memory, start=True,
            )
            self.app.call_from_thread(self._set_status, f"[green]VM {name} ({new_id}) created and starting![/]")
            time.sleep(1.5)
            self.app.call_from_thread(self.action_cancel)
        except Exception as e:
            self.app.call_from_thread(self._set_status, f"[red]Error: {e}[/]")

    def action_cancel(self) -> None:
        self.app.pop_screen()
