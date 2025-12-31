# Scripts

This folder contains small, production-minded utilities that mirror common IT support / operations workflows.

## What’s included
- **log_cleanup/log_cleanup.py** — safely removes old log files (supports dry-run)
- **disk_report/disk_report.py** — reports disk usage to terminal and optional CSV export
- **csv_audit/csv_audit.py** — validates and summarizes CSVs (missing values, duplicates, basic stats)

## Standards (how these are written)
These scripts aim to follow expectations you’d see in an enterprise environment:
- **Safe defaults** (no destructive actions without explicit flags)
- **Clear CLI behavior** (`--help`, predictable inputs/outputs)
- **Input validation** (fail fast, readable errors)
- **Auditable output** (human-readable console + machine-friendly CSV when applicable)

## Quick start
From the repo root:

```bash
python scripts/log_cleanup/log_cleanup.py --help
python scripts/disk_report/disk_report.py --help
python scripts/csv_audit/csv_audit.py --help
```
