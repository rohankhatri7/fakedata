from random import choice, random
from config import fake, fake_en, fake_es, fake_address, ny_zips
from unicodedata import normalize

def _strip_accents(text: str) -> str:
    # return the ASCII version of text
    return normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

def generate_complex_name(type="first"):
    # more complicated names
    name_funcs = {
        "first": [fake_en.first_name, fake_es.first_name],
        "last": [fake_en.last_name, fake_es.last_name]
    }
    
    if random() < 0.3:  # Probability of generating a complex name
        name_type = choice(["hyphenated", "double", "simple"])
        name_locale = choice(name_funcs[type])
        
        if name_type == "hyphenated":
            name = f"{name_locale()}-{name_locale()}"
        elif name_type == "double":
            name = f"{name_locale()} {name_locale()}"
        else:
            name = name_locale()
    else:
        name = choice(name_funcs[type])()
    
    # No special characters or accents
    return _strip_accents(name)

def split_address(address):
    # If street 1 contains suite, unit, apt, or #, split and append to street2 column
    keywords = ["apt", "suite", "unit", "#", "ste"]
    parts = address.lower().split()
    
    for i, word in enumerate(parts):
        if any(keyword in word for keyword in keywords):
            street = " ".join(parts[:i])
            unit = " ".join(parts[i:])
            return address[:len(street)], address[len(street):].strip()
    return address, ""
