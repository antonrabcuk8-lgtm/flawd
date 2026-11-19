"""Flawd scenario runner — load YAML, mock tools, assert agent behavior."""

try:
    from flawd import __version__
except Exception:  # pragma: no cover - editable / partial installs
    __version__ = "0.2.0"
