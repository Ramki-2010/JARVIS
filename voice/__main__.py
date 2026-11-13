"""`python -m voice --root <voice data folder>`: the voice worker (started by interaction/voice_child.py)."""

import argparse
import os
import sys

from voice.worker import Worker


def main() -> int:
    ap = argparse.ArgumentParser(prog="voice")
    ap.add_argument("--root", required=True, help="absolute path of the voice data folder")
    args = ap.parse_args()
    if not os.path.isabs(args.root) or not os.path.isdir(args.root):
        print("the voice folder must be an existing absolute path", file=sys.stderr)
        return 2
    return Worker(args.root).main()


if __name__ == "__main__":
    raise SystemExit(main())
