from __future__ import annotations
import pathlib, datetime, random
from typing import Dict, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import TEMPLATE_DIR, OPENSANS_FONT, SIGNATURE_FONT

# Use the cleaned template (without white boxes) generated via cleanup_template.py
# This ensures new documents blend seamlessly with the background.
INDIA_PASSPORT_TEMPLATE_PATH = TEMPLATE_DIR / "cleanindiapassport.png"

# Coordinates scaled down from US template to fit 960x1363 canvas
DEFAULT_COORDS: Dict[str, Tuple[int, int]] = {
    "PassportNumber":(760, 790),  # further down and right
    "Surname":       (350, 822),
    "GivenNames":    (350, 890),
    "DOB":           (358, 945),
    "Sex":           (604, 945),
    "PlaceOfBirth":  (350, 1003),
    "PlaceOfIssue":  (350, 1070),
    "DateOfIssue":   (360, 1132),
    "DateOfExpiry":  (680, 1130),
}

# Maximum widths for text to auto-shrink within each field box
FIELD_BOXES: Dict[str, int] = {
    "Surname":       430,
    "GivenNames":    430,
    "DOB":           210,
    "Sex":           140,
    "PlaceOfBirth":  430,
    "PlaceOfIssue":  430,
    "DateOfIssue":   200,
    "PassportNumber":200,
    "DateOfExpiry":  200,
}

BASE_FONT_SIZE = 28
SEX_FONT_SIZE  = 24
FIELD_FONT_SIZES = {
    "Surname":      20,
    "GivenNames":   18,
    "DOB":          20,
    "PlaceOfBirth": 22,
    "PlaceOfIssue": 22,
    "DateOfIssue":  22,
    "DateOfExpiry": 22,
    "PassportNumber": 24,
    "Sex":          SEX_FONT_SIZE,
}
FONT_COLOR     = (0, 0, 0)


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def _render(text: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    dummy = Image.new("RGB", (1, 1))
    d = ImageDraw.Draw(dummy)
    w, h = d.textbbox((0, 0), text, font=font)[2:]
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((0, 0), text, font=font, fill=FONT_COLOR)
    return img


def fill_india_passport_template(raw: Dict[str, str], out_path: str,
                                 coords: Dict[str, Tuple[int, int]] = None,
                                 font_size: int = BASE_FONT_SIZE) -> str:
    """Populate the Indian passport template PNG with row data.

    Parameters
    ----------
    raw : Dict[str, str]
        Row dictionary from CSV/dataframe.
    out_path : str
        Destination path for generated PNG.
    coords : optional Dict[str, Tuple[int,int]]
        Override default coordinates.
    font_size : int
        Base font size (auto-shrinks to fit boxes).
    """
    coords = coords or DEFAULT_COORDS
    base   = Image.open(INDIA_PASSPORT_TEMPLATE_PATH).convert("RGBA")

    surname = raw.get("LastName", "").upper()
    mi      = raw.get("MiddleInitial", "").strip()
    given   = f"{raw.get('FirstName','')}{f' {mi}.' if mi else ''}".upper()
    fullname = f"{given} {surname}".strip()

    # --- Dates ---------------------------------------------------------------
    dob_dt  = datetime.datetime.strptime(raw["DOB"], "%m/%d/%Y")
    dob_str = dob_dt.strftime("%d %b %Y").upper()

    # Sex
    sex = (raw.get("Gender", "")).upper()

    # Place of birth / issue (defaults)
    pob = raw.get("PlaceOfBirth", "INDIA").upper() or "INDIA"
    poi = raw.get("PlaceOfIssue", "INDIA").upper() or "INDIA"

    # Issue / Expire dates – same logic as U.S.
    today      = datetime.date.today()
    age_years  = (today - dob_dt.date()).days // 365
    validity   = 5 if age_years < 16 else 10

    latest_issue_year   = today.year - 1
    earliest_issue_year = max(dob_dt.year + 16, latest_issue_year - validity)
    issue_year          = random.randint(earliest_issue_year, latest_issue_year)
    issue_month         = random.randint(1, 12)
    issue_day           = random.randint(1, 28)
    issue_dt            = datetime.date(issue_year, issue_month, issue_day)

    expiry_dt           = issue_dt.replace(year=issue_dt.year + validity)

    issue_str  = issue_dt.strftime("%d %b %Y").upper()
    expiry_str = expiry_dt.strftime("%d %b %Y").upper()

    # Generate Indian passport number: 1 letter + 7 digits
    passport_num = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + f"{random.randint(0, 9999999):07d}"

    # --- Field mapping -------------------------------------------------------
    fields = {
        "Surname":       surname,
        "GivenNames":    fullname,
        "DOB":           dob_str,
        "Sex":           sex,
        "PlaceOfBirth":  pob,
        "PlaceOfIssue":  poi,
        "DateOfIssue":   issue_str,
        "DateOfExpiry":  expiry_str,
        "PassportNumber": passport_num,
    }

    # --- Render each field ---------------------------------------------------
    for key, text in fields.items():
        x, y = coords[key]
        font_path = SIGNATURE_FONT if key == "Signature" else OPENSANS_FONT
        size = FIELD_FONT_SIZES.get(key, BASE_FONT_SIZE)

        max_w = FIELD_BOXES.get(key, base.width)

        # Auto-shrink to fit
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