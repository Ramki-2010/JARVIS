"""Canonical serialization for audit records and golden files (ADR-0005 D4).

A record is serialized once to UTF-8 bytes with sorted keys and no insignificant
whitespace. No Unicode normalisation. No floating-point numbers. Duplicate keys
on parse are an error. The stored bytes are what is hashed; verification
re-hashes stored bytes and never re-serializes.
"""

import hashlib
import json


class CanonicalError(ValueError):
    pass


def _check(value, path="$"):
    if isinstance(value, float):
        raise CanonicalError("floating-point value at %s" % path)
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise CanonicalError("non-string key at %s" % path)
            _check(v, "%s.%s" % (path, k))
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _check(v, "%s[%d]" % (path, i))
    elif value is None or isinstance(value, (str, int, bool)):
        return
    else:
        raise CanonicalError("unsupported type %s at %s" % (type(value).__name__, path))


def dumps(value) -> bytes:
    """Canonical UTF-8 bytes. Raises CanonicalError on floats, unsupported types
    or strings that cannot be encoded as UTF-8 (for example lone surrogates)."""
    _check(value)
    text = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CanonicalError("string is not encodable as UTF-8") from exc


def _no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise CanonicalError("duplicate key %r" % (k,))
        out[k] = v
    return out


def _reject_float(text):
    raise CanonicalError("floating-point value %s" % text)


def _reject_constant(text):
    raise CanonicalError("non-finite constant %s" % text)


def loads(data: bytes):
    """Parse canonical bytes. Rejects duplicate keys, floats and NaN/Infinity."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CanonicalError("not UTF-8") from exc
    return json.loads(text, object_pairs_hook=_no_duplicates,
                      parse_float=_reject_float, parse_constant=_reject_constant)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
