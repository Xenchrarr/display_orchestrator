from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any

import yaml


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "monctl" / "config.yml"


@dataclass(frozen=True)
class Monitor:
    key: str
    name: str
    bus: int
    inputs: Dict[str, str]  # label -> hex code string e.g. "0x11"


@dataclass(frozen=True)
class Preset:
    key: str
    name: str
    set: Dict[str, str]  # monitor_key -> input_label


@dataclass(frozen=True)
class AppConfig:
    monitors: Dict[str, Monitor]
    presets: Dict[str, Preset]


def _get(d: dict, key: str, default=None):
    return d[key] if key in d else default


def load_config(path: Optional[Path] = None) -> AppConfig:
    path = path or DEFAULT_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    data: Dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    monitors_raw = data.get("monitors", {})
    presets_raw = data.get("presets", {})

    monitors: Dict[str, Monitor] = {}
    for key, m in monitors_raw.items():
        monitors[key] = Monitor(
            key=key,
            name=_get(m, "name", key.capitalize()),
            bus=int(m["bus"]),
            inputs=dict(m.get("inputs", {})),
        )

    presets: Dict[str, Preset] = {}
    for key, p in presets_raw.items():
        presets[key] = Preset(
            key=key,
            name=_get(p, "name", key.replace("_", " ").title()),
            set=dict(p.get("set", {})),
        )

    return AppConfig(monitors=monitors, presets=presets)
