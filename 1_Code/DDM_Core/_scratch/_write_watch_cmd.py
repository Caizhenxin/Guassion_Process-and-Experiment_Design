import pathlib

REPO = pathlib.Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
body = r'''@echo off
REM Stage 8 dashboard + jobboard publisher. Runs FOREVER (poll every 60 s).
REM Started by Task Scheduler (task DSH_stage8_watch), NOT by an agent tool call:
REM every process started from a tool call dies when the session restarts or when
REM the job that spawned it is killed (2026-10-25, four times).
REM DSH_HOME must be set here: without it 1_Code/Tools/jobstatus.py falls back to
REM ~/.dsh-jobboard and the sidebar panel keeps showing a stale snapshot.
setlocal
cd /d "D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
set DSH_HOME=C:\Users\%USERNAME%\AppData\Roaming\dsh-desktop\harness
set PYTHONIOENCODING=utf-8
python -u -X utf8 1_Code\Experiment\stage8_watch.py --log "1_Code\DDM_Core\_scratch\_stage8_d123_r3.log" --every 60 --n-groups 4 --job-id stage8_d123 --relaunch 1_Code\DDM_Core\_scratch\_stage8_launch.cmd >> "1_Code\DDM_Core\_scratch\_watch4.log" 2>&1
'''
p = REPO / "1_Code" / "Experiment" / "_stage8_watch.cmd"
p.write_bytes(body.replace("\n", "\r\n").encode("ascii"))
raw = p.read_bytes()
print(f"written {len(raw)} bytes crlf={raw.count(b'\r\n')} bare_lf={raw.count(b'\n') - raw.count(b'\r\n')}")
