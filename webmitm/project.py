"""Project model: one mounted directory that persists everything about an engagement.

A webmitm *project* is a directory (mounted into the container at /project) holding:

  <project>/
    webmitm.yaml      # which addons to load and their settings (profiles, keys policy, MCP)
    .mitmproxy/       # the mitmproxy CA + conf, so the CA is stable across container restarts
    addons/           # drop-in project-specific addons (loose .py modules)
    flows/            # saved flow files (traffic persistence)

Nothing here imports mitmproxy, so the project model is unit-testable on its own.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # noqa: BLE001 - yaml optional; JSON config still works
    yaml = None

DEFAULT_CONFIG: dict[str, Any] = {
    "load": [],  # addons to enable: shipped short names or project module names in <project>/addons/
    "addons": {},  # per-addon config, keyed by the name used in `load`
    "mcp": {"enabled": True, "port": 9876},
}


def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Project:
    def __init__(self, root: str | os.PathLike) -> None:
        self.root = Path(root)

    @property
    def confdir(self) -> Path:
        return self.root / ".mitmproxy"

    @property
    def addons_dir(self) -> Path:
        return self.root / "addons"

    @property
    def flows_dir(self) -> Path:
        return self.root / "flows"

    @property
    def flows_file(self) -> Path:
        return self.flows_dir / "flows.mitm"

    def config_path(self) -> Path | None:
        for name in ("webmitm.yaml", "webmitm.yml", "webmitm.json"):
            p = self.root / name
            if p.exists():
                return p
        return None

    def ensure(self) -> None:
        for d in (self.root, self.confdir, self.addons_dir, self.flows_dir):
            d.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> dict[str, Any]:
        path = self.config_path()
        if path is None:
            return copy.deepcopy(DEFAULT_CONFIG)
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            loaded = json.loads(text)
        elif yaml is not None:
            loaded = yaml.safe_load(text) or {}
        else:
            raise RuntimeError(f"cannot read {path.name}: PyYAML not installed and file is not .json")
        return _deep_merge(DEFAULT_CONFIG, loaded)
