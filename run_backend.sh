#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/backend"
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
PYTHONPATH=. uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
