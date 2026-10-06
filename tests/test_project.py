"""Platform sanity test: the project model (no mitmproxy/mcp needed).

Run: python tests/test_project.py
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from webmitm.project import DEFAULT_CONFIG, Project  # noqa: E402


def _check(name: str, cond: bool) -> None:
    if not cond:
        raise AssertionError(f"FAIL: {name}")
    print(f"  ok: {name}")


def main() -> int:
    d = tempfile.mkdtemp()
    p = Project(d)
    p.ensure()
    _check("project dirs created", p.confdir.exists() and p.addons_dir.exists() and p.flows_dir.exists())

    cfg = p.load_config()
    _check("default config when no file", cfg["load"] == [] and cfg["mcp"]["enabled"] is True)

    # A project file is deep-merged over the defaults.
    (p.root / "webmitm.json").write_text('{"load": ["x"], "mcp": {"port": 9000}}', encoding="utf-8")
    cfg = p.load_config()
    _check("file overrides merge over defaults", cfg["load"] == ["x"] and cfg["mcp"]["port"] == 9000 and cfg["mcp"]["enabled"] is True)

    _check("DEFAULT_CONFIG is addon-agnostic", DEFAULT_CONFIG["load"] == [] and DEFAULT_CONFIG["addons"] == {})

    print("\nALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
