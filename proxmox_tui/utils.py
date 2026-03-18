from __future__ import annotations

STATUS_STYLE = {
    "running": "[bold green]running[/]",
    "stopped": "[bold red]stopped[/]",
    "paused": "[bold yellow]paused[/]",
}


def format_uptime(seconds: int) -> str:
    if not seconds:
        return "—"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s"
