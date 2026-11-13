"""The public-data fetcher (ADR-0014). The only package allowed network modules.

It runs as a short-lived child process of its own (`python -m fetcher <lookup> ...`), reads fixed addresses over
HTTPS and prints one line of JSON. It holds no state, no credentials and no cache. `keys` is plain data shared with
the intent layer and imports nothing from the network.
"""
