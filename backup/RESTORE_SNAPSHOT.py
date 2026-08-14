#!/usr/bin/env python3
"""Restore JUNGLE/OS source files from a JSONL snapshot.

Usage:
    python3 backup/RESTORE_SNAPSHOT.py [--snapshot PATH] [--dest DIR]

Each line of the snapshot is {"path": "...", "content_b64": "..."}.
Absolute paths and paths containing ".." are refused.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path, PurePosixPath

DEFAULT_SNAPSHOT = Path(__file__).with_name("JUNGLE_OS_SOURCE_SNAPSHOT.jsonl")


def is_safe(rel: str) -> bool:
    if not rel or rel.strip() != rel:
        return False
    p = PurePosixPath(rel)
    if p.is_absolute() or rel.startswith("/") or rel.startswith("\\"):
        return False
    if ".." in p.parts:
        return False
    if len(rel) > 1 and rel[1] == ":":  # windows drive letter
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT))
    ap.add_argument("--dest", default=".")
    args = ap.parse_args()

    snapshot = Path(args.snapshot)
    dest = Path(args.dest).resolve()
    if not snapshot.is_file():
        print(f"snapshot not found: {snapshot}", file=sys.stderr)
        return 1

    written = 0
    with snapshot.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                rel = entry["path"]
                data = base64.b64decode(entry["content_b64"], validate=True)
            except Exception as exc:  # malformed line
                print(f"line {lineno}: skipped ({exc})", file=sys.stderr)
                continue

            if not is_safe(rel):
                print(f"line {lineno}: refused unsafe path {rel!r}", file=sys.stderr)
                continue

            target = (dest / rel).resolve()
            if dest != target and dest not in target.parents:
                print(f"line {lineno}: refused escaping path {rel!r}", file=sys.stderr)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            written += 1

    print(f"restored {written} files into {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())