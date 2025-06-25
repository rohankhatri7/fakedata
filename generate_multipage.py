# Generate multi-page documents
from __future__ import annotations

import argparse, shutil, tempfile, random
from pathlib import Path
from typing import List, Tuple, Optional

from PIL import Image

# local imports (assembly helpers)
import assemble_ssn # ssn pages
import assemble_passport_pages # passport pages


def _get_paystub_type() -> str:
    #Randomly select between 'adp' and 'paychex' paystub types, falling back to available type if one is empty.
    adp_dir = Path("output/paystubs/adp")
    paychex_dir = Path("output/paystubs/paychex")
    
    adp_count = len(list(adp_dir.glob("*.png"))) if adp_dir.exists() else 0
    paychex_count = len(list(paychex_dir.glob("*.png"))) if paychex_dir.exists() else 0
    
    if adp_count == 0 and paychex_count == 0:
        raise ValueError("No paystub images found in either output/paystubs/adp/ or output/paystubs/paychex/")
    elif adp_count == 0:
        return "paychex"
    elif paychex_count == 0:
        return "adp"
    else:
        return random.choice(["adp", "paychex"])

def _collect_card_images(prefix: str, count: int, source_dir: Path, paystub_type: Optional[str] = None) -> List[Path]:
    if paystub_type == "paychex":
        # For paychex, the prefix is different
        prefix = "paychex"
    elif paystub_type == "adp":
        # ADP files now use 'adp' prefix
        prefix = "adp"
        
    # Look for PNG files with the specified prefix
    images = sorted(source_dir.glob(f"{prefix}*.png"))
    if len(images) < count:
        raise ValueError(f"Not enough {prefix} card images in {source_dir} (need {count}, have {len(images)})")
    return images[:count]

def generate(sequence: List[Tuple[str, int]], outfile: str, grayscale: bool = True):
    #Generate combined PDF per sequence list
    tmp_root = Path(tempfile.mkdtemp(prefix="multi_doc_"))
    final_pages: List[Path] = []

    try:
        # ensure output sub-dirs
        ssn_cards_dir    = Path("output/ssn_docs")
        passports_dir    = Path("output/passports")
        paystub_dir      = Path("output/paystubs/adp")  # Default to ADP paystubs

        # keep counters to know which images have already been used
        used_counters = {
            "ssn": 0,
            "us": 0,
            "india": 0,
            "paystub": 0, # ADP paystubs
            "paychex": 0, # Paychex paystubs
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

            elif form_type in ("paystub", "stub", "paycheck"):
                # Try to collect all needed paystubs, alternating between ADP and Paychex if needed
                remaining = count
                collected = []
                
                while remaining > 0:
                    # Get available counts for each paystub type
                    adp_available = 0
                    paychex_available = 0
                    
                    # Check how many ADP paystubs are available
                    adp_dir = Path("output/paystubs/adp")
                    if adp_dir.exists():
                        adp_files = sorted(adp_dir.glob("adp*.png"))
                        adp_available = len(adp_files) - used_counters["paystub"]
                    
                    # Check how many Paychex paystubs are available
                    paychex_dir = Path("output/paystubs/paychex")
                    if paychex_dir.exists():
                        paychex_files = sorted(paychex_dir.glob("paychex*.png"))
                        paychex_available = len(paychex_files) - used_counters["paychex"]
                    
                    # If no more paystubs available, break the loop
                    if adp_available <= 0 and paychex_available <= 0:
                        break
                    
                    # Choose which type to use (prioritize the type with more available)
                    if adp_available >= paychex_available and adp_available > 0:
                        paystub_type = "adp"
                        counter_key = "paystub"
                        available = adp_available
                        paystub_dir = adp_dir
                    elif paychex_available > 0:
                        paystub_type = "paychex"
                        counter_key = "paychex"
                        available = paychex_available
                        paystub_dir = paychex_dir
                    else:
                        break
                    
                    to_take = min(remaining, available)
                    
                    if to_take > 0:
                        print(f"Using {to_take} {paystub_type.upper()} paystubs from {paystub_dir}")
                        try:
                            if paystub_type == "adp":
                                cards = sorted(paystub_dir.glob("adp*.png"))[used_counters[counter_key]:used_counters[counter_key] + to_take]
                            else:
                                cards = sorted(paystub_dir.glob("paychex*.png"))[used_counters[counter_key]:used_counters[counter_key] + to_take]
                                
                            collected.extend(cards)
                            used_counters[counter_key] += to_take
                            remaining -= to_take
                        except (ValueError, IndexError) as e:
                            print(f"  Warning: {e}")
                            break
                
                if remaining > 0:
                    raise ValueError(f"Not enough paystub images available (needed {count}, found {count - remaining})")
                
                # Process the collected cards
                cards = collected

                out_dir = tmp_root / f"paystub_pages_{len(final_pages)}"
                out_dir.mkdir(parents=True, exist_ok=True)
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