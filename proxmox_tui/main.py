from __future__ import annotations

import sys
from pathlib import Path

from textual.app import App, ComposeResult

from . import api
from .config import get_proxmox_config


class ProxmoxTUI(App):
    CSS = """
    Screen {
        background: $surface;
    }
    """

    TITLE = "proxmox-tui"

    def on_mount(self) -> None:
        from .screens.vm_list import VMListScreen
        self.push_screen(VMListScreen())

    def _move_focused(self, direction: str) -> None:
        focused = self.focused
        if focused is None:
            return
        action = f"action_cursor_{direction}" if hasattr(focused, f"action_cursor_{direction}") else f"action_scroll_{direction}"
        if hasattr(focused, action):
            getattr(focused, action)()

    def key_j(self) -> None:
        self._move_focused("down")

    def key_k(self) -> None:
        self._move_focused("up")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Proxmox TUI")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.toml")
    args = parser.parse_args()

    try:
        cfg = get_proxmox_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        api.init(cfg)
    except Exception as e:
        print(f"Failed to connect to Proxmox: {e}", file=sys.stderr)
        sys.exit(1)

    app = ProxmoxTUI()
    app.run()


if __name__ == "__main__":
    main()
