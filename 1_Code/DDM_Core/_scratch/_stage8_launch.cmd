@echo off
REM Stage 8 rerun (D123 criteria + D125 per-model checkpoints).
REM Launched detached via WMI Win32_Process.Create, so it is NOT a child of the
REM agent session. That matters: every process started from a tool call dies when
REM the session/repl restarts (2026-10-25, three times, ~4 h of fitting lost).
REM This file MUST use CRLF: cmd.exe misparses LF-only batch files and exits
REM instantly with no output.
setlocal
cd /d "D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
set PYTHONIOENCODING=utf-8
set LOG=1_Code\DDM_Core\_scratch\_stage8_d123_r3.log
set /a TRIES=0
:loop
set /a TRIES+=1
if %TRIES% GTR 8 goto giveup
echo. >> "%LOG%"
echo ===== attempt %TRIES% at %DATE% %TIME% ===== >> "%LOG%"
python -u -X utf8 1_Code\DDM_Core\stage8_run.py --data "2_Data\Real_Data\New_Design\_stage8_in" --out "2_Data\Real_Data\New_Design\_pipeline\stage8_d123" --n-em 3 --n-draws 12 --n-x 21 --n-ppc 1 --hyper-method analytic --loo-level trial --allow-large --resume >> "%LOG%" 2>&1
if %ERRORLEVEL%==0 goto done
echo [launcher] attempt %TRIES% failed with %ERRORLEVEL%, sleeping 120s >> "%LOG%"
timeout /t 120 /nobreak > NUL
goto loop
:done
echo [launcher] finished OK at %DATE% %TIME% >> "%LOG%"
exit /b 0
:giveup
echo [launcher] gave up after %TRIES% attempts >> "%LOG%"
exit /b 1
