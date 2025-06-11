#faker does not have built in city nor county functions that can be specific to NY as it will always be random

# 9 digit zip code; 5 digits hyphen 4 digits; look at USPS for some of them
    # not possible through USPS API, it cannot just generate zip+4 without being given a real street address
# adjust street1 and street2 to simulate real world like i did w/ county
# work on pdf/image templates
# look at Dan's repo for image templates

import os
from dotenv import load_dotenv
load_dotenv()
import pandas as pd
from random import choice, random

from config import (
    FILE, NUMROWS, SHEETNAME,
    fake, fake_address, ny_zips,
    NY_ADDR_CSV, REAL_ADDRESS_RATIO
)
from generators import generate_complex_name, split_address

import zipcodes
import usps_api

# ---------------------------------------------------------------------------
# Utility to lazily load a sample of real NY addresses from OpenAddresses CSV
# ---------------------------------------------------------------------------
_ADDR_SAMPLE = None


def _load_address_sample():
    # load dataframe of NY addresses; first 100k rows only
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
                nrows=100_000,
            )
            .dropna(subset=["NUMBER", "STREET", "CITY", "POSTCODE"])
        )
    return _ADDR_SAMPLE

#generate rows in spreadsheet
def generate_rows(n: int = NUMROWS) -> pd.DataFrame:
    rows = []

    for _ in range(n):
        if random() < REAL_ADDRESS_RATIO:
            # real NY addresses using USPS API and OpenAddresses
            addr_df = _load_address_sample()
            addr = addr_df.sample(1).iloc[0]

            street1 = f"{addr['NUMBER']} {addr['STREET']}".strip()
            street2 = addr['UNIT'] if pd.notna(addr.get('UNIT')) else ""
            city = addr['CITY'].title()
            zip5 = str(addr['POSTCODE'])[:5]

            # County via zipcodes lib (may be empty)
            zinfo = zipcodes.matching(zip5)
            county = zinfo[0]['county'].replace("County", "").strip() if zinfo else ""

            # ZIP+4 via USPS
            try:
                zip9 = usps_api.lookup_zip9(street1, city, "NY")
            except Exception as exc:
                print(f"[WARN] USPS lookup failed for '{street1}, {city}': {exc}")
                zip9 = zip5

            rows.append({
                "Formtype": "", #empty for now
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
                "Filename": "real",
            })
        else:
            # faker generated address, still specific to NY
            rec = choice(ny_zips)
            full_address = fake_address.street_address()
            street1, street2_candidate = split_address(full_address)
            street2 = street2_candidate or (fake_address.secondary_address() if random() < 0.3 else "")

            rows.append({
                "Formtype": "",
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
                "Filename": "fake",
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
