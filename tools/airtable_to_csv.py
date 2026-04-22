#!/usr/bin/env python3
"""Pull the NJCIC Grants table from Airtable and write a CSV that matches the
shape of Airtable's own 'Grid view' CSV export, byte-for-byte where possible.

Output columns (exact order):
  Grantee, Total awarded:, Grant purpose, Grantee website, Year(s) granted:,
  Focus area, Service area, Returned/Cancelled grant?, Reason cancelled/returned:

Usage:
  python3 airtable_to_csv.py [--out PATH]

Default output: ~/projects/njcic-grantees-map/data/Grants-Grid view.csv
Existing file is backed up to .bak-YYYYMMDD-HHMMSS before overwrite.
"""
import argparse
import csv
import json
import shutil
import subprocess
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE_ID  = "appryDZWgPpP0GmZw"
TABLE_ID = "tblFADXYCq495smGH"

COLUMNS = [
    "Grantee",
    "Total awarded:",
    "Grant purpose",
    "Grantee website",
    "Year(s) granted:",
    "Focus area",
    "Service area",
    "Returned/Cancelled grant?",
    "Reason cancelled/returned:",
    "City",
    "Lat",
    "Long",
    "Area",
    "Legislative district",
    "Project",
]


def get_token() -> str:
    return subprocess.check_output(
        ["pass", "show", "claude/tokens/airtable-pat-dnr"], text=True
    ).splitlines()[0]


def fetch_records(token: str) -> list[dict]:
    records, offset = [], None
    while True:
        params = [("pageSize", "100")]
        if offset:
            params.append(("offset", offset))
        url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        records.extend(data["records"])
        offset = data.get("offset")
        if not offset:
            break
    return records


def format_currency(value) -> str:
    if value in (None, "", 0):
        return ""
    # Airtable returns currency as a number; match the existing CSV's '$NNNNN.NN' format
    return f"${float(value):.2f}".replace("$-", "-$")  # keep sign outside if ever negative


def format_years(value) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return str(value)


def format_checkbox(value) -> str:
    return "checked" if value else ""


def format_multiselect(value) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return str(value)


def build_row(fields: dict) -> dict:
    lat = fields.get("Lat")
    lng = fields.get("Long")
    return {
        "Grantee":                    fields.get("Grantee", "") or "",
        "Total awarded:":             format_currency(fields.get("Total awarded:")),
        "Grant purpose":              fields.get("Grant purpose", "") or "",
        "Grantee website":            fields.get("Grantee website", "") or "",
        "Year(s) granted:":           format_years(fields.get("Year(s) granted:")),
        "Focus area":                 fields.get("Focus area", "") or "",
        "Service area":               fields.get("Service area", "") or "",
        "Returned/Cancelled grant?":  format_checkbox(fields.get("Returned/Cancelled grant?")),
        "Reason cancelled/returned:": fields.get("Reason cancelled/returned:", "") or "",
        "City":                       fields.get("City", "") or "",
        "Lat":                        f"{lat:.4f}" if lat is not None else "",
        "Long":                       f"{lng:.4f}" if lng is not None else "",
        "Area":                       format_multiselect(fields.get("Area")),
        "Legislative district":       fields.get("Legislative district", "") or "",
        "Project":                    fields.get("Project", "") or "",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default=str(Path.home() / "projects/njcic-grantees-map/data/Grants-Grid view.csv"),
        help="Output CSV path (default matches current pipeline)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Write to a temp file only")
    args = parser.parse_args()

    out_path = Path(args.out)

    token = get_token()
    records = fetch_records(token)
    rows = [build_row(r["fields"]) for r in records if r["fields"].get("Grantee")]
    print(f"Fetched {len(records)} records; {len(rows)} after filtering for Grantee name")

    # Backup existing file before overwrite (unless dry-run)
    if not args.dry_run and out_path.exists():
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = out_path.with_suffix(out_path.suffix + f".bak-{ts}")
        shutil.copy2(out_path, backup)
        print(f"Backed up old CSV to: {backup}")

    target = out_path if not args.dry_run else Path(f"/tmp/airtable_to_csv_dryrun.csv")
    target.parent.mkdir(parents=True, exist_ok=True)

    # Write with BOM + LF line endings to match Airtable's native export
    with open(target, "wb") as fb:
        fb.write("﻿".encode("utf-8"))
    with open(target, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    size = target.stat().st_size
    print(f"Wrote {target} — {size:,} bytes, {len(rows)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
