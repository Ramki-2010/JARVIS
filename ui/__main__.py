"""Start the Stage A dashboard: py -3.14 -m ui [--config <absolute path to jarvis.toml>]

It prints one local address with a per-launch token. Open it in a browser on this
machine. It does not open the browser itself (no other process is started).
"""

import argparse
import os
import sys

from ui.server import DashboardServer

DEFAULT_CONFIG = r"D:\JARVIS\governance\jarvis.toml"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ui", description="JARVIS read-only dashboard (Stage A)")
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--voice-root", help="the voice folder whose live signal drives LISTENING and SPEAKING (default: next to the governance folder)")
    args = parser.parse_args(argv)
    server = DashboardServer(args.config, os.path.join(args.voice_root, "state", "voice_state.json") if args.voice_root else "")
    print("JARVIS dashboard (read-only) on this machine only:")
    print(server.url)
    print("Keep this window open. Ctrl+C stops it.")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
