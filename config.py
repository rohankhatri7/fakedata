import zipcodes
from faker import Faker
from random import random 

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