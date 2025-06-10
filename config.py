import zipcodes
from faker import Faker
from random import random  # Add this import

# File settings
FILE = "testfaker.xlsx"   
NUMROWS = 100                
SHEETNAME = "Sheet1"

# Initialize Faker instances
fake = Faker(['en_US', 'es'])
fake_en = fake['en_US']
fake_es = fake['es']
fake_address = Faker('en_US')

# Preload NY zips
ny_zips = zipcodes.filter_by(state="NY")