"""Versioned, bounded interchange format for desktop and browser history."""

import json
import math
import os
import tempfile
from pathlib import Path

MAX_BYTES = 100_000
MAX_BACKUP = 10_000_000
MAX_ITEMS = 2000


def validate_records(records):
    if not isinstance(records, list) or len(records) > MAX_ITEMS:
        raise ValueError("Backup must contain at most 2,000 snippets.")
    clean = []
    seen = set()
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("Invalid snippet record.")
        body, category = row.get("body"), row.get("category")
        pinned, copied = row.get("pinned"), row.get("copied")
        if (
            not isinstance(body, str)
            or not body.strip()
            or len(body.encode("utf-8")) > MAX_BYTES
        ):
            raise ValueError("Each snippet must contain text and fit within 100 KB.")
        if not isinstance(category, str) or not category.strip() or len(category) > 80:
            raise ValueError("Each category must contain 1–80 characters.")
        if type(pinned) is not bool:
            raise ValueError("Pinned must be true or false.")
        if (
            type(copied) not in (int, float)
            or not math.isfinite(copied)
            or not 0 <= copied <= 253402214400
        ):
            raise ValueError("Invalid copy date.")
        if body in seen:
            raise ValueError("Backup contains duplicate snippet text.")
        seen.add(body)
        clean.append(
            dict(body=body, category=category.strip(), pinned=pinned, copied=copied)
        )
    return clean


def decode_backup(raw):
    if len(raw.encode("utf-8")) > MAX_BACKUP:
        raise ValueError("Backup exceeds 10 MB.")
    try:
        document = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise ValueError("Backup is not valid JSON.") from exc
    if (
        not isinstance(document, dict)
        or document.get("format") != "clipview"
        or type(document.get("version")) is not int
        or document["version"] != 1
    ):
        raise ValueError("Unsupported backup format or version.")
    return validate_records(document.get("clips"))


def encode_backup(records):
    rows = [
        dict(
            body=r["body"],
            category=r["category"],
            pinned=bool(r["pinned"]),
            copied=r["copied"],
        )
        for r in records
    ]
    validate_records(rows)
    raw = json.dumps(
        dict(format="clipview", version=1, clips=rows), ensure_ascii=False, indent=2
    )
    if len(raw.encode("utf-8")) > MAX_BACKUP:
        raise ValueError("Backup exceeds 10 MB. Export a smaller collection.")
    return raw


def write_backup(path, records):
    """Replacing a backup only after a complete write; keeping private permissions."""
    data = encode_backup(records)
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix=".clipview-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
