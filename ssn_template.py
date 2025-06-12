import os, random, pathlib
from typing import Dict, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import SSN_TEMPLATE_PATH, HANDWRITING_FONT, TEMPLATE_DIR, FONTS_DIR, SIGNATURE_FONT

# Updated for 570×360 px template
DEFAULT_COORDS: Dict[str, Tuple[int, int]] = {
    "SSN": (170, 110),        # SSN line (shift a bit left)
    "FullName": (180, 180),   # Name line (shift a bit left)
    "Signature": (220, 260),  # Signature line (slightly left)
    "DOB": (380, 290),        # DOB slightly up/left
}

# Width (and optional height) each field may occupy before font is shrunk
FIELD_BOXES: Dict[str, Tuple[int, int]] = {
    #  (max_width_px, max_height_px) – height is advisory (can be None)
    "SSN": (300, None),
    "FullName": (300, None),
    "Signature": (300, None),
    "DOB": (140, None),
}

# Font parameters
DEFAULT_FONT_SIZE = 42  # tweak for your template DPI
DEFAULT_FONT_COLOR = (0, 0, 0)  # black handwriting ink

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Return a FreeType font object for *path*; raise if missing."""
    font_path = pathlib.Path(path)
    if not font_path.exists():
        raise FileNotFoundError(f"Font not found: {font_path}")
    return ImageFont.truetype(str(font_path), size)


def _render_text(text: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    """Render *text* onto a transparent RGBA image and return it (with random slant)."""
    asc, desc = font.getmetrics()
    # measure text size using textbbox (compatible with Pillow ≥10)
    dummy = Image.new("RGB", (1, 1))
    d = ImageDraw.Draw(dummy)
    bbox = d.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    img = Image.new("RGBA", (w + 10, h + desc + 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), text, font=font, fill=DEFAULT_FONT_COLOR)

    # Apply small random rotation to simulate human writing slant
    angle = random.uniform(-4, 4)  # degrees
    img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    return img


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fill_ssn_template(raw_row: Dict[str, str], out_path: str, coords: Dict[str, Tuple[int, int]] = None,
                       font_size: int = DEFAULT_FONT_SIZE):
    """Overlay *row* values onto the SSN PNG template and write *out_path*.

    Only the fields referenced in *coords* are used.
    """
    coords = coords or DEFAULT_COORDS

    # Load base template image
    template_path = pathlib.Path(SSN_TEMPLATE_PATH)
    if not template_path.exists():
        raise FileNotFoundError(f"SSN template PNG not found at {template_path}.")

    base = Image.open(template_path).convert("RGBA")
    body_font = _load_font(HANDWRITING_FONT, font_size)
    sig_font = _load_font(SIGNATURE_FONT, int(font_size * 0.8))

    # Build derived values the template expects
    row = dict(raw_row)  # make a copy we can extend
    # FullName combines first / middle initial (if any) / last
    mi = row.get("MiddleInitial", "").strip()
    mi_part = f" {mi}." if mi else ""
    row["FullName"] = f"{row.get('FirstName', '')}{mi_part} {row.get('LastName', '')}".strip()
    row["Signature"] = row["FullName"]  # simple assumption; customise if needed

    sig_bottom = None  # track bottom of signature for overlap check

    for field, (x, y) in coords.items():
        value = str(row.get(field, "")).strip()
        if not value:
            continue
        # pick base font size multiplier
        if field == "Signature":
            base_multiplier = 0.7
            font_path = SIGNATURE_FONT
        elif field == "DOB":
            base_multiplier = 0.4
            font_path = HANDWRITING_FONT
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
        box_width, _ = FIELD_BOXES.get(field, (base.width - x - 20, None))

        while size_px > 10:
            font_to_use = _load_font(font_path, size_px)
            text_img = _render_text(value, font_to_use)
            if text_img.width <= box_width:
                break
            size_px = max(10, int(size_px * 0.9))  # shrink 10 % and retry

        # If x is "center", override to horizontally center the text
        if x == "center":
            x = (base.width - text_img.width) // 2

        # For DOB, if it would overlap signature, push it down
        if field == "DOB" and sig_bottom is not None:
            if y < sig_bottom + 5:
                y = sig_bottom + 10

        # paste using alpha mask to preserve transparency
        base.paste(text_img, (int(x), int(y)), text_img)

        # record signature bottom for collision avoidance
        if field == "Signature":
            sig_bottom = y + text_img.height

    # Ensure output directory exists
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, format="PNG")

    return out_path 