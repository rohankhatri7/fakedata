from __future__ import annotations

import argparse
import pathlib
from typing import Tuple

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from config import (
    CSV_FILE,
    TEMPLATE_DIR,
    OPENSANS_FONT,
)

TEMPLATE_PATH = TEMPLATE_DIR / "paychex_paystub.png"

# Top-left mailing address block
ADDRESS_XY: Tuple[int, int] = (60, 106)
ADDRESS_LINE_SP: int = 22

# Mid-left "Personal and Check Information" block (under header, above dept)
MIDBLOCK_XY: Tuple[int, int] = (32, 480)
MIDBLOCK_LINE_SP: int = 15

NAME_SIZE: int = 14
ADDR_SIZE: int = 13
SSN_SIZE: int = 11

def _load_font(path: pathlib.Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def _render(text: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    dummy = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy)
    w, h = draw.textbbox((0, 0), text, font=font)[2:]
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((0, 0), text, font=font, fill=(0, 0, 0))
    return img


def _u(val: object) -> str:
    return str(val).strip().upper() if val and str(val).lower() != "nan" else ""


def fill_paychex_paystub(row: dict, out_path: str):
    base = Image.open(TEMPLATE_PATH).convert("RGBA")

    mi = row.get("MiddleInitial", "").strip()
    full_name = f"{row.get('FirstName','').strip()} {mi + ' ' if mi else ''}{row.get('LastName','').strip()}".upper()

    street1 = _u(row.get("Street1"))
    street2 = _u(row.get("Street2"))
    city = _u(row.get("City"))
    state = _u(row.get("State"))
    zip5 = str(row.get("Zip", "")).strip()[:5]
    city_line = f"{city}, {state} {zip5}".strip(", ")

    ssn = str(row.get("SSN", "")).strip()

    font_name_top = _load_font(OPENSANS_FONT, NAME_SIZE)
    font_addr_top = _load_font(OPENSANS_FONT, ADDR_SIZE)
    font_name_mid = _load_font(OPENSANS_FONT, NAME_SIZE - 1)
    font_addr_mid = _load_font(OPENSANS_FONT, ADDR_SIZE - 1)
    font_ssn      = _load_font(OPENSANS_FONT, SSN_SIZE)

    x, y = ADDRESS_XY
    lines = [full_name, street1]
    if street2:
        lines.append(street2)
    lines.append(city_line)

    for line in lines:
        img = _render(line, font_addr_top)
        base.paste(img, (x, y), img)
        y += ADDRESS_LINE_SP

    x, y = MIDBLOCK_XY
    lines_mid = [full_name, street1]
    if street2:
        lines_mid.append(street2)
    lines_mid.append(city_line)
    lines_mid.append(f"SSN: {ssn}")

    for line in lines_mid:
        font = font_name_mid if line == full_name else (font_ssn if line.startswith("SSN") else font_addr_mid)
        img = _render(line, font)
        base.paste(img, (x, y), img)
        y += MIDBLOCK_LINE_SP

    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, "PNG")


def main(csv_path: str = CSV_FILE, limit: int | None = None, out_dir: str = "output/paystubs/paychex"):
    df = pd.read_csv(csv_path)
    if limit is not None:
        df = df.head(limit)

    out_root = pathlib.Path(out_dir).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    print(f"Creating {len(df)} Paychex stubs → {out_root}")

    for idx, row in df.iterrows():
        outfile = out_root / f"paychex{idx+1}.png"
        fill_paychex_paystub(row.to_dict(), str(outfile))
        if (idx + 1) % 10 == 0 or (idx + 1) == len(df):
            print(f"  → {outfile.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fill Paychex pay-stub template with address & SSN from CSV rows.")
    parser.add_argument("--csv", default=CSV_FILE, help="CSV file produced by app.py (default: %(default)s)")
    parser.add_argument("--limit", type=int, default=None, help="Generate only the first N rows")
    parser.add_argument("--out", default="output/paychex", help="Output directory for Paychex stub PNGs")
    args = parser.parse_args()

    main(args.csv, args.limit, args.out)
