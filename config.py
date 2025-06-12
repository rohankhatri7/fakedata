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
