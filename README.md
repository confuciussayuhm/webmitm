# webmitm

A Dockerised **mitmproxy platform** — web-viewable traffic (mitmweb), one MCP/API control
surface, per-project persistence, and a drop-in **addon** mechanism. A simpler, scriptable,
many-at-once proxy base for match/replace, upstream proxying, traffic capture, remote control,
and running many concurrent instances.

## What it gives you

- **mitmweb UI** — view/inspect/replay traffic in the browser; native intercept (pause, edit, resume).
- **Per-project persistence** — the CA, saved flows, settings and addons live in a mounted
  project dir, so the CA is stable across restarts and each engagement is self-contained.
- **One MCP control server** — set any mitmproxy option live (e.g. `modify_body`/`modify_headers`
  for match/replace, `mode` for upstream proxy, `allow_hosts`/`ignore_hosts` for scope, `intercept`),
  list addons, and whatever tools your addons add. mitmweb's own HTTP API covers raw flow access.
- **Addons** — drop a Python mitmproxy addon into a project and load it from config.

## Architecture

```
webmitm/                     the PLATFORM
  bootstrap.py               the single `mitmweb -s` entry: reads the project, builds the addon chain
  project.py                 project dir model (CA, flows, config, addons)
  control.py                 the one MCP server + the addon that starts it; collects each addon's tools
  addons/                    shipped addons (none bundled yet)

<project>/                   a mounted PROJECT (persists everything about one engagement)
  webmitm.yaml               which addons to load + their settings + MCP config
  .mitmproxy/                the CA + conf (stable across restarts)
  addons/                    drop-in project-specific addons
  flows/                     saved traffic
```

## Run it (Docker)

```bash
docker build -t webmitm:latest .
WEBMITM_PROJECT_NAME=example docker compose up      # mounts projects/example -> /project
```

Host ports default to **8090 / 8091 / 9878** (chosen to avoid clashing with Burp on 8080/8081
and a Burp MCP server on 9876). Then:

- Browser proxy -> `127.0.0.1:8090`; install the CA from `http://mitm.it` while proxied. With a
  shared CA mounted (below), you install it **once ever** and it covers every project, app and
  device — nothing new to add to your phone per engagement.
- mitmweb UI -> `http://127.0.0.1:8091` (password = `WEBMITM_WEB_PASSWORD`, default `webmitm`).
- MCP control -> `http://127.0.0.1:9878/mcp` (when enabled in the project config).

Override ports with `WEBMITM_PROXY_PORT` / `WEBMITM_UI_PORT` / `WEBMITM_MCP_PORT`. All three bind
to loopback on purpose — proxy, UI and MCP are a control plane. For a target on your own machine,
use `host.docker.internal` instead of `localhost` (the proxy runs in the container).

A new engagement is just a new dir: `mkdir -p projects/<name>` (optionally add a `webmitm.yaml`),
then `WEBMITM_PROJECT_NAME=<name> docker compose up`.

## Shared CA — reuse your Burp CA, install once ever

A CA per project is wrong for real use (you would re-add CAs to the same phone for every app you
test). Instead, mount **one** CA at `./ca/mitmproxy-ca.pem` and every project reuses it. Make it
your **Burp CA** and devices that already trust Burp need **no new cert at all**:

```bash
# In Burp: Proxy -> Proxy settings -> Import/export CA certificate, export BOTH:
#   "Certificate in DER format"  and  "Private key in DER format"
tools/burp-ca-to-mitm.sh burp-ca-key.der burp-ca.der      # writes ca/mitmproxy-ca.pem
WEBMITM_PROJECT_NAME=example docker compose up
```

`docker-compose.yml` mounts `./ca:/ca:ro`; the entrypoint seeds the project's confdir from it on
first run (a project that already has its own CA keeps it — delete its `.mitmproxy/` to re-seed).
mitmproxy needs the CA **private key**, not just the public `.der` everyone installs, because it
signs interception certs with it (see mitmproxy's certificate docs). If `./ca` is empty, each
project just generates its own CA as before.

## Match/replace and upstream proxy

No addon needed — these are mitmproxy options you set once in the project (or live over MCP
`webmitm_set_option`):

- **Match/replace:** `modify_body` / `modify_headers` (regex, scoped by a flow filter).
- **Upstream proxy:** run with `--mode upstream:http://host:port` (or set the `mode` option live;
  changing `mode` restarts listeners on the fly).
- **mTLS client cert:** `client_certs` (PKCS#12 dir). **Scope:** `allow_hosts` / `ignore_hosts`.

## Writing an addon

An addon is a standard [mitmproxy addon](https://docs.mitmproxy.org/stable/addons/overview/)
module placed in `<project>/addons/`, exposing either a `build(config)` factory or a module-level
`addons = [...]` list, and optionally `register_mcp_tools(mcp)` to add tools to the shared MCP
server. Enable it in `webmitm.yaml`:

```yaml
load:
  - my_addon          # -> <project>/addons/my_addon.py
addons:
  my_addon:
    some_option: true
```

```python
# <project>/addons/my_addon.py
from mitmproxy import http

class MyAddon:
    name = "my_addon"
    def __init__(self, config): self.config = config
    def request(self, flow: http.HTTPFlow) -> None:
        flow.request.headers["X-Example"] = "1"
    def register_mcp_tools(self, mcp) -> None:      # optional
        @mcp.tool()
        def my_addon_ping() -> str:
            return "pong"

def build(config=None):
    return MyAddon(config or {})
```

## Tests

```bash
python tests/test_project.py     # platform project-model sanity (no mitmproxy/mcp needed)
```

## Status

- Platform (bootstrap, project model, addon loader, MCP control, Docker): **done**, loads clean
  under mitmproxy in the container.
- No addons bundled.
- External orchestrator integration (per-run sidecar): not yet (separate change).
