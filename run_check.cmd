@echo off
REM Inpol Monitor - Daily case check runner
REM This script is invoked by Windows Task Scheduler
@set JSON_LOGGING_ENABLED=true

cd /d "%~dp0"

REM Ensure logs directory exists
if not exist logs mkdir logs

REM Run the orchestrator and append output to scheduler log
python -m src.orchestrator >> logs\scheduler.log 2>&1
