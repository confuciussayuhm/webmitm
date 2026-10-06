"""Platform control: the single MCP server, and the addon that starts it.

webmitm runs ONE MCP server for the whole proxy. The ControlAddon starts it once mitmproxy
is running, registers platform-level tools (list addons, read/set mitmproxy options), and
then lets every peer addon contribute its own tools via `register_mcp_tools(mcp)` - so any
project addon's tools appear on the same endpoint as the platform tools.

Option writes are marshalled onto mitmproxy's event loop (the MCP server runs in its own
thread), which is the one cross-thread hazard worth handling carefully. Raw flow access is
intentionally left to mitmweb's own HTTP API (/flows, /flows/dump) rather than duplicated here.
"""

from __future__ import annotations

import concurrent.futures
from typing import Any

from mitmproxy import ctx


class ControlAddon:
    name = "control"

    def __init__(self, project: Any, config: dict[str, Any], peers: list[Any]) -> None:
        self.project = project
        self.config = config
        self.peers = peers
        self._thread = None

    def running(self) -> None:
        mcp_cfg = self.config.get("mcp") or {}
        port = int(mcp_cfg.get("port", 0))
        host = str(mcp_cfg.get("host", "127.0.0.1"))
        if not mcp_cfg.get("enabled") or not port or self._thread is not None:
            return
        try:
            self._thread = start_mcp(self.peers, ctx.master, host, port)
            ctx.log.info(f"[webmitm] MCP control server on {host}:{port} (/mcp)")
        except Exception as e:  # noqa: BLE001 - MCP must never take the proxy down
            ctx.log.warn(f"[webmitm] MCP server failed to start: {e}")


def _set_option_threadsafe(master: Any, name: str, value: Any, timeout: float = 5.0) -> None:
    fut: concurrent.futures.Future = concurrent.futures.Future()

    def _apply() -> None:
        try:
            master.options.update(**{name: value})
            fut.set_result(True)
        except Exception as e:  # noqa: BLE001
            fut.set_exception(e)

    master.event_loop.call_soon_threadsafe(_apply)
    fut.result(timeout=timeout)


def build_mcp(peers: list[Any], master: Any):  # noqa: ANN201 - FastMCP
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("webmitm")

    @mcp.tool()
    def webmitm_list_addons() -> list[str]:
        """Names of the addons currently loaded in this proxy."""
        return [getattr(p, "name", type(p).__name__) for p in peers]

    @mcp.tool()
    def webmitm_get_option(name: str) -> dict:
        """Read one mitmproxy option's current value."""
        return {"name": name, "value": getattr(master.options, name, None)}

    @mcp.tool()
    def webmitm_set_option(name: str, value: Any) -> dict:
        """Set one mitmproxy option live (e.g. mode, allow_hosts, modify_body, intercept)."""
        _set_option_threadsafe(master, name, value)
        return {"name": name, "value": getattr(master.options, name, None)}

    # Let each peer addon contribute its own tools onto this one server.
    for peer in peers:
        hook = getattr(peer, "register_mcp_tools", None)
        if callable(hook):
            hook(mcp)

    return mcp


def start_mcp(peers: list[Any], master: Any, host: str, port: int):  # noqa: ANN201 - Thread
    import threading

    mcp = build_mcp(peers, master)
    mcp.settings.host = host
    mcp.settings.port = port

    def _run() -> None:
        mcp.run(transport="streamable-http")

    thread = threading.Thread(target=_run, name="webmitm-mcp", daemon=True)
    thread.start()
    return thread
