from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, Static
from textual.containers import Horizontal, Vertical
from textual import work

from .. import api
from ..utils import STATUS_STYLE, format_uptime
from .confirm_delete import ConfirmDeleteScreen
from .edit_vm import EditVMScreen
from .provision import ProvisionScreen


def _get_ip(vm: dict) -> str:
    if "_ip" in vm:
        return vm["_ip"]
    for key, val in vm.items():
        if key.startswith("ipconfig"):
            for part in str(val).split(","):
                if part.startswith("ip="):
                    return part[3:]
    return "—"


class DetailPanel(Static):
    DEFAULT_CSS = """
    DetailPanel {
        border: round $accent;
        padding: 1 2;
        width: 1fr;
        height: 100%;
    }
    """

    def show_vm(self, vm: dict) -> None:
        vmid = vm.get("vmid", "—")
        name = vm.get("name", "—")
        status = vm.get("status", "—")
        cpus = vm.get("cpus", vm.get("cores", "—"))
        maxmem_mb = int(vm.get("maxmem", 0)) // 1024 // 1024
        mem_mb = int(vm.get("mem", 0)) // 1024 // 1024
        mem_pct = int(mem_mb * 100 / maxmem_mb) if maxmem_mb else 0
        cpu_pct = int(float(vm.get("cpu", 0)) * 100)

        self.update(
            f"[bold]Detail: {name}[/]\n\n"
            f"ID     : {vmid}\n"
            f"Status : {STATUS_STYLE.get(status, status)}\n"
            f"CPU    : {cpus} cores ({cpu_pct}%)\n"
            f"RAM    : {maxmem_mb} MB ({mem_pct}%)\n"
            f"IP     : {_get_ip(vm)}\n"
            f"Uptime : {format_uptime(int(vm.get('uptime', 0)))}\n"
        )


