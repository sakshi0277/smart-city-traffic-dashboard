"""Loads config.yaml so every module reads settings from one place."""

from functools import lru_cache
from pathlib import Path

import yaml

# This file is at <project>/src/config.py, so the project root is one level up.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = PROJECT_ROOT / "config.yaml"


@lru_cache(maxsize=1)
def load_config() -> dict:
    """Read config.yaml once and keep the result in memory."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"config.yaml not found at: {CONFIG_FILE}")
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_path(key: str) -> Path:
    """Return an absolute folder path, e.g. get_path('raw')."""
    cfg = load_config()
    return PROJECT_ROOT / cfg["paths"][key]
