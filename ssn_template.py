import os, random, pathlib
from typing import Dict, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import SSN_TEMPLATE_PATH, HANDWRITING_FONT, TEMPLATE_DIR, FONTS_DIR, SIGNATURE_FONT

DEFAULT_COORDS: Dict[str, Tuple[int, int]] = {
    "SSN": ("center", 125),
    "FullName": ("center", 195),
    "Signature": ("center", 260),
}

# field boxes for no overlap
FIELD_BOXES: Dict[str, Tuple[int, int]] = {
    "SSN": (300, None),
    "FullName": (300, None),
    "Signature": (300, None),
}

# font parameters
DEFAULT_FONT_SIZE = 42
DEFAULT_FONT_COLOR = (0, 0, 0)  # black handwriting ink


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Return a FreeType font object for *path*; raise if missing."""
    font_path = pathlib.Path(path)
    if not font_path.exists():
        raise FileNotFoundError(f"Font not found: {font_path}")
    return ImageFont.truetype(str(font_path), size)


def _render_text(text: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    """Render *text* onto a transparent RGBA image without rotation."""
    asc, desc = font.getmetrics()

    # measure text size using textbbox (compatible with Pillow)
    dummy = Image.new("RGB", (1, 1))
    d = ImageDraw.Draw(dummy)
    bbox = d.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    img = Image.new("RGBA", (w + 10, h + desc + 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), text, font=font, fill=DEFAULT_FONT_COLOR)

    return img

# public api
def fill_ssn_template(raw_row: Dict[str, str], out_path: str, coords: Dict[str, Tuple[int, int]] = None,
                       font_size: int = DEFAULT_FONT_SIZE):

    # overlay row values onto the ssn_png template
    coords = coords or DEFAULT_COORDS

    # load base template image
    template_path = pathlib.Path(SSN_TEMPLATE_PATH)
    if not template_path.exists():
        raise FileNotFoundError(f"SSN template PNG not found at {template_path}.")

    base = Image.open(template_path).convert("RGBA")
    body_font = _load_font(HANDWRITING_FONT, font_size)
    sig_font = _load_font(SIGNATURE_FONT, int(font_size * 0.8))

    # build derived values the template expects
    row = dict(raw_row)
    # fullname combines first / middle initial / last
    mi = row.get("MiddleInitial", "").strip()
    mi_part = f" {mi}." if mi else ""
    row["FullName"] = f"{row.get('FirstName', '')}{mi_part} {row.get('LastName', '')}".strip()
    row["Signature"] = row["FullName"]

    sig_bottom = None 

    for field, (x, y) in coords.items():
        value = str(row.get(field, "")).strip()
        if not value:
            continue

        # pick base font size multiplier
        if field == "Signature":
            base_multiplier = 0.7
            font_path = SIGNATURE_FONT
        elif field == "FullName":
            base_multiplier = 0.8
            font_path = HANDWRITING_FONT
        elif field == "SSN":
            base_multiplier = 0.9
            font_path = HANDWRITING_FONT
        else:
            base_multiplier = 1.0
            font_path = HANDWRITING_FONT

        size_px = int(font_size * base_multiplier)

        # auto-shrink so text fits inside its predefined box width
        if isinstance(x, str):  # 'center' placeholder
            box_default = base.width - 40   # entire card minus 20-px margins
        else:
            box_default = base.width - x - 20
        box_width, _ = FIELD_BOXES.get(field, (box_default, None))

        while size_px > 10:
            font_to_use = _load_font(font_path, size_px)
            text_img = _render_text(value, font_to_use)
            if text_img.width <= box_width:
                break
            size_px = max(10, int(size_px * 0.9))  # shrink 10 % and retry

        centered = False
        if x == "center":
            x = (base.width - text_img.width) // 2
            centered = True

        if centered:
            x += 20 

        base.paste(text_img, (int(x), int(y)), text_img)

        # capture bottom of signature for potential use later
        if field == "Signature":
            sig_bottom = y + text_img.height

    # ensure output directory exists
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, format="PNG")

    return out_path 