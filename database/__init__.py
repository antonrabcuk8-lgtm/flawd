"""Flawd scenario catalog package (YAML cards shipped as package data)."""

from pathlib import Path

CATALOG_DIR = Path(__file__).resolve().parent

__all__ = ["CATALOG_DIR"]
