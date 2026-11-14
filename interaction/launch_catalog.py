"""The launch catalog (ADR-0015 D4): RK's file, read and validated here, never written.

`launch_catalog.toml` lives in the governance zone beside the policy and the registry. Each entry is checked at load and
again just before use; an entry that fails is dropped with a plain notice (the id only), never guessed or repaired.
Nothing here starts a process or opens a socket.
"""

import os
import re
import tomllib
from typing import Dict, List, NamedTuple, Optional, Tuple

MAX_ENTRIES = 64
MAX_ARG_CHARS = 300
ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,30}$")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .'&-]{0,40}$")
DRIVE_PATH = re.compile(r"^[A-Za-z]:\\")
VAR = re.compile(r"%([A-Za-z0-9_()]+)%")
# The only environment variables a catalog path may use. The values come from the running user's own environment.
ALLOWED_VARS = ("USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "SYSTEMROOT", "PROGRAMDATA")
# ADR-0015 D4: the ceiling of openable file types. The catalog may narrow it, never widen it.
FILE_EXTENSIONS = frozenset({".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".mp3", ".flac", ".wav", ".m4a", ".ogg",
                             ".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".txt", ".md"})
# ADR-0015 D3 item 4: never openable, whatever the catalog says.
NEVER_OPEN = frozenset({".exe", ".msi", ".bat", ".cmd", ".com", ".ps1", ".psm1", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".hta",
                        ".jar", ".reg", ".lnk", ".url", ".scr", ".dll", ".sys", ".cpl", ".msc", ".appx", ".msix",
                        ".zip", ".7z", ".rar", ".iso", ".img", ".vhd", ".vhdx", ".cab", ".tar", ".gz"})
FILE_PLACEHOLDER = "{file}"
_ADDRESS = re.compile(r"^https://[A-Za-z0-9._~:/?#@!$&'()*+,;=%\[\]-]{1,200}$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_SCHEMES = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")


class Entry(NamedTuple):
    kind: str                 # "app", "folder" or "game"
    id: str
    name: str
    spoken: Tuple[str, ...]
    exe: str = ""             # apps and games: absolute path of a local .exe
    args: Tuple[str, ...] = ()
    file_args: Tuple[str, ...] = ()   # apps only: the argument template for a file ("{file}" as a whole element)
    path: str = ""            # folders: absolute local path


class FileRule(NamedTuple):
    program: str              # an app id
    extensions: Tuple[str, ...]
    folders: Tuple[str, ...]  # folder ids the rule applies to


class Catalog(NamedTuple):
    apps: Dict[str, Entry]
    folders: Dict[str, Entry]
    games: Dict[str, Entry]
    rules: Tuple[FileRule, ...]
    notices: Tuple[str, ...]

    def count(self) -> int:
        return len(self.apps) + len(self.folders) + len(self.games)


EMPTY = Catalog({}, {}, {}, (), ())


def normalise(text: str) -> str:
    """Lower case, punctuation to spaces, filler words dropped: the form names are compared in."""
    words = [w for w in re.findall(r"[a-z0-9]+", str(text).casefold()) if w not in ("the", "my", "a", "an")]
    return " ".join(words)


def expand(raw: str, env=None) -> Optional[str]:
    """Replace %NAME% for the allowed variables only; None if any other variable or an empty value appears."""
    env = os.environ if env is None else env
    bad = []

    def sub(match):
        name = match.group(1).upper()
        value = env.get(name) or env.get(match.group(1))
        if name not in ALLOWED_VARS or not value:
            bad.append(name)
            return ""
        return value

    out = VAR.sub(sub, raw)
    return None if bad or "%" in out else out


def _local_path(raw, env) -> Optional[str]:
    if not isinstance(raw, str) or not raw or _CONTROL.search(raw):
        return None
    path = expand(raw, env)
    if path is None or not DRIVE_PATH.match(path) or path.startswith("\\\\") or ".." in path.replace("\\", "/").split("/"):
        return None
    return os.path.normpath(path)


def _args(raw, kind: str, allow_file: bool):
    """Validate a fixed argument list; None if any element is not acceptable."""
    if not isinstance(raw, list) or len(raw) > 8:
        return None
    out = []
    for item in raw:
        if not isinstance(item, str) or len(item) > MAX_ARG_CHARS or _CONTROL.search(item):
            return None
        if FILE_PLACEHOLDER in item and not (allow_file and item == FILE_PLACEHOLDER):
            return None
        scheme = _SCHEMES.match(item)
        if scheme:
            name = scheme.group(0)[:-3].lower()
            if name == "https":
                if not _ADDRESS.match(item):
                    return None
            elif not (name == "steam" and kind == "game" and re.fullmatch(r"steam://[A-Za-z0-9/_-]{1,60}", item)):
                return None
        elif item.lower().startswith("http:"):
            return None
        out.append(item)
    return tuple(out)


def _spoken(raw, name: str) -> Optional[Tuple[str, ...]]:
    names = [name] + (raw if isinstance(raw, list) else [])
    if any(not isinstance(n, str) or not NAME_RE.match(n) for n in names):
        return None
    return tuple(sorted({normalise(n) for n in names if normalise(n)}))


def parse(data: dict, env=None, exists=os.path.isfile, is_dir=os.path.isdir) -> Catalog:
    """Validate a parsed catalog. Bad entries are dropped and named (by id) in the notices."""
    apps: Dict[str, Entry] = {}
    folders: Dict[str, Entry] = {}
    games: Dict[str, Entry] = {}
    rules: List[FileRule] = []
    notices: List[str] = []
    seen_ids = set()
    total = 0

    def drop(ident, why):
        notices.append("catalog entry %s dropped: %s" % (ident if isinstance(ident, str) and ID_RE.match(ident) else "?", why))

    if data.get("schema_version") != 1:
        return Catalog({}, {}, {}, (), ("the launch catalog has an unknown schema version",))
    for kind, table, plural in (("app", apps, "app"), ("folder", folders, "folder"), ("game", games, "game")):
        for raw in data.get(plural, []) if isinstance(data.get(plural), list) else []:
            total += 1
            if total > MAX_ENTRIES:
                notices.append("the catalog has more than %d entries; the rest were ignored" % MAX_ENTRIES)
                break
            if not isinstance(raw, dict):
                drop("?", "not a table")
                continue
            ident, name = raw.get("id"), raw.get("name")
            if not (isinstance(ident, str) and ID_RE.match(ident)):
                drop("?", "bad id")
                continue
            if ident in seen_ids:
                drop(ident, "duplicate id")
                continue
            spoken = _spoken(raw.get("spoken"), name) if isinstance(name, str) else None
            if spoken is None:
                drop(ident, "bad name")
                continue
            if kind == "folder":
                path = _local_path(raw.get("path"), env)
                if path is None or not is_dir(path):
                    drop(ident, "folder missing or not a local absolute path")
                    continue
                entry = Entry("folder", ident, name, spoken, path=path)
            else:
                exe = _local_path(raw.get("exe"), env)
                if exe is None or not exe.lower().endswith(".exe") or not exists(exe):
                    drop(ident, "program missing, not a local absolute .exe path")
                    continue
                args = _args(raw.get("args", []), kind, False)
                file_args = _args(raw.get("file_args", []), kind, True) if kind == "app" else ()
                if args is None or file_args is None:
                    drop(ident, "bad arguments")
                    continue
                entry = Entry(kind, ident, name, spoken, exe=exe, args=args, file_args=file_args)
            seen_ids.add(ident)
            table[ident] = entry
    for raw in data.get("filetype", []) if isinstance(data.get("filetype"), list) else []:
        program, exts, where = raw.get("program") if isinstance(raw, dict) else None, raw.get("extensions") if isinstance(raw, dict) else None, raw.get("folders") if isinstance(raw, dict) else None
        ok = (isinstance(program, str) and program in apps and apps[program].file_args and isinstance(exts, list) and isinstance(where, list)
              and exts and where and all(isinstance(e, str) for e in exts) and all(isinstance(f, str) and f in folders for f in where))
        exts = tuple(sorted({e.lower() for e in exts if isinstance(e, str)})) if ok else ()
        if not ok or not set(exts) <= FILE_EXTENSIONS:
            notices.append("a filetype rule was dropped: it names an unknown program or folder, or an extension outside the allow list")
            continue
        rules.append(FileRule(program, exts, tuple(where)))
    return Catalog(apps, folders, games, tuple(rules), tuple(notices))


def load(path: str, env=None) -> Optional[Catalog]:
    """The validated catalog, EMPTY-with-notice if the file is unreadable, or None if there is no catalog file."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return Catalog({}, {}, {}, (), ("the launch catalog could not be read",))
    return parse(data, env)


def recheck(entry: Entry, exists=os.path.isfile, is_dir=os.path.isdir) -> bool:
    """Just before use: the program or folder is still there."""
    return bool(is_dir(entry.path)) if entry.kind == "folder" else bool(exists(entry.exe))


def lookup(catalog: Catalog, name: str, hint: str = "") -> List[Entry]:
    """Entries whose id, name or spoken name equals `name` (compared in normalised form), narrowed by a kind hint."""
    want = normalise(name)
    if not want:
        return []
    kinds = {"app": ("app",), "application": ("app",), "program": ("app",), "folder": ("folder",), "directory": ("folder",),
             "game": ("game",)}.get(hint, ("app", "game", "folder"))
    tables = {"app": catalog.apps, "folder": catalog.folders, "game": catalog.games}
    found = []
    for kind in kinds:
        for entry in tables[kind].values():
            if want == normalise(entry.id) or want in entry.spoken:
                found.append(entry)
    return found
