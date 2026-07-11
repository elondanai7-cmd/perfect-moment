#!/usr/bin/env bash
# Stops whatever start.sh launched (web app server + cloudflared tunnel).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDFILE="$ROOT/webapp/.pids"

if [ ! -f "$PIDFILE" ]; then
  echo "Nothing to stop (no $PIDFILE -- was it started with start.sh?)."
  exit 0
fi

while read -r pid; do
  [ -z "$pid" ] && continue
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null && echo "Stopped PID $pid"
  fi
done < "$PIDFILE"

rm -f "$PIDFILE"
echo "Done. Link is no longer live."
