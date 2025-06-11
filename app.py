#faker does not have built in city nor county functions that can be specific to NY as it will always be random

# 9 digit zip code; 5 digits hyphen 4 digits; look at USPS for some of them
    # not possible through USPS API, it cannot just generate zip+4 without being given a real street address
# adjust street1 and street2 to simulate real world like i did w/ county

import pandas as pd
import os
from random import choice, random 
from config import FILE, NUMROWS, SHEETNAME, fake, fake_address, ny_zips
from generators import generate_complex_name, split_address

def generate_rows(n=NUMROWS) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        rec = choice(ny_zips)
        full_address = fake_address.street_address()
        street1, street2 = split_address(full_address)
        
        rows.append({
            "Formtype": "",                           
            "AccountID": fake.bothify("AC##########"), 
            "HealthBenefitID": fake.bothify("HX###########"),
            "DOB": fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m/%d/%Y"),
            "FirstName": generate_complex_name("first"),
            "MiddleInitial": fake.random_uppercase_letter(),
            "LastName": generate_complex_name("last"),
            "SSN": fake.ssn(),
            "County": f"{rec['county']}",
            "Street1": street1,
            "Street2": street2 or fake_address.secondary_address() if random() < 0.3 else "",
            "Zip": rec["zip_code"],
            "City": rec["city"],
            "State": "NY",
            "Filename": ""      
        })
    return pd.DataFrame(rows)

def main():
    try:
        if not os.path.exists(FILE):
            print(f"Creating new file: {FILE}")
        else:
            print(f"Replacing data in existing file: {FILE}")
        
        new_rows = generate_rows()
        new_rows.to_excel(FILE,
                         index=False,
                         sheet_name=SHEETNAME,
                         engine="openpyxl")
        print(f"Success: generated {NUMROWS} rows to '{FILE}' on '{SHEETNAME}'.")
    except PermissionError:
        print(f"ERROR: File '{FILE}' is open. Close it and re-run.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
