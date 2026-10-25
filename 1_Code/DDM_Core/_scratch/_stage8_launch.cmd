@echo off
REM Stage 8 rerun (D123 criteria). Launched by 1_Code/Experiment/stage8_watch.py
REM when the run process disappears (uses --resume).
REM NOTE: this file MUST use CRLF line endings. cmd.exe misparses LF-only
REM batch files: the process exits instantly with no output (lost 5 auto-restarts
REM on 2026-10-25 because of exactly that).
cd /d "D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
set PYTHONIOENCODING=utf-8
python -u -X utf8 1_Code\DDM_Core\stage8_run.py --data "2_Data\Real_Data\New_Design\_stage8_in" --out "2_Data\Real_Data\New_Design\_pipeline\stage8_d123" --n-em 3 --n-draws 12 --n-x 21 --n-ppc 1 --hyper-method analytic --loo-level trial --allow-large --resume >> "1_Code\DDM_Core\_scratch\_stage8_d123_r2.log" 2>&1
