# IT Ops Automation Pack (Python)

A small collection of **production-minded CLI utilities** that mirror real IT support / operations workflows:
- cleaning up old log files
- reporting disk usage
- auditing CSV data used in reporting

## Why this exists
I work in IT support / operations and wanted a public repo that shows how I approach repeatable tasks:
- clean inputs
- safe defaults
- clear output
- logs + error handling

## What’s included
- **log_cleanup** — safely removes old log files (**dry-run by default**)
- **disk_report** — prints disk usage to terminal and can export to CSV
- **csv_audit** — validates and summarizes CSVs (missing values, duplicates, basic stats)

## Quick start
From the repo root (Python 3.10+ recommended):

```bash
python scripts/log_cleanup/log_cleanup.py --help
python scripts/disk_report/disk_report.py --help
python scripts/csv_audit/csv_audit.py --help
```

## Docs / execution proof
Each tool has a short doc with screenshots:
- `docs/log_cleanup/`
- `docs/disk_report/`
- `docs/csv_audit/`

## Notes for employers
This repo emphasizes:
- **CLI ergonomics** (argparse, helpful `--help`, clear flags)
- **Safety** (dry-run defaults, explicit “do the destructive thing” flags)
- **Readable output** (tables / CSV export where useful)
- **Defensive coding** (validation, error handling, predictable behavior)


