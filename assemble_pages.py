# paste SSN pngs onto blank template
# fixed where script reruns in giveup branch to account for all ids
from pathlib import Path
import random, argparse
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

from config import (
    BLANK_PAGE_PATH, PAGE_WIDTH, PAGE_HEIGHT,
    CSV_FILE, HANDWRITING_FONT
)

MARGIN = 50 
SCALE_MIN, SCALE_MAX = 1.8, 2.2
ID_FONT_SIZE = 48


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
        # random scale
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

        # render AccountID & HealthBenefitID near the card
        if idx < len(csv_rows):
            row = csv_rows[idx]
            aid = row.get("AccountID", "")
            hid = row.get("HealthBenefitID", "")

            if aid or hid:
                font = _load_font(ID_FONT_SIZE)
                text_lines = [aid, hid] if hid else [aid]

                # pre-render all lines so we know their dimensions
                text_imgs = [_render_text(t, font) for t in text_lines if t]
                total_h = sum(img.height for img in text_imgs) + 4 * (len(text_imgs) - 1)

                # determine whether we can place above/below
                above_ok = (y - 10 - total_h) >= MARGIN
                below_ok = (y + card.height + 10 + total_h) <= (PAGE_HEIGHT - MARGIN)

                if not above_ok and not below_ok:
                    # nowhere to put the IDs -> skip this card
                    continue

                # choose placement randomly but constrained to valid options
                if above_ok and below_ok:
                    place_above = random.choice((True, False))
                else:
                    place_above = above_ok

                # horizontal alignment
                align = random.choice((0, 1, 2))

                if place_above:
                    base_y = y - 10 - total_h
                else:
                    base_y = y + card.height + 10

                for img in text_imgs:
                    if align == 0:
                        tx = x
                    elif align == 1:
                        tx = x + (card.width - img.width) // 2
                    else:
                        tx = x + card.width - img.width

                    # text never runs outside the sheet
                    tx = max(MARGIN, min(tx, PAGE_WIDTH - MARGIN - img.width))

                    ty = base_y

                    id_rect = (tx, ty, tx + img.width, ty + img.height)

                    # fail placement if it overlaps an existing box (card or text)
                    if any(_overlap(id_rect, b) for b in boxes):
                        return False

                    page.paste(img, (tx, ty), img)
                    boxes.append(id_rect)

                    base_y += img.height + 4

    return True


def _overlap(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 < bx1 or ax1 > bx2 or ay2 < by1 or ay1 > by2)


def assemble(cards_dir: str, out_dir: str, num_pages: Optional[int] = None):
    # one SSN per sheet, if not specified, defaults to number in ssn_docs
    cards = sorted(Path(cards_dir).glob("*.png"))
    if not cards:
        print(f"No card PNGs found in {cards_dir}")
        return

    # limit to the requested number of pages
    if num_pages is not None:
        cards = cards[: num_pages]

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # load CSV rows once
    import pandas as pd
    csv_rows = pd.read_csv(CSV_FILE).to_dict("records")

    page_num = 1
    for i, card_path in enumerate(cards):
        batch = [card_path]

        for _ in range(20): #try up to 20 times before failing
            page = _load_blank_page()
            if _place_cards_on_page(page, batch, start_index=i, csv_rows=csv_rows):
                break
        else:
            print(f"WARNING: could not place IDs for page {page_num}")

        out_path = Path(out_dir) / f"sheet{page_num}.png"
        page.save(out_path, "PNG")
        print(f"→ wrote {out_path}")
        page_num += 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Assemble composite sheets – *one* SSN card per sheet.")
    ap.add_argument("--cards", default="output/ssn_docs", help="Directory holding individual SSN card PNGs")
    ap.add_argument("--out", default="output/sheets", help="Directory to write composite sheets")
    ap.add_argument("-n", "--pages", type=int, default=None, help="Number of pages (and therefore cards) to generate – defaults to all found cards")
    args = ap.parse_args()

    assemble(args.cards, args.out, args.pages) 