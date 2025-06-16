#!/usr/bin/env python
# generate SSN documents from CSV
import os, pathlib, pandas as pd, argparse, random
from config import CSV_FILE, SSN_TEMPLATE_PATH, HANDWRITING_FONT
from ssn_template import fill_ssn_template


def main(csv_path: str, limit: int = None, output_dir: str = "output/ssn_docs"):
    df = pd.read_csv(csv_path)
    if limit is not None:
        df = df.head(limit)

    out_root = pathlib.Path(output_dir).expanduser().resolve()
    print(f"Creating SSN documents from {len(df)} rows … (output dir: {out_root})")

    for idx, row in df.iterrows():
        outfile = out_root / f"ssn{idx+1}.png"
        fill_ssn_template(row.to_dict(), str(outfile))
        if (idx + 1) % 10 == 0 or (idx + 1) == len(df):
            print(f"  → {outfile}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fill SSN PNG templates with generated data.")
    parser.add_argument("--csv", default=CSV_FILE, help="Path to CSV produced by app.py (default: %(default)s)")
    parser.add_argument("--limit", type=int, default=None, help="Generate only the first N rows")
    parser.add_argument("--out", default="output/ssn_docs", help="Directory to write filled PNGs")
    args = parser.parse_args()

    main(args.csv, args.limit, args.out) 