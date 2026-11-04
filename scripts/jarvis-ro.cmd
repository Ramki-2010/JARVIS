@echo off
rem Read-only JARVIS: only look-but-do-not-change commands run (see scripts\jarvis_ro.py).
rem Uses the pinned Python 3.14 through the py launcher. Works from any folder.
rem Usage: scripts\jarvis-ro.cmd resume
setlocal
pushd "%~dp0.."
py -3.14 "%~dp0jarvis_ro.py" %*
set JARVIS_EXIT=%ERRORLEVEL%
popd
exit /b %JARVIS_EXIT%
