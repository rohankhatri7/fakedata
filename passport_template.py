from __future__ import annotations
import pathlib, datetime
from typing import Dict, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import TEMPLATE_DIR, FONTS_DIR, OPENSANS_FONT, SIGNATURE_FONT

PASSPORT_TEMPLATE_PATH = TEMPLATE_DIR / "cleanpassport.png"

DEFAULT_COORDS = {
    "Signature":    (380,  860),  
    "Surname":      (500, 1220),
    "GivenNames":   (500, 1290),
    "Nationality":  (500, 1510),
    "DOB":          (500, 1430),
    "PlaceOfBirth": (500, 1680),
    "Sex":          (1240, 1509),  # Fine adjustment up and left
}

FIELD_BOXES = {
    "Surname":       650,
    "GivenNames":    650,
    "Nationality":   650,
    "PlaceOfBirth":  650,
    "Sex":           200,
    "DOB":           320,
}

BASE_FONT_SIZE = 28
SIG_FONT_SIZE  = 60
SEX_FONT_SIZE  = 40

FONT_COLOR = (0, 0, 0)


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def _render(text: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    dummy = Image.new("RGB", (1, 1))
    d = ImageDraw.Draw(dummy)
    w, h = d.textbbox((0, 0), text, font=font)[2:]
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((0, 0), text, font=font, fill=FONT_COLOR)
    return img


def fill_passport_template(raw: Dict[str, str], out_path: str,
                           coords: Dict[str, Tuple[int, int]] = None,
                           font_size: int = BASE_FONT_SIZE) -> str:
    #paint values on template image
    coords = coords or DEFAULT_COORDS
    base = Image.open(PASSPORT_TEMPLATE_PATH).convert("RGBA")

    surname = raw.get("LastName", "").upper()
    mi = raw.get("MiddleInitial", "").strip()
    given = f"{raw.get('FirstName','')}{f' {mi}.' if mi else ''}".upper()
    fullname = f"{given} {surname}".strip()
    dob_dt = datetime.datetime.strptime(raw["DOB"], "%m/%d/%Y")
    dob_str = dob_dt.strftime("%d %b %Y").upper()
    sex = (raw.get("Gender", "")).upper()

    fields = {
        # render order (top-to-bottom)
        "Signature":     fullname,
        "Surname":       surname,
        "GivenNames":    fullname,
        "Nationality":   "UNITED STATES OF AMERICA",
        "DOB":           dob_str,
        "Sex":           sex,
    }

    for key, text in fields.items():
        x, y = coords[key]
        font_path = SIGNATURE_FONT if key == "Signature" else OPENSANS_FONT
        # Larger font for Signature and Sex fields
        if key == "Signature":
            size = SIG_FONT_SIZE
        elif key == "Sex":
            size = SEX_FONT_SIZE
        else:
            size = BASE_FONT_SIZE
        max_w     = FIELD_BOXES.get(key, base.width)

        # auto-shrink loop (unchanged)
        while size >= 10:
            font = _load_font(font_path, size)
            img  = _render(text, font)
            if img.width <= max_w:
                break
            size = int(size * 0.9)

        base.paste(img, (x, y), img)

    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, "PNG")
    return out_path 