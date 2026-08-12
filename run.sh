#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ -x "venv/bin/streamlit" ]; then
  exec venv/bin/streamlit run app.py
fi

if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

exec streamlit run app.py
