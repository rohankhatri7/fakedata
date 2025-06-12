import time, os, requests, urllib.parse, json
from typing import Tuple

from config import USPS_CLIENT_ID, USPS_CLIENT_SECRET

# Taken from USPS API docs
_TOKEN_URL = "https://apis-tem.usps.com/oauth2/v3/token"
_ZIP_ENDPOINT = "https://apis-tem.usps.com/addresses/v3/zipcode"

_cache: dict = {"token": None, "expires": 0}


# Refresh USPS OAuth token once an hour
def _refresh_token() -> str:
    body = {
        "client_id": USPS_CLIENT_ID,
        "client_secret": USPS_CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "addresses"
    }
    resp = requests.post(_TOKEN_URL,
                         headers={"Content-Type": "application/json", "Accept": "application/json"},
                         json=body,
                         timeout=30)
    resp.raise_for_status()
    data = resp.json()
    _cache["token"] = data["access_token"]
    _cache["expires"] = time.time() + int(data.get("expires_in", 3600)) - 300
    return _cache["token"]

# Return cached token automatically since they refresh every 8 hours
def _get_token() -> str:
    if not USPS_CLIENT_ID or USPS_CLIENT_ID == "CHANGE_ME":
        raise RuntimeError("USPS_CLIENT_ID / USPS_CLIENT_SECRET environment variables not set.")
    if time.time() >= _cache.get("expires", 0):
        return _refresh_token()
    return _cache["token"]


def lookup_zip9(street: str, city: str, state: str = "NY") -> str:
    # Return 9-digit ZIP code; if fail, default to 5-digit ZIP
    token = _get_token()
    params = {
        "streetAddress": street,
        "city": city,
        "state": state
    }
    try:
        r = requests.get(_ZIP_ENDPOINT,
                         headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                         params=params,
                         timeout=20)
        r.raise_for_status()
        addr = r.json().get("address", {})
        zip5 = addr.get("ZIPCode") or addr.get("zipCode")
        plus4 = addr.get("ZIPPlus4") or addr.get("zipPlus4")
        if zip5 and plus4:
            return f"{zip5}-{plus4}"
    except Exception:
        pass
    return params["streetAddress"].split()[-1][:5]
