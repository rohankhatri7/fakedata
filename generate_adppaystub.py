#!/usr/bin/env python
from __future__ import annotations

import argparse, pathlib
from typing import Tuple

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from config import (
    CSV_FILE, TEMPLATE_DIR, OPENSANS_FONT, SIGNATURE_FONT,
)

TEMPLATE_PATH = TEMPLATE_DIR / "cleanadp_paystub.png"

ADDRESS_XY        = (880, 290)   
ADDRESS_LINE_SP   = 40  
LOWER_LEFT_XY     = (215, 1560) 
SIGNATURE_XY      = (800, 1720) 

NAME_SIZE         = 28  
ADDR_SIZE         = 24  
SIGNATURE_SIZE    = 30  


def _load_font(path: pathlib.Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def _render(text: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    """Render text to RGBA image (tight bounding box)."""
    dummy = Image.new("RGB", (1, 1))
    draw  = ImageDraw.Draw(dummy)
    w, h = draw.textbbox((0, 0), text, font=font)[2:]
    img  = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((0, 0), text, font=font, fill=(0, 0, 0))
    return img


def fill_adp_paystub(row: dict, out_path: str):
    base = Image.open(TEMPLATE_PATH).convert("RGBA")

    mi = row.get("MiddleInitial", "").strip()
    full_name = f"{row.get('FirstName','').strip()} {mi + ' ' if mi else ''}{row.get('LastName','').strip()}".upper()

    def _u(val: object) -> str:
        return str(val).strip().upper() if val and str(val).lower() != "nan" else ""

    street1 = _u(row.get("Street1"))
    street2 = _u(row.get("Street2"))
    city    = _u(row.get("City"))
    state   = _u(row.get("State"))
    zip5    = str(row.get("Zip", "")).strip()[:5]
    city_line = f"{city}, {state} {zip5}".strip()

    font_addr = _load_font(OPENSANS_FONT, ADDR_SIZE)
    lines = [full_name, street1]
    if street2:
        lines.append(street2)
    lines.append(city_line)

    x, y = ADDRESS_XY
    for ln in lines:
        txt_img = _render(ln, font_addr)
        base.paste(txt_img, (x, y), txt_img)
        y += ADDRESS_LINE_SP

    font_name = _load_font(OPENSANS_FONT, NAME_SIZE)
    ll_img    = _render(full_name, font_name)
    base.paste(ll_img, LOWER_LEFT_XY, ll_img)

    font_sig = _load_font(SIGNATURE_FONT, SIGNATURE_SIZE)
    sig_img  = _render(full_name, font_sig)
    base.paste(sig_img, SIGNATURE_XY, sig_img)

    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, "PNG")


def main(csv_path: str = CSV_FILE, limit: int | None = None, out_dir: str = "output/paystubs/adp"):
    df = pd.read_csv(csv_path)
    if limit is not None:
        df = df.head(limit)

    out_root = pathlib.Path(out_dir).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    print(f"Creating {len(df)} pay-stubs → {out_root}")

    for idx, row in df.iterrows():
        outfile = out_root / f"adp{idx+1}.png"
        fill_adp_paystub(row.to_dict(), str(outfile))
        if (idx + 1) % 10 == 0 or (idx + 1) == len(df):
            print(f"  → {outfile.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fill ADP pay-stub template with address & signature from CSV rows.")
    parser.add_argument("--csv", default=CSV_FILE, help="CSV file produced by app.py (default: %(default)s)")
    parser.add_argument("--limit", type=int, default=None, help="Generate only the first N rows")
    parser.add_argument("--out", default="output/paystubs/adp", help="Output directory for pay-stub PNGs")
    args = parser.parse_args()

    main(args.csv, args.limit, args.out) 