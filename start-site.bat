@echo off
start "" python "%~dp0serve_site.py"
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8765/
