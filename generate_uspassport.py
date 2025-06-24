#!/usr/bin/env python
"""
Populate the cleaned passport template from rows in the CSV produced
by your faker pipeline.
"""
import pathlib, argparse, pandas as pd

from config import CSV_FILE
from us_passport_template import fill_passport_template

def main(csv=CSV_FILE, limit=None, out_dir="output/passports"):
    df = pd.read_csv(csv)
    if limit:
        df = df.head(limit)

    out_root = pathlib.Path(out_dir)
    print(f"Writing {len(df)} passports → {out_root.resolve()}")

    for i, row in df.iterrows():
        fname = out_root / f"uspassport{i+1}.png"
        fill_passport_template(row.to_dict(), str(fname))
        if (i + 1) % 10 == 0 or i + 1 == len(df):
            print(f"  {fname.name}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate filled-in passport PNGs.")
    ap.add_argument("--csv", default=CSV_FILE, help="CSV file to read (default: %(default)s)")
    ap.add_argument("--limit", type=int, help="Only create the first N rows")
    ap.add_argument("--out", default="output/passports", help="Output directory")
    args = ap.parse_args()

    main(args.csv, args.limit, args.out) 