class VMListScreen(Screen):
    BINDINGS = [
        Binding("s", "start_vm", "Start"),
        Binding("S", "stop_vm", "Stop"),
        Binding("r", "reboot_vm", "Reboot"),
        Binding("d", "delete_vm", "Delete"),
        Binding("n", "new_vm", "New VM"),
        Binding("e", "edit_vm", "Edit VM"),
        Binding("R", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    DEFAULT_CSS = """
    VMListScreen {
        layout: vertical;
    }
    #main-row {
        layout: horizontal;
        height: 1fr;
    }
    #vm-panel {
        border: round $accent;
        width: 2fr;
        height: 100%;
        padding: 0;
    }
    #vm-panel DataTable {
        height: 1fr;
    }
    #status-bar {
        height: 1;
        padding: 0 1;
        background: $surface;
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._vms: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-row"):
            with Vertical(id="vm-panel"):
                yield DataTable(id="vm-table", cursor_type="row", zebra_stripes=True)
            yield DetailPanel(id="detail-panel")
        yield Label("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#vm-table", DataTable).add_columns("VMID", "Name", "Status", "CPU", "RAM")
        self.load_vms()
        self.set_interval(5, self.load_vms)

    @work(thread=True)
    def load_vms(self) -> None:
        try:
            vms = api.list_vms()
            for vm in vms:
                if vm.get("status") == "running":
                    ip = api.get_vm_ip(int(vm["vmid"]))
                    if ip:
                        vm["_ip"] = ip
            self.app.call_from_thread(self._update_table, vms)
        except Exception as e:
            self.app.call_from_thread(self._set_status, f"[red]Error: {e}[/]")

    def _update_table(self, vms: list[dict]) -> None:
        table = self.query_one("#vm-table", DataTable)

        selected_vmid = None
        if self._vms and table.row_count > 0:
            idx = table.cursor_row
            if idx < len(self._vms):
                selected_vmid = int(self._vms[idx]["vmid"])

        self._vms = vms
        table.clear()
        for vm in vms:
            status = vm.get("status", "—")
            cpu_pct = int(float(vm.get("cpu", 0)) * 100)
            maxmem_mb = int(vm.get("maxmem", 0)) // 1024 // 1024
            table.add_row(
                str(vm.get("vmid", "")),
                vm.get("name", ""),
                STATUS_STYLE.get(status, status),
                f"{cpu_pct}%",
                f"{maxmem_mb} MB",
                key=str(vm.get("vmid")),
            )

        if vms:
            restored = next(
                (i for i, v in enumerate(vms) if int(v["vmid"]) == selected_vmid), 0
            ) if selected_vmid is not None else 0
            table.move_cursor(row=restored)
            self._show_detail(vms[restored])

        self._set_status(f"[dim]{len(vms)} VMs loaded[/]")

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-bar", Label).update(msg)

    def _show_detail(self, vm: dict) -> None:
        self.query_one("#detail-panel", DetailPanel).show_vm(vm)

    def _selected_vm(self) -> dict | None:
        table = self.query_one("#vm-table", DataTable)
        idx = table.cursor_row
        if table.row_count == 0 or idx >= len(self._vms):
            return None
        return self._vms[idx]

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value:
            vmid = int(event.row_key.value)
            vm = next((v for v in self._vms if int(v["vmid"]) == vmid), None)
            if vm:
                self._show_detail(vm)

    @work(thread=True)
    def action_start_vm(self) -> None:
        vm = self._selected_vm()
        if vm is None:
            return
        try:
            api.start_vm(int(vm["vmid"]))
            self.app.call_from_thread(self._set_status, f"[green]Starting {vm['name']}…[/]")
        except Exception as e:
            self.app.call_from_thread(self._set_status, f"[red]Error: {e}[/]")
        self.app.call_from_thread(self.load_vms)

    @work(thread=True)
    def action_stop_vm(self) -> None:
        vm = self._selected_vm()
        if vm is None:
            return
        try:
            api.shutdown_vm(int(vm["vmid"]))
            self.app.call_from_thread(self._set_status, f"[yellow]Stopping {vm['name']}…[/]")
        except Exception as e:
            self.app.call_from_thread(self._set_status, f"[red]Error: {e}[/]")
        self.app.call_from_thread(self.load_vms)

    @work(thread=True)
    def action_reboot_vm(self) -> None:
        vm = self._selected_vm()
        if vm is None:
            return
        try:
            api.reboot_vm(int(vm["vmid"]))
            self.app.call_from_thread(self._set_status, f"[yellow]Rebooting {vm['name']}…[/]")
        except Exception as e:
            self.app.call_from_thread(self._set_status, f"[red]Error: {e}[/]")
        self.app.call_from_thread(self.load_vms)

    def action_delete_vm(self) -> None:
        vm = self._selected_vm()
        if vm is None:
            return
        if vm.get("status") != "stopped":
            self._set_status("[red]VM must be stopped before deleting[/]")
            return

        def on_result(confirmed: bool) -> None:
            if confirmed:
                self._do_delete(int(vm["vmid"]))

        self.app.push_screen(ConfirmDeleteScreen(int(vm["vmid"]), vm.get("name", "")), on_result)

    @work(thread=True)
    def _do_delete(self, vmid: int) -> None:
        try:
            api.delete_vm(vmid)
            self.app.call_from_thread(self._set_status, f"[green]VM {vmid} deleted[/]")
        except Exception as e:
            self.app.call_from_thread(self._set_status, f"[red]Error: {e}[/]")
        self.app.call_from_thread(self.load_vms)

    def action_edit_vm(self) -> None:
        vm = self._selected_vm()
        if vm is None:
            return

        def on_result(changes: dict) -> None:
            if changes:
                self._do_edit(int(vm["vmid"]), changes)

        self.app.push_screen(EditVMScreen(int(vm["vmid"]), vm.get("name", "")), on_result)

    @work(thread=True)
    def _do_edit(self, vmid: int, changes: dict) -> None:
        try:
            api.update_vm(
                vmid,
                cores=changes.get("cores", 0),
                memory=changes.get("memory", 0),
                disk_size=changes.get("disk_size", ""),
            )
            self.app.call_from_thread(self._set_status, "[green]VM updated[/]")
        except Exception as e:
            self.app.call_from_thread(self._set_status, f"[red]Error: {e}[/]")
        self.app.call_from_thread(self.load_vms)

    def action_new_vm(self) -> None:
        self.app.push_screen(ProvisionScreen())

    def action_refresh(self) -> None:
        self.load_vms()

    def action_quit(self) -> None:
        self.app.exit()
