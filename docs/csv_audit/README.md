# CSV Audit Tool — csv_audit.py

A command-line utility for validating CSV files used in reporting, audits, and IT operations workflows.

## What It Does

- Reads any well-formed CSV with a header row
- Reports:
  - total rows and columns
  - missing values per column
  - exact duplicate rows
  - basic numeric statistics (min / max / mean)
- Optional outputs:
  - summary audit report CSV
  - duplicate rows CSV for remediation

Designed for safe, read-only inspection of data files.

---

## Usage

### Help
```bash
python csv_audit.py --help

