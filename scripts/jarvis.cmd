@echo off
rem Run JARVIS with the pinned interpreter (Python 3.14 through the py launcher).
rem The python on PATH may be older; this never uses it. Works from any folder.
rem Usage: scripts\jarvis.cmd <command> [arguments]     for example: scripts\jarvis.cmd doctor
setlocal
pushd "%~dp0.."
py -3.14 -m jarvis %*
set JARVIS_EXIT=%ERRORLEVEL%
popd
exit /b %JARVIS_EXIT%
