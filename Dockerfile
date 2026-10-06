# webmitm platform image: mitmproxy + web UI (mitmweb) + MCP control + addon host.
#
# Build:  docker build -t webmitm:latest .
# Run:    see docker-compose.yml, or:
#   docker run --rm -it \
#     -p 127.0.0.1:8080:8080 \        # proxy listener (point your browser here)
#     -p 127.0.0.1:8081:8081 \        # mitmweb UI
#     -p 127.0.0.1:9876:9876 \        # MCP control (if enabled in the project config)
#     -e WEBMITM_WEB_PASSWORD=webmitm \
#     -v "$PWD/projects/example:/project" \
#     webmitm:latest
#
# The official mitmproxy image already bundles mitmproxy; we add our package,
# PyYAML (project config) and mcp (control server).
FROM mitmproxy/mitmproxy:latest

USER root
WORKDIR /opt/webmitm

# mcp pinned to v1: v2 renamed FastMCP -> MCPServer and changed the tool API.
RUN pip install --no-cache-dir "PyYAML>=6" "mcp>=1.2,<2"

COPY webmitm/ ./webmitm/
COPY docker/entrypoint.sh /usr/local/bin/webmitm-entrypoint
RUN chmod +x /usr/local/bin/webmitm-entrypoint

ENV PYTHONPATH=/opt/webmitm \
    WEBMITM_PROJECT=/project \
    WEBMITM_MODE=regular

EXPOSE 8080 8081 9876
ENTRYPOINT ["/usr/local/bin/webmitm-entrypoint"]
