#!/usr/bin/env python

from __future__ import annotations

import argparse, random
from pathlib import Path
from typing import List, Tuple, Optional

from PIL import Image, ImageDraw, ImageFont

from config import (
    BLANK_PAGE_PATH, PAGE_WIDTH, PAGE_HEIGHT,
    CSV_FILE, HANDWRITING_FONT
)

###############################################################################
# Tunables
###############################################################################
MARGIN               = 50          # all-around page margin (pixels)
SCALE_MIN, SCALE_MAX = 1.2, 1.6   # random scale factor applied to passport PNG
ID_FONT_SIZE         = 48          # AccountID / HealthBenefitID text size
###############################################################################


def _load_blank_page() -> Image.Image:
    """Return a PIL image sized to the configured PAGE_WIDTH × PAGE_HEIGHT."""
    template = Path(BLANK_PAGE_PATH)
    if template.exists():
        page = Image.open(template).convert("RGB")
        return page.resize((PAGE_WIDTH, PAGE_HEIGHT), Image.LANCZOS)
    # fallback – plain white if template is missing
    return Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(HANDWRITING_FONT), size)


def _render_text(text: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    dummy_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    w, h = dummy_draw.textbbox((0, 0), text, font=font)[2:4]
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((0, 0), text, font=font, fill=(0, 0, 0))
    return img


def _overlap(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 < bx1 or ax1 > bx2 or ay2 < by1 or ay1 > by2)


def _place_passport_on_page(
    page: Image.Image,
    passport_path: Path,
    csv_index: int,
    csv_rows,
) -> bool:
    """Paste a single passport onto *page* including the ID text.

    Returns True on success, False if text could not be placed without
    overlapping other elements (caller may retry with a new random layout).
    """
    boxes: List[Tuple[int, int, int, int]] = []  # track occupied rectangles

    # Load & scale the passport image
    passport = Image.open(passport_path).convert("RGBA")
    scale = random.uniform(SCALE_MIN, SCALE_MAX)
    passport = passport.resize((int(passport.width * scale), int(passport.height * scale)), Image.LANCZOS)

    # Try random positions up to N times to avoid overlap / margins
    for _ in range(50):
        x = random.randint(MARGIN, PAGE_WIDTH - passport.width - MARGIN)
        y = random.randint(MARGIN, PAGE_HEIGHT - passport.height - MARGIN)
        rect = (x, y, x + passport.width, y + passport.height)
        if not boxes or all(not _overlap(rect, b) for b in boxes):
            break
    else:
        return False  # could not find placement

    boxes.append(rect)
    page.paste(passport, (x, y), passport)

    # ---------------------------------------------------------------------
    # Render AccountID and HealthBenefitID (if present) near the passport.
    # ---------------------------------------------------------------------
    if csv_index < len(csv_rows):
        row = csv_rows[csv_index]
        aid = str(row.get("AccountID", "")).strip()
        hid = str(row.get("HealthBenefitID", "")).strip()

        if aid or hid:
            font = _load_font(ID_FONT_SIZE)
            text_imgs = [_render_text(t, font) for t in (aid, hid) if t]
            total_h = sum(img.height for img in text_imgs) + 4 * (len(text_imgs) - 1)

            # Where can we place? (above or below passport)
            above_ok = (y - 10 - total_h) >= MARGIN
            below_ok = (y + passport.height + 10 + total_h) <= (PAGE_HEIGHT - MARGIN)
            if not above_ok and not below_ok:
                return False  # nowhere to place IDs without clipping

            place_above = above_ok if (above_ok and not below_ok) else (below_ok if (below_ok and not above_ok) else random.choice((True, False)))
            align      = random.choice((0, 1, 2))  # left, centre, right within passport width

            base_y = (y - 10 - total_h) if place_above else (y + passport.height + 10)

            for img in text_imgs:
                if align == 0:
                    tx = x
                elif align == 1:
                    tx = x + (passport.width - img.width) // 2
                else:
                    tx = x + passport.width - img.width

                # Keep inside page margins
                tx = max(MARGIN, min(tx, PAGE_WIDTH - MARGIN - img.width))

                id_rect = (tx, base_y, tx + img.width, base_y + img.height)
                if any(_overlap(id_rect, b) for b in boxes):
                    return False  # overlaps existing items

                page.paste(img, (tx, base_y), img)
                boxes.append(id_rect)
                base_y += img.height + 4

    return True


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def assemble(cards_dir: str, out_dir: str,
            num_pages: Optional[int] = None,
            grayscale: bool = True,
            passport_type: str = "us"):
    """Assemble one passport per sheet.

    Parameters
    ----------
    cards_dir : str
        Directory containing filled-in passport PNGs.
    out_dir : str
        Where to save the finished sheet PNGs.
    num_pages : int | None
        How many sheets to create (defaults to all passports found).
    grayscale : bool
        Convert sheets to 8-bit greyscale.
    passport_type : {"us", "india"}
        Filter input PNGs by filename prefix so the same folder can hold
        both U.S. and Indian passport images.
    """

    prefix_map = {"us": "uspassport", "india": "indiapassport"}
    prefix = prefix_map.get(passport_type.lower())
    if prefix is None:
        raise ValueError("passport_type must be 'us' or 'india'")

    passports = sorted(Path(cards_dir).glob(f"{prefix}*.png"))
    if not passports:
        print(f"No passport PNGs found in {cards_dir}")
        return

    if num_pages is not None:
        passports = passports[: num_pages]

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # Load CSV once – we rely on row index parity between generated passports and CSV rows.
    import pandas as pd
    csv_rows = pd.read_csv(CSV_FILE).to_dict("records")

    for idx, passport_path in enumerate(passports, start=1):
        # Try several random layouts in case ID placement fails
        for _ in range(20):
            page = _load_blank_page()
            success = _place_passport_on_page(page, passport_path, idx - 1, csv_rows)
            if success:
                break
        else:
            print(f"WARNING: could not place IDs for page {idx}")
            page = _load_blank_page()
            _place_passport_on_page(page, passport_path, idx - 1, csv_rows)

        page_to_save = page.convert("L") if grayscale else page
        out_path = Path(out_dir) / f"{passport_type}_passport_sheet{idx}.png"
        page_to_save.save(out_path, "PNG")
        print(f"→ wrote {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Compose filled-in passport sheets (one per page).")
    ap.add_argument("--type", choices=["us", "india"], default="us", help="Which passport images to use (filename prefix)")
    ap.add_argument("--cards", default="output/passports", help="Directory containing generated passport PNGs")
    ap.add_argument("--out",   default="output/passport_sheets", help="Destination directory for sheets")
    ap.add_argument("-n", "--pages", type=int, default=None, help="Number of pages to generate (defaults to all found passports)")
    ap.add_argument("--color", action="store_true", help="Keep sheets in colour (default greyscale)")

    args = ap.parse_args()
    assemble(args.cards, args.out, args.pages, grayscale=not args.color, passport_type=args.type) 