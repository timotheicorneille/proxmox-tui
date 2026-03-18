# proxmox-tui

![demo](demo.gif)

proxmox-tui is a terminal interface to manage your Proxmox server. List VMs, start, stop, reboot, clone from a template or delete, all from your keyboard without touching the web UI.

Talks to the Proxmox REST API over LAN or Tailscale via [proxmoxer](https://github.com/proxmoxer/proxmoxer).

## Setup

### 1. API token

In Proxmox UI → Datacenter → API Tokens → Add:
- User: `root@pam`
- Token name: `tui`
- Uncheck "Privilege Separation" (or grant the needed permissions)

### 2. Config

```bash
cp config.toml.example config.toml
$EDITOR config.toml
```

```toml
[proxmox]
host = "192.168.1.100"    # LAN IP or Tailscale IP
user = "root@pam"
token_name = "tui"
token_value = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
verify_ssl = false
node = "pve"
```

`config.toml` is gitignored — never commit it.

### 3. Install

```bash
uv sync
```

### 4. Run

```bash
uv run proxmox-tui
# or with a custom config path:
uv run proxmox-tui --config /path/to/config.toml
```

## Keybindings

### VM list

| Key     | Action                        |
|---------|-------------------------------|
| `j`/`k` | Move up / down                |
| `s`     | Start selected VM             |
| `S`     | Stop selected VM (graceful)   |
| `r`     | Reboot selected VM            |
| `d`     | Delete selected VM (stopped only) |
| `n`     | New VM (clone from template)  |
| `R`     | Refresh list                  |
| `q`     | Quit                          |

### Provision form

| Key      | Action   |
|----------|----------|
| `Escape` | Cancel   |

### Delete confirmation

| Key          | Action  |
|--------------|---------|
| `y`          | Confirm |
| `n` / `Escape` | Cancel  |

The detail panel updates as you move between VMs. The list refreshes automatically every 5 seconds. The IP shown is the live runtime IP from the qemu guest agent when the VM is running, falling back to the cloud-init config when stopped.
