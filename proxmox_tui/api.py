from __future__ import annotations

from proxmoxer import ProxmoxAPI
from proxmoxer.tools import Tasks


_proxmox: ProxmoxAPI | None = None
_node: str = "pve"


def init(cfg: dict) -> None:
    global _proxmox, _node
    _proxmox = ProxmoxAPI(
        cfg["host"],
        user=cfg["user"],
        token_name=cfg["token_name"],
        token_value=cfg["token_value"],
        verify_ssl=cfg.get("verify_ssl", False),
    )
    _node = cfg.get("node", "pve")


def _api() -> ProxmoxAPI:
    if _proxmox is None:
        raise RuntimeError("API not initialised — call init() first")
    return _proxmox


# ---------------------------------------------------------------------------
# VM list
# ---------------------------------------------------------------------------

def list_vms() -> list[dict]:
    vms = _api().nodes(_node).qemu.get()
    return sorted(vms, key=lambda v: int(v["vmid"]))


def list_templates() -> list[dict]:
    return [v for v in list_vms() if v.get("template") == 1]


# ---------------------------------------------------------------------------
# VM detail
# ---------------------------------------------------------------------------

def get_vm_ip(vmid: int) -> str:
    """Return the runtime IP from the guest agent, or empty string if unavailable."""
    try:
        ifaces = _api().nodes(_node).qemu(vmid).agent("network-get-interfaces").get()
        for iface in ifaces.get("result", []):
            if iface.get("name") == "lo":
                continue
            for addr in iface.get("ip-addresses", []):
                if addr.get("ip-address-type") == "ipv4":
                    return addr["ip-address"]
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def start_vm(vmid: int) -> str:
    return _api().nodes(_node).qemu(vmid).status.start.post()


def shutdown_vm(vmid: int) -> str:
    return _api().nodes(_node).qemu(vmid).status.shutdown.post()


def reboot_vm(vmid: int) -> str:
    return _api().nodes(_node).qemu(vmid).status.reboot.post()


def delete_vm(vmid: int) -> str:
    return _api().nodes(_node).qemu(vmid).delete()


# ---------------------------------------------------------------------------
# Provisioning
# ---------------------------------------------------------------------------

def next_vmid() -> int:
    return int(_api().cluster.nextid.get())


_DISK_KEYS = ("scsi0", "virtio0", "sata0", "ide0", "scsi1", "virtio1", "sata1", "ide1")


def _primary_disk(vmid: int) -> str | None:
    """Return the first disk device name found in the VM config, or None."""
    cfg = _api().nodes(_node).qemu(vmid).config.get()
    for key in _DISK_KEYS:
        if key in cfg:
            return key
    return None


def get_vm_settings(vmid: int) -> dict:
    """Return current cores, memory (MB), primary disk name and size."""
    cfg = _api().nodes(_node).qemu(vmid).config.get()
    disk_name = None
    disk_size = "?"
    for key in _DISK_KEYS:
        if key not in cfg:
            continue
        for part in str(cfg[key]).split(","):
            if part.startswith("size="):
                disk_size = part[5:]
        disk_name = key
        break
    return {
        "cores": cfg.get("cores", 1),
        "memory": cfg.get("memory", 512),
        "disk": disk_name,
        "disk_size": disk_size,
    }


def update_vm(vmid: int, cores: int = 0, memory: int = 0, disk_size: str = "") -> None:
    """Update cores, memory and/or disk size of an existing VM."""
    params: dict = {}
    if cores:
        params["cores"] = cores
    if memory:
        params["memory"] = memory
    if params:
        _api().nodes(_node).qemu(vmid).config.put(**params)
    if disk_size:
        disk = _primary_disk(vmid)
        if disk is None:
            raise RuntimeError(f"No disk found on VM {vmid}")
        _api().nodes(_node).qemu(vmid).resize.put(disk=disk, size=disk_size)


def clone_vm(
    template_id: int,
    new_id: int,
    name: str,
    ip: str,
    gateway: str,
    dns: str = "",
    disk_size: str = "",
    cores: int = 0,
    memory: int = 0,
    start: bool = True,
) -> None:
    upid = _api().nodes(_node).qemu(template_id).clone.post(newid=new_id, name=name, full=1)
    Tasks.blocking_status(_api(), upid)

    if disk_size:
        disk = _primary_disk(new_id)
        if disk:
            _api().nodes(_node).qemu(new_id).resize.put(disk=disk, size=disk_size)

    hw: dict = {}
    if cores:
        hw["cores"] = cores
    if memory:
        hw["memory"] = memory
    if hw:
        _api().nodes(_node).qemu(new_id).config.put(**hw)

    ciconfig: dict = {"ipconfig0": f"ip={ip},gw={gateway}"}
    if dns:
        ciconfig["nameserver"] = dns
    _api().nodes(_node).qemu(new_id).config.put(**ciconfig)

    if start:
        _api().nodes(_node).qemu(new_id).status.start.post()
