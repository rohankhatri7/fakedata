from random import choice, random
from config import fake, fake_en, fake_es, fake_address, ny_zips

def generate_complex_name(type="first"):
    """Generate complex first or last names with various formats"""
    name_funcs = {
        "first": [fake_en.first_name, fake_es.first_name],
        "last": [fake_en.last_name, fake_es.last_name]
    }
    
    if random() < 0.3:  # 30% chance of complex name
        name_type = choice(["hyphenated", "double", "simple"])
        name_locale = choice(name_funcs[type])
        
        if name_type == "hyphenated":
            return f"{name_locale()}-{name_locale()}"
        elif name_type == "double":
            return f"{name_locale()} {name_locale()}"
        else:
            return name_locale()
    return choice(name_funcs[type])()

def split_address(address):
    """Split address into street and unit parts"""
    keywords = ["apt", "suite", "unit", "#", "ste"]
    parts = address.lower().split()
    
    for i, word in enumerate(parts):
        if any(keyword in word for keyword in keywords):
            street = " ".join(parts[:i])
            unit = " ".join(parts[i:])
            return address[:len(street)], address[len(street):].strip()
    return address, ""