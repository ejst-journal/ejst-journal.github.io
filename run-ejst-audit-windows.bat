@echo off
cd /d "%~dp0"
python tools\ejst_scholar_audit.py
if errorlevel 1 echo Audit found errors. Open scholar-audit-report.md
if not errorlevel 1 echo Audit completed. Open scholar-audit-report.md
pause
