# python generate_india_passport_docs.py [--csv myrows.csv] [--limit N] [--out output/passports]
import argparse, pathlib, pandas as pd

from config import CSV_FILE
from india_passport_template import fill_india_passport_template

def main(csv_path: str = CSV_FILE, limit: int | None = None, out_dir: str = "output/passports"):
    df = pd.read_csv(csv_path)
    if limit is not None:
        df = df.head(limit)

    out_root = pathlib.Path(out_dir).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    print(f"Creating {len(df)} Indian passports → {out_root}")

    for idx, row in df.iterrows():
        outfile = out_root / f"indiapassport{idx+1}.png"
        fill_india_passport_template(row.to_dict(), str(outfile))
        if (idx + 1) % 10 == 0 or (idx + 1) == len(df):
            print(f"  → {outfile.name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fill Indian passport PNG templates with generated data.")
    parser.add_argument("--csv", default=CSV_FILE, help="CSV produced by app.py (default: %(default)s)")
    parser.add_argument("--limit", type=int, default=None, help="Generate only the first N rows")
    parser.add_argument("--out", default="output/passports", help="Output directory (default: %(default)s)")
    args = parser.parse_args()

    main(args.csv, args.limit, args.out) 