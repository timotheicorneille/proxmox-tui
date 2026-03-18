import tomllib
from pathlib import Path

_DEFAULT_PATHS = [
    Path("config.toml"),
    Path.home() / ".config" / "proxmox-tui" / "config.toml",
]


def load_config(path: Path | None = None) -> dict:
    candidates = [path] if path is not None else _DEFAULT_PATHS

    for candidate in candidates:
        if candidate.exists():
            with open(candidate, "rb") as f:
                return tomllib.load(f)

    raise FileNotFoundError(
        "config.toml not found. Copy config.toml.example to config.toml and fill in your credentials."
    )


def get_proxmox_config(path: Path | None = None) -> dict:
    return load_config(path)["proxmox"]
