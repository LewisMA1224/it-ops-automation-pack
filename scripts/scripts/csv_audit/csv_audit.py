#!/usr/bin/env python3
"""
csv_audit.py — CSV Validation + Quick Stats (CLI)

What it does:
- Reads any well-formed CSV (with a header row)
- Reports:
  - total rows, total columns
  - missing values per column (empty cells)
  - duplicate rows (exact duplicates across all columns)
  - basic numeric stats (min/max/mean) for columns that look numeric

Run examples (Windows-friendly):
  python csv_audit.py --path "C:\\Temp\\people-1000.csv"
  python csv_audit.py --path "C:\\Temp\\people-1000.csv" --report "C:\\Temp\\audit_report.csv"
  python csv_audit.py --path "C:\\Temp\\people-1000.csv" --delimiter ","
  python csv_audit.py --path "C:\\Temp\\people-1000.csv" --top-unique 5

Notes:
- Missing value = empty string after trimming whitespace
- Duplicate row = an exact match across *all* columns (after trimming)
- Numeric detection: tries to parse floats (ignores commas like "1,234")
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Config:
    path: Path
    delimiter: str
    encoding: str
    report_path: Optional[Path]
    top_unique: int


def parse_args(argv: Sequence[str]) -> Config:
    parser = argparse.ArgumentParser(description="Audit a CSV file for missing values, duplicates, and basic stats.")
    parser.add_argument("--path", required=True, help="Path to CSV file (must have a header row).")
    parser.add_argument("--delimiter", default=",", help="CSV delimiter (default: ',').")
    parser.add_argument("--encoding", default="utf-8", help="File encoding (default: utf-8).")
    parser.add_argument("--report", dest="report_path", default=None, help="Optional output CSV report path.")
    parser.add_argument(
        "--top-unique",
        type=int,
        default=0,
        help="If > 0, include top N most common values per column (can be slower on large CSVs).",
    )
    args = parser.parse_args(argv)

    p = Path(args.path).expanduser()
    rp = Path(args.report_path).expanduser() if args.report_path else None

    delim = args.delimiter
    if len(delim) != 1:
        raise ValueError("Delimiter must be a single character (e.g., ',' or '\\t').")

    return Config(
        path=p,
        delimiter=delim,
        encoding=args.encoding,
        report_path=rp,
        top_unique=max(0, int(args.top_unique)),
    )


def normalize_cell(value: Optional[str]) -> str:
    """Trim whitespace; treat None as empty."""
    return (value or "").strip()


def safe_float(value: str) -> Optional[float]:
    """
    Try to parse a number.
    - Strips commas: "1,234.5" -> 1234.5
    - Returns None if it cannot parse
    """
    v = value.strip()
    if v == "":
        return None
    v = v.replace(",", "")
    try:
        return float(v)
    except ValueError:
        return None


class CSVReader:
    def read_rows(self, path: Path, delimiter: str, encoding: str) -> Tuple[List[str], List[Dict[str, str]]]:
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {path}")
        if not path.is_file():
            raise ValueError(f"Not a file: {path}")

        with path.open("r", encoding=encoding, newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            if reader.fieldnames is None:
                raise ValueError("CSV appears to have no header row (fieldnames missing).")

            headers = [h.strip() for h in reader.fieldnames if h is not None]
            if not headers:
                raise ValueError("CSV header row is empty.")

            rows: List[Dict[str, str]] = []
            for row in reader:
                # Normalize: ensure all headers exist even if missing in row
                normalized = {h: normalize_cell(row.get(h)) for h in headers}
                rows.append(normalized)

        return headers, rows


@dataclass
class ColumnAudit:
    column: str
    non_empty: int
    missing: int
    unique_count: int
    numeric_count: int
    numeric_min: Optional[float]
    numeric_max: Optional[float]
    numeric_mean: Optional[float]
    top_values: List[Tuple[str, int]]  # (value, count)


@dataclass
class AuditResult:
    path: str
    rows: int
    columns: int
    duplicate_rows: int
    duplicate_row_examples: List[Tuple[int, int]]  # (first_index, dup_index) 1-based row indices
    per_column: List[ColumnAudit]


class Auditor:
    def audit(
        self,
        path: Path,
        headers: List[str],
        rows: List[Dict[str, str]],
        top_unique: int,
    ) -> AuditResult:
        row_count = len(rows)
        col_count = len(headers)

        # Duplicate detection: exact full-row match after normalization
        seen: Dict[Tuple[str, ...], int] = {}
        dup_count = 0
        dup_examples: List[Tuple[int, int]] = []

        for idx, r in enumerate(rows, start=1):  # 1-based
            signature = tuple(r.get(h, "") for h in headers)
            if signature in seen:
                dup_count += 1
                if len(dup_examples) < 10:  # keep examples small
                    dup_examples.append((seen[signature], idx))
            else:
                seen[signature] = idx

        per_column: List[ColumnAudit] = []
        for h in headers:
            values = [r.get(h, "") for r in rows]
            missing = sum(1 for v in values if normalize_cell(v) == "")
            non_empty = row_count - missing

            uniques: Dict[str, int] = {}
            numeric_vals: List[float] = []

            for v in values:
                nv = normalize_cell(v)
                if nv != "":
                    uniques[nv] = uniques.get(nv, 0) + 1
                    f = safe_float(nv)
                    if f is not None:
                        numeric_vals.append(f)

            unique_count = len(uniques)
            numeric_count = len(numeric_vals)

            if numeric_vals:
                nmin = min(numeric_vals)
                nmax = max(numeric_vals)
                nmean = sum(numeric_vals) / len(numeric_vals)
            else:
                nmin = nmax = nmean = None

            top_values: List[Tuple[str, int]] = []
            if top_unique > 0 and uniques:
                # Sort by count desc, then value asc for stability
                top_values = sorted(uniques.items(), key=lambda x: (-x[1], x[0]))[:top_unique]

            per_column.append(
                ColumnAudit(
                    column=h,
                    non_empty=non_empty,
                    missing=missing,
                    unique_count=unique_count,
                    numeric_count=numeric_count,
                    numeric_min=nmin,
                    numeric_max=nmax,
                    numeric_mean=nmean,
                    top_values=top_values,
                )
            )

        return AuditResult(
            path=str(path),
            rows=row_count,
            columns=col_count,
            duplicate_rows=dup_count,
            duplicate_row_examples=dup_examples,
            per_column=per_column,
        )


class ReportWriter:
    def print_summary(self, result: AuditResult) -> None:
        print(f"\nCSV Audit Report")
        print(f"File: {result.path}")
        print(f"Rows: {result.rows}")
        print(f"Columns: {result.columns}")
        print(f"Duplicate rows (exact): {result.duplicate_rows}")

        if result.duplicate_row_examples:
            print("Duplicate examples (first_row -> duplicate_row):")
            for a, b in result.duplicate_row_examples:
                print(f"  {a} -> {b}")

        print("\nPer-column results:")
        print("-" * 90)
        print(f"{'COLUMN':30} {'MISSING':>8} {'UNIQUE':>8} {'NUM#':>8} {'MIN':>12} {'MAX':>12} {'MEAN':>12}")
        print("-" * 90)

        for c in result.per_column:
            min_s = f"{c.numeric_min:.3f}" if c.numeric_min is not None else "-"
            max_s = f"{c.numeric_max:.3f}" if c.numeric_max is not None else "-"
            mean_s = f"{c.numeric_mean:.3f}" if c.numeric_mean is not None else "-"
            print(
                f"{c.column[:30]:30} "
                f"{c.missing:8d} "
                f"{c.unique_count:8d} "
                f"{c.numeric_count:8d} "
                f"{min_s:>12} "
                f"{max_s:>12} "
                f"{mean_s:>12}"
            )

            if c.top_values:
                tv = ", ".join([f"{v}({n})" for v, n in c.top_values])
                print(f"{'':4}Top values: {tv}")

        print("-" * 90)

    def write_report_csv(self, report_path: Path, result: AuditResult) -> None:
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with report_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["file", result.path])
            w.writerow(["rows", result.rows])
            w.writerow(["columns", result.columns])
            w.writerow(["duplicate_rows_exact", result.duplicate_rows])
            if result.duplicate_row_examples:
                w.writerow(["duplicate_examples_first_to_dup", "; ".join([f"{a}->{b}" for a, b in result.duplicate_row_examples])])
            else:
                w.writerow(["duplicate_examples_first_to_dup", ""])

            w.writerow([])
            w.writerow(["column", "non_empty", "missing", "unique_count", "numeric_count", "numeric_min", "numeric_max", "numeric_mean"])

            for c in result.per_column:
                w.writerow([
                    c.column,
                    c.non_empty,
                    c.missing,
                    c.unique_count,
                    c.numeric_count,
                    "" if c.numeric_min is None else f"{c.numeric_min:.6f}",
                    "" if c.numeric_max is None else f"{c.numeric_max:.6f}",
                    "" if c.numeric_mean is None else f"{c.numeric_mean:.6f}",
                ])

            # Optional: top values section
            any_top = any(bool(c.top_values) for c in result.per_column)
            if any_top:
                w.writerow([])
                w.writerow(["top_values_per_column"])
                for c in result.per_column:
                    if c.top_values:
                        w.writerow([c.column, "; ".join([f"{v}({n})" for v, n in c.top_values])])


def main(argv: Sequence[str]) -> int:
    try:
        cfg = parse_args(argv)
        reader = CSVReader()
        auditor = Auditor()
        writer = ReportWriter()

        headers, rows = reader.read_rows(cfg.path, cfg.delimiter, cfg.encoding)
        result = auditor.audit(cfg.path, headers, rows, cfg.top_unique)

        writer.print_summary(result)

        if cfg.report_path:
            writer.write_report_csv(cfg.report_path, result)
            print(f"\nReport CSV written to: {cfg.report_path.resolve()}")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
