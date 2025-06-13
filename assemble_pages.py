# paste SSN pngs onto blank template
from pathlib import Path
import random, argparse
from typing import List, Tuple
from PIL import Image

from config import BLANK_PAGE_PATH, PAGE_WIDTH, PAGE_HEIGHT

MARGIN = 50 
MAX_PER_PAGE = 5
SCALE_MIN, SCALE_MAX = 0.9, 1.1


def _load_blank_page() -> Image.Image:
    template = Path(BLANK_PAGE_PATH)
    if template.exists():
        page = Image.open(template).convert("RGB")
        return page.resize((PAGE_WIDTH, PAGE_HEIGHT), Image.LANCZOS)
    # fallback – plain white sheet
    return Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")


def _place_cards_on_page(page: Image.Image, card_paths: List[Path]):
    boxes: List[Tuple[int, int, int, int]] = []  # keep used rectangles
    for card_path in card_paths:
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

    page_num = 1
    for i in range(0, len(cards), per_page):
        page = _load_blank_page()
        batch = cards[i : i + per_page]
        _place_cards_on_page(page, batch)
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