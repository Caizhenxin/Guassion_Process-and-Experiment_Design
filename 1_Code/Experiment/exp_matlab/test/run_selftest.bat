@echo off
rem ============================================================
rem  run_selftest.bat -- six local self-tests, path-independent
rem  (manual v2.7 / program v4.8 / D92, 2026-10-18)
rem
rem  Usage: double-click this file, or run: test\run_selftest.bat
rem  Why it exists: the commands in the manual used absolute paths that
rem  only exist on the development machine. This file cd's to the program
rem  folder via %~dp0.. so the whole exp_matlab folder can be copied to
rem  any lab computer and still work.
rem ============================================================
cd /d "%~dp0.."
echo [selftest] program dir = %CD%
echo.

set FAIL=0

echo === 1/6 check_ask_info ===========================================
matlab -batch "addpath('test'); check_ask_info"
if errorlevel 1 set FAIL=1
echo.

echo === 2/6 check_input_validation ====================================
matlab -batch "addpath('test'); check_input_validation"
if errorlevel 1 set FAIL=1
echo.

echo === 3/6 check_data_accum =========================================
matlab -batch "addpath('test'); check_data_accum"
if errorlevel 1 set FAIL=1
echo.

echo === 4/6 runbatch_full_session(1, 99) =============================
matlab -batch "addpath('test'); runbatch_full_session(1, 99)"
if errorlevel 1 set FAIL=1
echo.

echo === 5/6 check_full_session.py ====================================
python -X utf8 test\check_full_session.py
if errorlevel 1 set FAIL=1
echo.

echo === 6/6 check_manual_d4.py =======================================
python -X utf8 test\check_manual_d4.py
if errorlevel 1 set FAIL=1
echo.

echo ============================================================
if "%FAIL%"=="1" (
    echo [selftest] SOME STEP RETURNED NON-ZERO -- do NOT start data collection.
    echo [selftest] Send a screenshot of the whole window to the PI.
    exit /b 1
)
echo [selftest] all six commands returned 0.
echo [selftest] Now check the expected last lines in the table:
echo [selftest]   40/0, 51/0, 33/0, SUMMARY pass=27 fail=0, 32/0, 40/0
echo ============================================================
exit /b 0
