@echo off
cd /d "%~dp0backend"
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
set PYTHONPATH=.
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
