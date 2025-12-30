"""
log_cleanup.py
Safely clean up old log files in a target directory.

Defaults to dry-run (no deletions). Use --delete to actually remove files.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Iterable


LOG_EXTENSIONS = {".log", ".txt"}  # adjust if needed


def human_bytes(num: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024:
            return f"{num:.0f} {unit}"
        num /= 1024
    return f"{num:.0f} PB"


def iter_candidate_files(root: Path, recursive: bool) -> Iterable[Path]:
    if recursive:
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in LOG_EXTENSIONS:
                yield p
    else:
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in LOG_EXTENSIONS:
                yield p


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean up old log files safely (dry-run by default)."
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Folder containing logs to review (example: C:\\temp\\logs or /var/log/myapp)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Delete logs older than this many days (default: 30).",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search subfolders recursively.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete files (otherwise dry-run).",
    )

    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"ERROR: path is not a folder: {root}")
        return 2

    cutoff_seconds = time.time() - (args.days * 86400)
    mode = "DELETE" if args.delete else "DRY-RUN"

    candidates = list(iter_candidate_files(root, args.recursive))
    old_files = []
    total_bytes = 0

    for f in candidates:
        try:
            mtime = f.stat().st_mtime
            if mtime < cutoff_seconds:
                size = f.stat().st_size
                old_files.append((f, size, mtime))
                total_bytes += size
        except OSError as e:
            print(f"SKIP: {f} ({e})")

    print(f"Mode: {mode}")
    print(f"Path: {root}")
    print(f"Days threshold: {args.days}")
    print(f"Recursive: {args.recursive}")
    print(f"Found {len(candidates)} candidate files, {len(old_files)} eligible for cleanup.\n")

    deleted = 0
    freed = 0

    for f, size, mtime in sorted(old_files, key=lambda x: x[2]):
        age_days = int((time.time() - mtime) / 86400)
        if args.delete:
            try:
                f.unlink()
                deleted += 1
                freed += size
                print(f"DELETED ({age_days}d): {f} [{human_bytes(size)}]")
            except OSError as e:
                print(f"FAILED: {f} ({e})")
        else:
            print(f"WOULD DELETE ({age_days}d): {f} [{human_bytes(size)}]")

    print("\nSummary")
    print(f"- Eligible files: {len(old_files)}")
    if args.delete:
        print(f"- Deleted files: {deleted}")
        print(f"- Space freed: {human_bytes(freed)}")
    else:
        print(f"- Potential space freed: {human_bytes(total_bytes)}")
        print("- No files were deleted (dry-run). Use --delete to remove files.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
