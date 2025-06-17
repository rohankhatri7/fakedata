# use openCV inpaint to remove white regions from template image
import argparse, os
from pathlib import Path
import cv2
import numpy as np


def inpaint_white_regions(
    src_path: str,
    dst_path: str | None = None,
    threshold: int = 245,
    radius: int = 3,
    method: str = "ns",
    dark_threshold: int | None = None,
) -> str:
    """Remove nearly-white rectangles by in-painting.

    Parameters
    ----------
    src_path : str
        Source image path.
    dst_path : str | None
        Destination (defaults to <src>_clean.png).
    threshold : int
        Pixel values >= threshold are considered white (0-255).
    radius : int
        In-painting radius in pixels.
    method : str
        Either "ns" (Navier-Stokes) or "telea".
    dark_threshold : int | None
        Pixels <= this value are treated as dark mask (0-255). If omitted, dark pixels are ignored.
    Returns
    -------
    str
        The path written.
    """
    img = cv2.imread(src_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(src_path)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # mask bright pixels
    _, mask_bright = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

    mask = mask_bright

    # optionally add very dark areas to mask (signature bar etc.)
    if dark_threshold is not None:
        _, mask_dark = cv2.threshold(gray, dark_threshold, 255, cv2.THRESH_BINARY_INV)
        mask = cv2.bitwise_or(mask, mask_dark)

    # clean edges a bit
    mask = cv2.medianBlur(mask, 5)

    flags = cv2.INPAINT_NS if method.lower().startswith("n") else cv2.INPAINT_TELEA
    cleaned = cv2.inpaint(img, mask, radius, flags)

    # default destination path
    if dst_path is None:
        root, ext = os.path.splitext(src_path)
        dst_path = f"{root}_clean{ext}"

    cv2.imwrite(dst_path, cleaned)
    print(f"✅ In-painted template saved → {dst_path}")
    return dst_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="In-paint near-white regions in a template image so the background looks continuous.")
    ap.add_argument("source", nargs="?", default="templates/passport.png", help="Input image path")
    ap.add_argument("dest", nargs="?", default=None, help="Output path")
    ap.add_argument("--threshold", type=int, default=245, help="Threshhold for white detection (0-255)")
    ap.add_argument("--radius", type=int, default=3, help="In-painting radius in pixels")
    ap.add_argument("--method", choices=["ns", "telea"], default="ns", help="In-painting algorithm: ns (Navier-Stokes) or telea")
    ap.add_argument("--dark-threshold", type=int, default=None, help="Pixels <= this value are treated as dark mask (0-255). If omitted, dark pixels are ignored.")
    args = ap.parse_args()

    inpaint_white_regions(
        args.source,
        args.dest,
        args.threshold,
        args.radius,
        args.method,
        args.dark_threshold,
    ) 