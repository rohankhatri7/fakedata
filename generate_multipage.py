# Generate multi-page documents combining SSN and passport pages.
from __future__ import annotations

import argparse, shutil, tempfile
from pathlib import Path
from typing import List, Tuple

from PIL import Image

# local imports (assembly helpers)
import assemble_ssn # ssn pages
import assemble_passport_pages # passport pages


def _collect_card_images(prefix: str, count: int, source_dir: Path) -> List[Path]:
    images = sorted(source_dir.glob(f"{prefix}*.png"))
    if len(images) < count:
        raise ValueError(f"Not enough {prefix} card images in {source_dir} (need {count}, have {len(images)})")
    return images[:count]

def generate(sequence: List[Tuple[str, int]], outfile: str, grayscale: bool = True):
    """Generate combined PDF per *sequence* list and write to *outfile*.

    Parameters
    ----------
    sequence : list of (form_type, count)
        form_type is one of "ssn", "us", "india".
    outfile : str
        Destination PDF path.
    """
    tmp_root = Path(tempfile.mkdtemp(prefix="multi_doc_"))
    final_pages: List[Path] = []

    try:
        # ensure output sub-dirs
        ssn_cards_dir    = Path("output/ssn_docs")
        passports_dir    = Path("output/passports")
        paystub_dir      = Path("output/paystubs")

        # keep counters to know which images have already been used
        used_counters = {
            "ssn": 0,
            "us": 0,
            "india": 0,
            "paystub": 0,
        }

        for form_type, count in sequence:
            if count <= 0:
                continue

            if form_type == "ssn":
                cards = _collect_card_images("ssn", count, ssn_cards_dir)[used_counters["ssn"]: used_counters["ssn"] + count]
                used_counters["ssn"] += count

                # temporary directory to hold pages for this group
                out_dir = tmp_root / f"ssn_sheets_{len(final_pages)}"
                out_dir.mkdir(parents=True, exist_ok=True)
                # assemble pages (one card per page)
                assemble_ssn.assemble(str(ssn_cards_dir), str(out_dir), num_pages=count, grayscale=grayscale)
                final_pages.extend(sorted(out_dir.glob("*.png")))

            elif form_type == "us":
                cards = _collect_card_images("uspassport", count, passports_dir)[used_counters["us"]: used_counters["us"] + count]
                used_counters["us"] += count

                # copy selected cards to temp dir so assembler only sees these
                with tempfile.TemporaryDirectory(dir=tmp_root) as td:
                    td_path = Path(td)
                    for c in cards:
                        shutil.copy(c, td_path / c.name)

                    out_dir = tmp_root / f"us_passport_sheets_{len(final_pages)}"
                    out_dir.mkdir(parents=True, exist_ok=True)
                    assemble_passport_pages.assemble(
                        str(td_path),
                        str(out_dir),
                        num_pages=count,
                        grayscale=grayscale,
                        passport_type="us",
                    )
                    final_pages.extend(sorted(out_dir.glob("*.png")))

            elif form_type == "india":
                cards = _collect_card_images("indiapassport", count, passports_dir)[used_counters["india"]: used_counters["india"] + count]
                used_counters["india"] += count

                with tempfile.TemporaryDirectory(dir=tmp_root) as td:
                    td_path = Path(td)
                    for c in cards:
                        shutil.copy(c, td_path / c.name)

                    out_dir = tmp_root / f"india_passport_sheets_{len(final_pages)}"
                    out_dir.mkdir(parents=True, exist_ok=True)
                    assemble_passport_pages.assemble(
                        str(td_path),
                        str(out_dir),
                        num_pages=count,
                        grayscale=grayscale,
                        passport_type="india",
                    )
                    final_pages.extend(sorted(out_dir.glob("*.png")))

            elif form_type in ("paystub", "stub"):
                cards = _collect_card_images("paystub", count, paystub_dir)[used_counters["paystub"]: used_counters["paystub"] + count]
                used_counters["paystub"] += count

                out_dir = tmp_root / f"paystub_pages_{len(final_pages)}"
                out_dir.mkdir(parents=True, exist_ok=True)
                # Copy selected cards to ensure we have fresh mtimes for ordering
                for c in cards:
                    dest = out_dir / c.name
                    shutil.copy(c, dest)
                    final_pages.append(dest)

            else:
                raise ValueError(f"Unknown form type: {form_type}")

        if not final_pages:
            print("Nothing generated – check inputs.")
            return

        # sort final_pages by modification time to preserve generation order
        final_pages = sorted(final_pages, key=lambda p: p.stat().st_mtime)

        # Build PDF
        pil_pages = [Image.open(p).convert("L" if grayscale else "RGB") for p in final_pages]
        first, rest = pil_pages[0], pil_pages[1:]
        pdf_path = Path(outfile).expanduser().resolve()
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        first.save(pdf_path, save_all=True, append_images=rest)
        print(f"Multi-page document written → {pdf_path} ({len(final_pages)} pages)")

    finally:
        # remove temporary dirs 
        shutil.rmtree(tmp_root, ignore_errors=True)



def _parse_sequence(seq_str: str) -> List[Tuple[str, int]]:
    parts = [p.strip() for p in seq_str.split(',') if p.strip()]
    seq: List[Tuple[str, int]] = []
    for part in parts:
        if ':' not in part:
            raise argparse.ArgumentTypeError("Sequence items must be in form type:count")
        t, n = part.split(':', 1)
        try:
            n_int = int(n)
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid count in '{part}'")
        seq.append((t.lower(), n_int))
    return seq


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate a multi-page PDF from SSN, passport, and pay-stub sheets.")
    ap.add_argument("--sequence", required=True, help="Comma-separated list form:count, e.g. 'ssn:5,us:3,paystub:2'", type=_parse_sequence)
    ap.add_argument("--outfile", required=True, help="Output PDF path")
    args = ap.parse_args()

    generate(args.sequence, args.outfile, grayscale=True) 