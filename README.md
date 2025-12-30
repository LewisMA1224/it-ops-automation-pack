# IT Ops Automation Pack (Python)

Three small, practical scripts that mirror real IT support workflows: cleaning logs, reporting disk usage, and auditing CSV data.

## Why this exists
I work in IT support / operations and wanted a public repo that shows how I approach repeatable tasks:
- clean inputs
- safe defaults
- clear output
- logs + error handling

## Scripts
- **log_cleanup.py** — deletes old log files (with a dry-run option)
- **disk_report.py** — outputs disk usage to terminal + CSV
- **csv_audit.py** — validates a CSV (missing values, duplicates, basic stats)

## Quick start
```bash
python scripts/log_cleanup.py --help
python scripts/disk_report.py --help
python scripts/csv_audit.py --help

