#!/usr/bin/env bash
# Convert a Burp Suite CA export into the shared mitmproxy CA (ca/mitmproxy-ca.pem),
# so webmitm signs with the SAME CA your devices already trust - no new cert installs.
#
# In Burp: Proxy -> Proxy settings -> Import / export CA certificate, export BOTH:
#   * "Certificate in DER format"   -> e.g. burp-ca.der
#   * "Private key in DER format"   -> e.g. burp-ca-key.der   (this is the PKCS#8 private key)
#
# Then:
#   tools/burp-ca-to-mitm.sh burp-ca-key.der burp-ca.der
#
# Produces ca/mitmproxy-ca.pem (private key first, then certificate - the layout mitmproxy wants).
# Every project started with a mounted ./ca will reuse it, so you install the Burp CA on your
# phone/browser ONCE and it covers every webmitm project, app and device.
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <burp-private-key.der> <burp-cert.der>" >&2
  exit 2
fi

KEY_DER="$1"
CERT_DER="$2"
OUT_DIR="$(cd "$(dirname "$0")/.." && pwd)/ca"
OUT="$OUT_DIR/mitmproxy-ca.pem"

mkdir -p "$OUT_DIR"
tmp_key="$(mktemp)"
tmp_cert="$(mktemp)"
trap 'rm -f "$tmp_key" "$tmp_cert"' EXIT

# Burp exports PKCS#8 DER for the key and DER for the cert; convert both to PEM.
openssl pkcs8 -inform DER -nocrypt -in "$KEY_DER" -out "$tmp_key" 2>/dev/null \
  || openssl rsa -inform DER -in "$KEY_DER" -out "$tmp_key"
openssl x509 -inform DER -in "$CERT_DER" -out "$tmp_cert"

# mitmproxy expects: private key first, then certificate, in one file.
cat "$tmp_key" "$tmp_cert" > "$OUT"
chmod 600 "$OUT"

echo "wrote $OUT"
echo "CA subject / usage:"
openssl x509 -in "$tmp_cert" -noout -subject -ext keyUsage,basicConstraints || true
echo
echo "Start any project and it will reuse this CA:"
echo "  WEBMITM_PROJECT_NAME=example docker compose up"
