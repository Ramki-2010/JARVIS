@echo off
rem Start the read-only JARVIS dashboard with the pinned interpreter (Python 3.14).
rem It listens on 127.0.0.1 only and prints one address with a per-launch token.
rem Usage: scripts\jarvis-ui.cmd [--config D:\path\to\jarvis.toml]
setlocal
pushd "%~dp0.."
py -3.14 -m ui %*
set JARVIS_EXIT=%ERRORLEVEL%
popd
exit /b %JARVIS_EXIT%
