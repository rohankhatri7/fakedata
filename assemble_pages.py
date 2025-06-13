# paste SSN pngs onto blank template
# fixed where script reruns in giveup branch to account for all ids
from pathlib import Path
import random, argparse
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont

from config import (
    BLANK_PAGE_PATH, PAGE_WIDTH, PAGE_HEIGHT,
    CSV_FILE, HANDWRITING_FONT
)

MARGIN = 50 
MAX_PER_PAGE = 5
# Cards will now be 30–60 % larger than original size
SCALE_MIN, SCALE_MAX = 1.3, 1.6


def _load_blank_page() -> Image.Image:
    template = Path(BLANK_PAGE_PATH)
    if template.exists():
        page = Image.open(template).convert("RGB")
        return page.resize((PAGE_WIDTH, PAGE_HEIGHT), Image.LANCZOS)
    # fallback – plain white sheet
    return Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(HANDWRITING_FONT), size)


def _render_text(text: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    draw_dummy = ImageDraw.Draw(Image.new("RGB", (1,1)))
    w,h = draw_dummy.textbbox((0,0), text, font=font)[2:4]
    img = Image.new("RGBA", (w,h), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.text((0,0), text, font=font, fill=(0,0,0))
    return img


def _place_cards_on_page(page: Image.Image, card_paths: List[Path], start_index: int, csv_rows) -> bool:
    boxes: List[Tuple[int, int, int, int]] = []
    for idx, card_path in enumerate(card_paths, start=start_index):
        card = Image.open(card_path).convert("RGBA")
        # Random scale
        scale = random.uniform(SCALE_MIN, SCALE_MAX)
        card = card.resize((int(card.width * scale), int(card.height * scale)), Image.LANCZOS)

        # find position with minimal overlap attempts
        for _ in range(50):
            x = random.randint(MARGIN, PAGE_WIDTH - card.width - MARGIN)
            y = random.randint(MARGIN, PAGE_HEIGHT - card.height - MARGIN)
            rect = (x, y, x + card.width, y + card.height)
            if all(not _overlap(rect, b) for b in boxes):
                break
        boxes.append(rect)
        page.paste(card, (x, y), card)

        # --- render AccountID & HealthBenefitID near the card ------------
        if idx < len(csv_rows):
            row = csv_rows[idx]
            aid = row.get("AccountID", "")
            hid = row.get("HealthBenefitID", "")

            if aid or hid:
                font = _load_font(32)
                text_lines = [aid, hid] if hid else [aid]
                offset_y = y + card.height + 10
                for line in text_lines:
                    if not line:
                        continue
                    text_img = _render_text(line, font)

                    # random horizontal placement: 0=left,1=center,2=right relative to card
                    align = random.choice((0,1,2))
                    if align == 0:  # left
                        tx = x
                    elif align == 1:  # centre
                        tx = x + (card.width - text_img.width)//2
                    else:  # right aligned with card right edge
                        tx = x + card.width - text_img.width

                    ty = offset_y
                    # decide whether to place above or below the card
                    place_above = random.choice((True, False))
                    if place_above:
                        offset_y = y - text_img.height - 10
                    else:
                        offset_y = y + card.height + 10

                    # ensure no overlap with existing
                    id_rect = (tx, ty, tx + text_img.width, ty + text_img.height)
                    if any(_overlap(id_rect, b) for b in boxes):
                        # if overlaps, try below card instead
                        if place_above:
                            ty = y + card.height + 10
                            id_rect = (tx, ty, tx + text_img.width, ty + text_img.height)
                            if any(_overlap(id_rect, b) for b in boxes):
                                return False  # fail placement
                        else:
                            return False

                    page.paste(text_img, (tx, ty), text_img)
                    boxes.append(id_rect)

                    offset_y = ty + text_img.height + 4 if not place_above else ty - text_img.height - 4

    return True  # all ids placed without overlap


def _overlap(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 < bx1 or ax1 > bx2 or ay2 < by1 or ay1 > by2)


def assemble(cards_dir: str, out_dir: str, per_page: int = MAX_PER_PAGE):
    cards = sorted(Path(cards_dir).glob("*.png"))
    if not cards:
        print(f"No card PNGs found in {cards_dir}")
        return
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # load CSV rows
    import pandas as pd
    csv_rows = pd.read_csv(CSV_FILE).to_dict("records")

    page_num = 1
    for i in range(0, len(cards), per_page):
        batch = cards[i : i + per_page]

        for attempt in range(20):  # up to 20 tries to place without collisions
            page = _load_blank_page()
            if _place_cards_on_page(page, batch, start_index=i, csv_rows=csv_rows):
                break
        else:
            print(f"WARNING: could not place all IDs for page {page_num}")

        out_path = Path(out_dir) / f"sheet_{page_num:03d}.png"
        page.save(out_path, "PNG")
        print(f"→ wrote {out_path}")
        page_num += 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Assemble SSN card PNGs onto white sheets.")
    ap.add_argument("--cards", default="output/ssn_docs", help="Directory holding individual SSN card PNGs")
    ap.add_argument("--out", default="output/sheets", help="Directory to write composite sheets")
    ap.add_argument("--per", type=int, default=MAX_PER_PAGE, help="Max cards per sheet (default 5)")
    args = ap.parse_args()

    assemble(args.cards, args.out, args.per) 