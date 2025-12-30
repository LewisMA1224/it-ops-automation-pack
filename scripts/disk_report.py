#!/usr/bin/env python3
"""
Disk Report (CLI)
- Prints disk usage info for a target path
- Optionally enumerates subfolders for additional rows
- Optionally exports results to CSV

Run examples:
  python app.py --path C:\
  python app.py --path C:\Temp --csv disk_report.csv
  python app.py --path C:\ --recursive --max-depth 2 --csv disk_report.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from shutil import disk_usage
from typing import Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Config:
    """Runtime configuration parsed from CLI."""
    path: Path
    recursive: bool
    max_depth: int
    csv_path: Optional[Path]
    include_hidden: bool


@dataclass(frozen=True)
class DiskRow:
    """A single row of disk usage results."""
    target: str
    total_bytes: int
    used_bytes: int
    free_bytes: int


def human_bytes(num_bytes: int) -> str:
    """Convert bytes to a human-readable string (e.g., 1.2 GB)."""
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{num_bytes} B"


def parse_args(argv: Sequence[str]) -> Config:
    parser = argparse.ArgumentParser(
        description="Generate disk usage report for a path; optionally export CSV."
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Target path to report on (e.g., C:\\ or /home/user).",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="If set, also scan subdirectories and include them as rows.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=1,
        help="Max directory depth for recursive scan (default: 1).",
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        default=None,
        help="Optional CSV output file path (e.g., disk_report.csv).",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden directories in recursive scan.",
    )

    args = parser.parse_args(argv)

    p = Path(args.path).expanduser()
    csv_path = Path(args.csv_path).expanduser() if args.csv_path else None

    # Normalize max_depth
    max_depth = max(0, int(args.max_depth))

    return Config(
        path=p,
        recursive=bool(args.recursive),
        max_depth=max_depth,
        csv_path=csv_path,
        include_hidden=bool(args.include_hidden),
    )


class DiskInspector:
    """Collects disk usage metrics for a path and optional subpaths."""

    def get_usage(self, target: Path) -> DiskRow:
        """
        Get disk usage for target path.

        Note: shutil.disk_usage returns usage for the *filesystem* containing the path,
        not per-folder size. This is intentional: this tool is about free/used space on the drive.
        """
        usage = disk_usage(str(target))
        return DiskRow(
            target=str(target),
            total_bytes=int(usage.total),
            used_bytes=int(usage.used),
            free_bytes=int(usage.free),
        )

    def iter_subdirs(self, base: Path, max_depth: int, include_hidden: bool) -> Iterable[Path]:
        """
        Yield subdirectories up to max_depth.
        Depth 1 => direct children; depth 2 => grandchildren; etc.
        """
        base = base.resolve()

        def is_hidden(path: Path) -> bool:
            # Windows: hidden attribute isn't trivial without pywin32; we approximate by dot-prefix.
            # On Unix, dot-prefix is typical.
            return path.name.startswith(".")

        def walk(current: Path, depth: int) -> Iterable[Path]:
            if depth > max_depth:
                return
            try:
                for child in current.iterdir():
                    if child.is_dir():
                        if (not include_hidden) and is_hidden(child):
                            continue
                        yield child
                        yield from walk(child, depth + 1)
            except PermissionError:
                # Skip folders we can't access; keep the report going.
                return
            except FileNotFoundError:
                return

        if max_depth <= 0:
            return []
        return walk(base, 1)


class ReportWriter:
    """Outputs results to terminal and/or CSV."""

    def print_report(self, rows: List[DiskRow]) -> None:
        if not rows:
            print("No results.")
            return

        # Column widths
        target_w = min(max(len(r.target) for r in rows), 80)
        header = f"{'TARGET'.ljust(target_w)}  {'TOTAL'.rjust(12)}  {'USED'.rjust(12)}  {'FREE'.rjust(12)}  {'FREE%'.rjust(6)}"
        print(header)
        print("-" * len(header))

        for r in rows:
            free_pct = (r.free_bytes / r.total_bytes * 100.0) if r.total_bytes else 0.0
            target = (r.target[: target_w - 3] + "...") if len(r.target) > target_w else r.target
            print(
                f"{target.ljust(target_w)}  "
                f"{human_bytes(r.total_bytes).rjust(12)}  "
                f"{human_bytes(r.used_bytes).rjust(12)}  "
                f"{human_bytes(r.free_bytes).rjust(12)}  "
                f"{free_pct:6.1f}"
            )

    def write_csv(self, csv_path: Path, rows: List[DiskRow]) -> None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now().isoformat(timespec="seconds")

        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["generated_at", now])
            writer.writerow(["target", "total_bytes", "used_bytes", "free_bytes", "free_percent"])
            for r in rows:
                free_pct = (r.free_bytes / r.total_bytes * 100.0) if r.total_bytes else 0.0
                writer.writerow([r.target, r.total_bytes, r.used_bytes, r.free_bytes, f"{free_pct:.2f}"])


def validate_path(p: Path) -> Tuple[bool, str]:
    """Validate the target path and return (ok, message)."""
    try:
        if not p.exists():
            return False, f"Path does not exist: {p}"
        # If path is a file, use its parent for disk usage.
        if p.is_file():
            return True, f"Path is a file; using parent directory for disk usage: {p.parent}"
        if p.is_dir():
            return True, ""
        return False, f"Unsupported path type: {p}"
    except OSError as e:
        return False, f"OS error when checking path: {e}"


def build_rows(cfg: Config, inspector: DiskInspector) -> List[DiskRow]:
    """Build disk usage rows based on config."""
    target = cfg.path

    ok, msg = validate_path(target)
    if not ok:
        raise ValueError(msg)

    if msg:
        print(f"Note: {msg}")

    # disk_usage works on a path; if file, use its parent
    if target.is_file():
        target = target.parent

    rows: List[DiskRow] = []
    rows.append(inspector.get_usage(target))

    if cfg.recursive and target.is_dir():
        for subdir in inspector.iter_subdirs(target, cfg.max_depth, cfg.include_hidden):
            # Same filesystem usage will repeat for many subdirs; still sometimes useful to show coverage.
            # If you want "per-folder size", that's a different feature (directory tree sizing).
            rows.append(inspector.get_usage(subdir))

    return rows


def main(argv: Sequence[str]) -> int:
    try:
        cfg = parse_args(argv)
        inspector = DiskInspector()
        writer = ReportWriter()

        rows = build_rows(cfg, inspector)

        print(f"\nDisk Report for: {cfg.path}")
        if cfg.recursive:
            print(f"Recursive: True (max depth = {cfg.max_depth}, include hidden = {cfg.include_hidden})")
        else:
            print("Recursive: False")

        print()
        writer.print_report(rows)

        if cfg.csv_path:
            writer.write_csv(cfg.csv_path, rows)
            print(f"\nCSV written to: {cfg.csv_path.resolve()}")

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
