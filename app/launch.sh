#!/bin/zsh
set -eu

APP_ROOT="$(cd "$(dirname "$0")" && pwd)"
SERVER="$APP_ROOT/server.py"
LOG="$APP_ROOT/server.log"
URL="http://127.0.0.1:11435/"

if ! /usr/bin/curl --silent --fail http://127.0.0.1:11435/api/status >/dev/null 2>&1; then
  /usr/bin/nohup /usr/bin/python3 "$SERVER" >>"$LOG" 2>&1 &
  for _ in {1..30}; do
    /usr/bin/curl --silent --fail http://127.0.0.1:11435/api/status >/dev/null 2>&1 && break
    /bin/sleep 0.2
  done
fi

if [ -d "/Applications/Google Chrome.app" ]; then
  open -n -a "Google Chrome" --args "--app=$URL"
elif [ -d "/Applications/Brave Browser.app" ]; then
  open -n -a "Brave Browser" --args "--app=$URL"
elif [ -d "/Applications/Microsoft Edge.app" ]; then
  open -n -a "Microsoft Edge" --args "--app=$URL"
else
  /usr/bin/open "$URL"
fi
