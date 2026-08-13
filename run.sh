#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ -x "venv/bin/uvicorn" ]; then
  exec venv/bin/uvicorn app:app --reload --host 127.0.0.1 --port 8787
fi

if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

exec uvicorn app:app --reload --host 127.0.0.1 --port 8787
