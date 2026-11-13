"""The voice surface (ADR-0012): local push-to-talk speech in, local speech out.

Runs in its own Python 3.10 interpreter under the data root, started by
`interaction/voice_child.py`. This package has no network or process module
(a static test checks it) and never imports the control plane (`jarvis/`).
Audio goes only to and from the local sound device, through Windows' own
`winmm` library via `ctypes`; nothing is installed for that and nothing is
stored (ADR-0012 D3).
"""
