#!/bin/sh
# Arranca el receiver local y un tunel publico temporal con Cloudflare.
# Copia la URL https://...-trycloudflare.com que aparece y ponla en el secreto UPLOAD_URL.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TOKEN=$(cat "$ROOT/token.txt")
cd "$ROOT"
RECEIVER_TOKEN="$TOKEN" python3 receiver.py "$ROOT" "$TOKEN" > receiver.log 2>&1 &
RECEIVER_PID=$!
echo "$RECEIVER_PID" > receiver.pid
trap 'kill "$RECEIVER_PID" 2>/dev/null || true' EXIT INT TERM
echo "[tunnel] receiver en http://127.0.0.1:8080 (pid $RECEIVER_PID)"
echo "[tunnel] esperando URL publica..."
"$HOME/.local/bin/cloudflared" tunnel --url http://127.0.0.1:8080
