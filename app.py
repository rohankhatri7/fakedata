#testing this push
import os
from dotenv import load_dotenv
load_dotenv()
import pandas as pd
from random import choice, random
import re

from config import (
    FILE, NUMROWS, SHEETNAME,
    fake, fake_address, ny_zips,
    NY_ADDR_CSV, REAL_ADDRESS_RATIO,
    CSV_FILE
)
from generators import generate_complex_name, split_address

import zipcodes
import usps_api

# load csv
_ADDR_SAMPLE = None

# load csv rows to keep in dataframe
def _load_address_sample():
    global _ADDR_SAMPLE
    if _ADDR_SAMPLE is None:
        if not os.path.exists(NY_ADDR_CSV):
            raise FileNotFoundError(f"NY address CSV not found: {NY_ADDR_CSV}")
        print(f"[INFO] Loading NY address sample from {NY_ADDR_CSV} …")
        _ADDR_SAMPLE = (
            pd.read_csv(
                NY_ADDR_CSV,
                usecols=["NUMBER", "STREET", "UNIT", "CITY", "POSTCODE"],
                dtype=str,
                nrows=10000,
            )
            .dropna(subset=["NUMBER", "STREET", "CITY", "POSTCODE"])
        )
    return _ADDR_SAMPLE

# Generate rows in spreadsheet
def generate_rows(n: int = NUMROWS) -> pd.DataFrame:
    rows = []

    for _ in range(n):
        if random() < REAL_ADDRESS_RATIO:
            addr_df = _load_address_sample()
            addr = addr_df.sample(1).iloc[0]

            #convert csv line to API parameters
            street1 = f"{addr['NUMBER']} {addr['STREET']}".strip()
            street2 = addr['UNIT'] if pd.notna(addr.get('UNIT')) else ""
            city = addr['CITY'].title()
            zip5_raw = str(addr['POSTCODE']) if pd.notna(addr['POSTCODE']) else ""
            m = re.match(r"(\d{5})", zip5_raw)
            zip5 = m.group(1) if m else ""

            # County via zipcodes lib (may be empty)
            zinfo = zipcodes.matching(zip5)
            county = zinfo[0]['county'].replace("County", "").strip() if zinfo else ""

            # ZIP+4 via USPS
            try:
                zip9 = usps_api.lookup_zip9(street1, city, "NY")
            except Exception as exc:
                print(f"[WARN] USPS lookup failed for '{street1}, {city}': {exc}")
                zip9 = zip5

            if not zip9 or not zip9[0].isdigit():
                zip9 = zip5

            # real address and zip via USPS
            rows.append({
                "Formtype": "",
                "RowType": "real",
                "AccountID": fake.bothify("AC##########"),
                "HealthBenefitID": fake.bothify("HX###########"),
                "DOB": fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m/%d/%Y"),
                "FirstName": generate_complex_name("first"),
                "MiddleInitial": fake.random_uppercase_letter(),
                "LastName": generate_complex_name("last"),
                "SSN": fake.ssn(),
                "County": county,
                "Street1": street1,
                "Street2": street2,
                "Zip": zip9,
                "City": city,
                "State": "NY",
                "Filename": "",
            })
        else:
            rec = choice(ny_zips)
            full_address = fake_address.street_address()
            street1, street2_candidate = split_address(full_address)
            street2 = street2_candidate or (fake_address.secondary_address() if random() < 0.3 else "")
            
            # all Faker generated data
            rows.append({
                "Formtype": "",
                "RowType": "fake",
                "AccountID": fake.bothify("AC##########"),
                "HealthBenefitID": fake.bothify("HX###########"),
                "DOB": fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m/%d/%Y"),
                "FirstName": generate_complex_name("first"),
                "MiddleInitial": fake.random_uppercase_letter(),
                "LastName": generate_complex_name("last"),
                "SSN": fake.ssn(),
                "County": rec["county"].replace("County", "").replace("county", "").strip(),
                "Street1": street1,
                "Street2": street2,
                "Zip": rec["zip_code"],
                "City": rec["city"],
                "State": "NY",
                "Filename": "",
            })

    return pd.DataFrame(rows)

def main():
    try:
        if not os.path.exists(FILE):
            print(f"Creating new file: {FILE}")
        else:
            print(f"Replacing data in existing file: {FILE}")
        
        new_rows = generate_rows()
        # Write Excel
        new_rows.to_excel(FILE,
                          index=False,
                          sheet_name=SHEETNAME,
                          engine="openpyxl")

        # also output to csv format
        new_rows.to_csv(CSV_FILE, index=False)

        print(f"Success: generated {NUMROWS} rows to '{FILE}' and '{CSV_FILE}'.")

    except PermissionError:
        print(f"ERROR: File '{FILE}' is open. Close it and re-run.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
