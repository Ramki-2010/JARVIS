@echo off
rem Start JARVIS the usual way: free memory, make sure the model server is running, then run the advisor.
rem Usage: scripts\start-jarvis.cmd --dashboard --voice-root D:\JARVIS\voice      (any advisor options are passed on)
rem   set JARVIS_NO_FREE=1 before running to skip closing programs this time.
rem Step 1 closes only the programs on RK's close list (see scripts\free_memory.py); if it fails, JARVIS still starts.
setlocal
pushd "%~dp0.."
set "JARVIS_ROOT=D:\JARVIS"

if not defined JARVIS_NO_FREE py -3.14 scripts\free_memory.py --apply

curl -s -m 3 http://127.0.0.1:11434/api/tags >nul 2>&1
if errorlevel 1 (
  echo starting the model server...
  set "OLLAMA_MODELS=%JARVIS_ROOT%\models\ollama"
  set "OLLAMA_HOST=127.0.0.1:11434"
  start "" /b "%JARVIS_ROOT%\ollama\bin\ollama.exe" serve >> "%JARVIS_ROOT%\ollama\serve.log" 2>&1
  for /l %%i in (1,1,30) do (
    curl -s -m 2 http://127.0.0.1:11434/api/tags >nul 2>&1 && goto ready
    ping -n 2 127.0.0.1 >nul
  )
  echo the model server did not answer in time; the advisor will say so and carry on without conversation.
)
:ready
py -3.14 -m advisor --config "%JARVIS_ROOT%\governance\jarvis.toml" %*
set JARVIS_EXIT=%ERRORLEVEL%
popd
exit /b %JARVIS_EXIT%
