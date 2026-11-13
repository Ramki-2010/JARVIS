"""`python -m fetcher weather <place>` | `hn` | `news <source|all> [keyword]`: one lookup, one line of JSON on stdout.

Arguments are checked here as well as by the caller. Exit code 0 with {"ok": true, ...} or {"ok": false, "error": ...};
2 for a usage error. Nothing is written to disk.
"""

import json
import re
import sys
import time

from fetcher import keys, lookups, net

KEYWORD = re.compile(r"^[a-z0-9][a-z0-9 ]{0,%d}$" % (keys.KEYWORD_MAX - 1))


def emit(obj) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=True) + "\n")


def run(argv):
    start = time.monotonic()

    def ms():
        return int((time.monotonic() - start) * 1000)

    try:
        name = argv[0] if argv else ""
        if name == "weather" and len(argv) == 2 and argv[1] in keys.PLACES:
            data, hosts, nbytes = lookups.weather(argv[1])
        elif name == "hn" and len(argv) == 1:
            data, hosts, nbytes = lookups.hacker_news()
        elif (name == "news" and 2 <= len(argv) <= 3 and (argv[1] in keys.NEWS or argv[1] == "all")
              and (len(argv) == 2 or KEYWORD.match(argv[2]))):
            data, hosts, nbytes = lookups.news(argv[1], argv[2] if len(argv) == 3 else "")
        else:
            return 2, {"ok": False, "error": "USAGE"}
    except net.FetchFailed as exc:
        return 0, {"ok": False, "error": exc.code, "hosts": [exc.host] if exc.host else [], "ms": ms()}
    except lookups.BadData:
        return 0, {"ok": False, "error": "PARSE", "hosts": [], "ms": ms()}
    return 0, {"ok": True, "lookup": name, "hosts": hosts, "bytes": nbytes, "ms": ms(), "data": data}


def main(argv=None) -> int:
    code, obj = run(list(sys.argv[1:] if argv is None else argv))
    emit(obj)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
