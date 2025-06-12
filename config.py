import zipcodes
from faker import Faker
from random import random 
import os, pathlib

FILE = "testfaker.xlsx"   
NUMROWS = 100                
SHEETNAME = "Sheet1"

# Initialize Faker
fake = Faker(['en_US', 'es'])
fake_en = fake['en_US']
fake_es = fake['es']
fake_address = Faker('en_US')  # Addresses follow US format

# Preload NY ZIP codes for Faker use
ny_zips = zipcodes.filter_by(state="NY")

# USPS credentials (set via environment for security; fallback to placeholder)
USPS_CLIENT_ID = os.getenv("USPS_CLIENT_ID", "CHANGE_ME")
USPS_CLIENT_SECRET = os.getenv("USPS_CLIENT_SECRET", "CHANGE_ME")

# Folder that holds NY address CSVs downloaded from OpenAddresses
NY_ADDR_DIR = pathlib.Path(__file__).parent / "ny"
# Statewide CSV for variety
NY_ADDR_CSV = os.getenv("NY_ADDR_CSV", str(NY_ADDR_DIR / "statewide.csv"))

# 30% of rows are real NY addresses
REAL_ADDRESS_RATIO = float(os.getenv("REAL_ADDRESS_RATIO", "0.3"))

# ---------------------------------------------------------------------------
# Output & template settings
# ---------------------------------------------------------------------------

# CSV output file (same base-name as the Excel workbook)
CSV_FILE = os.getenv("CSV_FILE", FILE.replace(".xlsx", ".csv"))

# Directory layout for templates & fonts
BASE_DIR = pathlib.Path(__file__).parent
TEMPLATE_DIR = BASE_DIR / "templates"
FONTS_DIR = BASE_DIR / "fonts"

# Specific template used for Social-Security form (PNG)
# Default looks for "ssn.png" in the project root; override via env-var if you keep it elsewhere.
SSN_TEMPLATE_PATH = os.getenv("SSN_TEMPLATE_PATH", str(BASE_DIR / "ssn.png"))

# Default handwriting font (TTF)
HANDWRITING_FONT = os.getenv("HANDWRITING_FONT", str(FONTS_DIR / "handwriting.ttf"))

# Signature-specific font (e.g., a cursive style)
SIGNATURE_FONT = os.getenv("SIGNATURE_FONT", str(FONTS_DIR / "signature.ttf"))
