"""The local model advisory surface (ADR-0013 and its Amendment 1).

A separate package outside `jarvis/`. It talks to a local model runtime on the
loopback interface only, uses only models on RK's approved list, and treats
everything the model says as untrusted text with no authority. It never imports
the control plane (`jarvis/`); it reaches it only through `interaction/`.
"""
