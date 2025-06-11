import time, os, requests, urllib.parse, json
from typing import Tuple

from config import USPS_CLIENT_ID, USPS_CLIENT_SECRET

# --- USPS OAuth --------------------------------------------------------------------
_TOKEN_URL = "https://apis-tem.usps.com/oauth2/v3/token"  # swap to prod domain when ready
_ZIP_ENDPOINT = "https://apis-tem.usps.com/addresses/v3/zipcode"

_cache: dict = {"token": None, "expires": 0}


def _refresh_token() -> str:
    """Fetch a fresh OAuth2 bearer-token using client-credentials grant."""
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
    # token TTL is typically 3600 s; be conservative and renew 5 minutes early
    _cache["expires"] = time.time() + int(data.get("expires_in", 3600)) - 300
    return _cache["token"]


def _get_token() -> str:
    if not USPS_CLIENT_ID or USPS_CLIENT_ID == "CHANGE_ME":
        raise RuntimeError("USPS_CLIENT_ID / USPS_CLIENT_SECRET environment variables not set.")
    if time.time() >= _cache.get("expires", 0):
        return _refresh_token()
    return _cache["token"]

# ------------------------------------------------------------------------------------


def lookup_zip9(street: str, city: str, state: str = "NY") -> str:
    """Return 9-digit ZIP (ZIP+4) for the supplied address via the USPS Addresses v3 API.

    Falls back to the 5-digit ZIP if the request fails for any reason.
    """
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
        # swallow and fallback below
        pass
    # Fallback – return 5-digit only
    return params["streetAddress"].split()[-1][:5] 