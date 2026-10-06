#!/bin/sh
# webmitm container entrypoint: run mitmweb with the platform bootstrap against the mounted
# /project volume. The CA and saved flows live under /project so they persist across runs.
#
# Shared CA: if a shared CA is mounted at /ca/mitmproxy-ca.pem (e.g. your Burp CA, so devices
# that already trust Burp need NO new cert), seed it into this project's confdir on first run.
# A project that already has its own CA keeps it; delete the project's .mitmproxy to re-seed.
set -e

CONFDIR=/project/.mitmproxy
mkdir -p "$CONFDIR" /project/flows

if [ -f /ca/mitmproxy-ca.pem ] && [ ! -f "$CONFDIR/mitmproxy-ca.pem" ]; then
  cp /ca/mitmproxy-ca.pem "$CONFDIR/mitmproxy-ca.pem"
  echo "[webmitm] seeded shared CA from /ca into $CONFDIR"
fi

WEB_ARGS=""
if [ -n "$WEBMITM_WEB_PASSWORD" ]; then
  WEB_ARGS="--set web_password=$WEBMITM_WEB_PASSWORD"
fi

exec mitmweb \
  --mode "${WEBMITM_MODE:-regular}" \
  --listen-host 0.0.0.0 --listen-port 8080 \
  --web-host 0.0.0.0 --web-port 8081 \
  --set confdir="$CONFDIR" \
  --set save_stream_file=/project/flows/flows.mitm \
  $WEB_ARGS \
  -s /opt/webmitm/webmitm/bootstrap.py
