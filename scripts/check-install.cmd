@echo off
rem Is this machine ready to run JARVIS? Reads only; creates and changes nothing.
rem 1. Python 3.14 is available through the py launcher.  2. jarvis doctor passes.
setlocal
py -3.14 -c "import sys; print('python', sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 14) else 1)"
if errorlevel 1 (
  echo check-install: FAILED - Python 3.14 is not available through "py -3.14".
  echo See docs\beta\BETA_OPERATIONS.md, section "Clean install".
  exit /b 1
)
call "%~dp0jarvis.cmd" doctor
exit /b %ERRORLEVEL%
