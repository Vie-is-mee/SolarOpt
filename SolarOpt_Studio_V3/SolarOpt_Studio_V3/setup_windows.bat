@echo off
cd /d %~dp0
call conda env create -f environment.yml
call conda activate solaropt-studio
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
