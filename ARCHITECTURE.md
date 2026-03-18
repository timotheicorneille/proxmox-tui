# Architecture

## Structure

```
proxmox_tui/
├── config.py          # Loads config.toml, exposes proxmox section
├── api.py             # All Proxmox API calls — nothing else
├── utils.py           # Shared constants and pure helpers (STATUS_STYLE, format_uptime)
├── main.py            # App entry point, global key bindings, CLI args
└── screens/
    ├── vm_list.py     # Main screen: VM table + detail panel
    ├── provision.py   # New VM form (clone from template + cloud-init)
    └── confirm_delete.py  # Delete confirmation modal
```

## Layers

**`config.py`** — reads `config.toml`, returns a plain dict. No logic, no side effects.

**`api.py`** — thin wrapper around proxmoxer. One function per operation, no UI concerns. All functions assume `init()` has been called first. The module-level `_proxmox` and `_node` are set once at startup and never change.

**`screens/`** — Textual screens. Each screen owns its own layout and CSS. They import from `api.py` but never from each other, except `vm_list.py` which imports `ProvisionScreen` and `ConfirmDeleteScreen` to push them onto the stack.

## Key decisions

**All API calls run in worker threads.**
proxmoxer is synchronous. Every call that touches the network is decorated with `@work(thread=True)` and updates the UI via `call_from_thread`. Nothing blocks the event loop.

**IP from guest agent, fallback to cloud-init.**
`api.get_vm_ip()` queries `qemu-guest-agent` for the actual runtime IP. If the agent is unavailable (VM stopped, agent not installed), `_get_ip()` in `vm_list.py` falls back to parsing the `ipconfig0` field from cloud-init config. IPs are fetched in the `load_vms` worker and stored as `_ip` on the vm dict — never fetched at render time.

**Cursor position survives refresh.**
`_update_table` saves the selected vmid before clearing the table and restores it after repopulating. If the VM disappears between refreshes it falls back to row 0.

**j/k navigation is app-level.**
`key_j` and `key_k` on the `App` class call `_move_focused()` which dispatches to `action_cursor_down/up` or `action_scroll_down/up` on whatever widget is currently focused. This makes it work everywhere without per-screen bindings. Input fields are exempt because they consume letter keys before they bubble up.

**Clone waits for task completion.**
`clone_vm()` uses `proxmoxer.tools.Tasks.blocking_status()` to wait for the Proxmox async clone task to finish before applying cloud-init config. This avoids a race condition where the VM object doesn't exist yet when config is applied.

## Stack

- **Textual** — TUI framework, CSS-like layout, reactive widgets
- **proxmoxer** — Python wrapper around the Proxmox REST API
- **uv** — dependency management and running
