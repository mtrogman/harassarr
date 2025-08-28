from __future__ import annotations
import yaml
from typing import Any, Dict
from .config_model import validate_config


def getConfig(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def checkConfig(path: str) -> None:
    """
    Fail fast if core parts of config.yml are malformed.
    Keeps compatibility with your existing callsites.
    """
    raw = getConfig(path)
    validate_config(raw)  # raises with a clear error if invalid
