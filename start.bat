@echo off
cd /d "%~dp0backend"
if not exist venv\Scripts\python.exe (
  echo Creating virtual environment...
  python -m venv venv
  venv\Scripts\python -m pip install -r requirements.txt
)
venv\Scripts\python app.py
