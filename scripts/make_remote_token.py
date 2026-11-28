"""`py -3.14 scripts\\make_remote_token.py --file D:\\JARVIS\\governance\\remote.toml`: RK's own tool for the phone's token.

Makes a new random remote token (256 bits), writes ONLY its SHA-256 into the `token_sha256` line of RK's remote settings file,
and prints the phone link once. The token itself is never written anywhere: if the link is lost, run this again (the old link
stops working at the next launch). `--revoke` clears the hash, which switches phone access off. ADR-0011 A4.6.4.
Run it yourself at the laptop: a token printed through any assistant would sit in that assistant's logs.
"""

import argparse
import hashlib
import os
import re
import secrets
import sys
import tempfile
import tomllib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from advisor.remote_config import HOSTNAME  # noqa: E402

LINE = re.compile(r'^(token_sha256\s*=\s*)"[^"\n]*"([ \t]*(?:#.*)?)$', re.M)


def replace_hash(text: str, digest: str) -> str:
    if len(LINE.findall(text)) != 1:
        raise ValueError("the file must hold exactly one token_sha256 line")
    return LINE.sub(lambda m: '%s"%s"%s' % (m.group(1), digest, m.group(2)), text)


def main(argv=None, out=sys.stdout, token_source=secrets.token_urlsafe) -> int:
    ap = argparse.ArgumentParser(prog="make_remote_token", description="Make or revoke the phone's remote token.")
    ap.add_argument("--file", required=True, help="absolute path of the remote settings file")
    ap.add_argument("--revoke", action="store_true", help="clear the token hash (phone access off)")
    args = ap.parse_args(argv)
    path = args.file
    if not os.path.isabs(path) or not os.path.isfile(path):
        print("the settings file must be an absolute path to an existing file", file=out)
        return 2
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        text = fh.read()
    try:
        hostname = tomllib.loads(text)["remote"]["hostname"]
        if not HOSTNAME.match(hostname):
            raise ValueError("hostname")
    except (tomllib.TOMLDecodeError, KeyError, TypeError, ValueError):
        print("the file does not hold a valid [remote] hostname; nothing was changed", file=out)
        return 2
    token = "" if args.revoke else token_source(32)
    digest = "" if args.revoke else hashlib.sha256(token.encode("utf-8")).hexdigest()
    try:
        new_text = replace_hash(text, digest)
    except ValueError as exc:
        print("%s; nothing was changed" % exc, file=out)
        return 2
    fd, temp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".remote-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_text)
        os.replace(temp, path)
    except OSError:
        try:
            os.unlink(temp)
        except OSError:
            pass
        print("the file could not be written; nothing was changed", file=out)
        return 2
    if args.revoke:
        print("The remote token is revoked. Phone access stays off until you make a new one.", file=out)
        return 0
    print("A new remote token was made and its hash saved. Open this link on the phone once, then bookmark it:", file=out)
    print("", file=out)
    print("    https://%s/#t=%s" % (hostname, token), file=out)
    print("", file=out)
    print("It is shown only now and is not stored anywhere. The previous link stops working at the next launch.", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
