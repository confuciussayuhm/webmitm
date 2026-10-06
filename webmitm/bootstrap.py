"""The single mitmproxy entry script: `mitmweb -s webmitm/bootstrap.py`.

Reads the project config (WEBMITM_PROJECT, default /project), builds the addon chain, and
exposes it as the module-level `addons` list mitmproxy looks for. The chain is:

  [ <enabled addons...>, ControlAddon ]

Enabled addons come from the project config `load:` list. A name is resolved as a SHIPPED
addon (from the SHIPPED map below) or, failing that, as a project-dropped module in
<project>/addons/ (which is placed on sys.path). An addon module exposes either a
`build(config)` factory or a mitmproxy-style `addons` list.
"""

from __future__ import annotations

import importlib
import os
import sys

from webmitm.control import ControlAddon
from webmitm.project import Project

# Shipped addons, by short name. Empty for now; project-dropped modules load by filename.
SHIPPED: dict[str, str] = {}


def _load_addon(spec: str, config: dict) -> list:
    module_name = SHIPPED.get(spec, spec)
    mod = importlib.import_module(module_name)
    if hasattr(mod, "build"):
        return [mod.build(config)]
    if hasattr(mod, "addons"):
        return list(mod.addons)
    raise RuntimeError(f"addon {spec!r} ({module_name}) exposes neither build(config) nor an addons list")


def build_addons() -> list:
    project = Project(os.environ.get("WEBMITM_PROJECT", "/project"))
    project.ensure()
    cfg = project.load_config()

    # Project-dropped addons import as top-level modules.
    sys.path.insert(0, str(project.addons_dir))

    peers: list = []
    addon_configs = cfg.get("addons") or {}
    for spec in cfg.get("load", []):
        peers.extend(_load_addon(spec, addon_configs.get(spec, {})))

    return [*peers, ControlAddon(project, cfg, peers)]


addons = build_addons()
