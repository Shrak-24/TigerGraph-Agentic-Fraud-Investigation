@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul && set "PY=py" || set "PY=python"
%PY% --version || (echo Python 3.10+ is required. & pause & exit /b 1)
if not exist .venv %PY% -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m streamlit run app.py
pause
