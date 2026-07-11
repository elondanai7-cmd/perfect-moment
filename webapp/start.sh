#!/usr/bin/env bash
# One-command pilot launch: starts the web app + a free cloudflared quick
# tunnel, waits for both, and prints the public link. Replaces the old
# multi-step manual dance (start server, wait, start tunnel separately, grep
# the log for the URL).
#
# Usage: bash webapp/start.sh
# Stop:  bash webapp/stop.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEBAPP="$ROOT/webapp"
PIDFILE="$WEBAPP/.pids"
SERVER_LOG="$WEBAPP/server.log"
TUNNEL_LOG="$WEBAPP/tunnel.log"

CLOUDFLARED="/c/Program Files (x86)/cloudflared/cloudflared.exe"
if [ ! -f "$CLOUDFLARED" ]; then
  CLOUDFLARED="/c/Program Files/cloudflared/cloudflared.exe"
fi
if [ ! -f "$CLOUDFLARED" ]; then
  echo "cloudflared not found. Install it first: winget install --id Cloudflare.cloudflared -e" >&2
  exit 1
fi

if [ -f "$PIDFILE" ]; then
  echo "Already running (found $PIDFILE). Run stop.sh first if you want a fresh start." >&2
  exit 1
fi

: > "$SERVER_LOG"
: > "$TUNNEL_LOG"

echo "Starting web app server..."
PYTHONUNBUFFERED=1 python -u "$WEBAPP/app.py" > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!

for i in $(seq 1 60); do
  if grep -qE "Running on local URL" "$SERVER_LOG" 2>/dev/null; then
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Server process died. Check $SERVER_LOG" >&2
    cat "$SERVER_LOG" >&2
    exit 1
  fi
  sleep 1
done

LOCAL_URL=$(grep -oE "http://127\.0\.0\.1:[0-9]+" "$SERVER_LOG" | head -1)
if [ -z "$LOCAL_URL" ]; then
  echo "Server didn't report a local URL within 60s. Check $SERVER_LOG" >&2
  kill "$SERVER_PID" 2>/dev/null || true
  exit 1
fi
echo "Server up at $LOCAL_URL"

echo "Starting cloudflared tunnel..."
"$CLOUDFLARED" tunnel --url "$LOCAL_URL" > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

PUBLIC_URL=""
for i in $(seq 1 30); do
  PUBLIC_URL=$(grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" "$TUNNEL_LOG" 2>/dev/null | head -1)
  if [ -n "$PUBLIC_URL" ]; then
    break
  fi
  if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
    echo "Tunnel process died. Check $TUNNEL_LOG" >&2
    cat "$TUNNEL_LOG" >&2
    kill "$SERVER_PID" 2>/dev/null || true
    exit 1
  fi
  sleep 1
done

if [ -z "$PUBLIC_URL" ]; then
  echo "Tunnel didn't report a public URL within 30s. Check $TUNNEL_LOG" >&2
  kill "$SERVER_PID" "$TUNNEL_PID" 2>/dev/null || true
  exit 1
fi

echo "$SERVER_PID" > "$PIDFILE"
echo "$TUNNEL_PID" >> "$PIDFILE"

echo ""
echo "================================================================"
echo "  Perfect Moment is live: $PUBLIC_URL"
echo "  (this link changes every time you restart -- share it fresh)"
echo "  Run 'bash webapp/stop.sh' when done."
echo "================================================================"
