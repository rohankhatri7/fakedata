import zipcodes
from faker import Faker
from random import random 
import os, pathlib

FILE = "testfaker.xlsx"   
NUMROWS = 100                
SHEETNAME = "Sheet1"

#initialize faker
fake = Faker(['en_US', 'es'])
fake_en = fake['en_US']
fake_es = fake['es']
fake_address = Faker('en_US') # addresses follow US format

# preload NY zips
ny_zips = zipcodes.filter_by(state="NY")

# USPS credentials (set via environment for security; fallback to placeholder)
USPS_CLIENT_ID = os.getenv("USPS_CLIENT_ID", "CHANGE_ME")
USPS_CLIENT_SECRET = os.getenv("USPS_CLIENT_SECRET", "CHANGE_ME")

# Directory that holds NY address CSVs downloaded from OpenAddresses
NY_ADDR_DIR = pathlib.Path(__file__).parent / "ny"
# We sample from this CSV (change to another if you prefer)
NY_ADDR_CSV = os.getenv("NY_ADDR_CSV", str(NY_ADDR_DIR / "statewide.csv"))

# Percentage of output rows that should be real NY addresses (0-1)
REAL_ADDRESS_RATIO = float(os.getenv("REAL_ADDRESS_RATIO", "0.3"))