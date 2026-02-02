import re
from typing import Set, List, Dict

# Canonical service names
SERVICE_NAKLIYE = "nakliye"
SERVICE_DOSEME = "döşeme" # Includes döküm, serim, yerleştirme
SERVICE_ISCILIK = "işçilik"
SERVICE_MONTAJ = "montaj"
SERVICE_SIKISTIRMA = "sıkıştırma"
SERVICE_SULAMA = "sulama"

# Keyword mapping to canonical services
KEYWORD_MAPPING = {
    "nakliye": SERVICE_NAKLIYE,
    "taşıma": SERVICE_NAKLIYE,
    "taşınması": SERVICE_NAKLIYE,
    "sevk": SERVICE_NAKLIYE,
    "sevk": SERVICE_NAKLIYE,
    "nakli": SERVICE_NAKLIYE,
    "nak": SERVICE_NAKLIYE, # abbreviation
    "nak.": SERVICE_NAKLIYE, # abbreviation with dot
    
    "döşeme": SERVICE_DOSEME,
    "döşen": SERVICE_DOSEME, # döşenmesi
    "serim": SERVICE_DOSEME,
    "serilmesi": SERVICE_DOSEME,
    "yerleştirme": SERVICE_DOSEME,
    "yerleştirilmesi": SERVICE_DOSEME,
    "döküm": SERVICE_DOSEME,
    "dökülmesi": SERVICE_DOSEME,
    "dökül": SERVICE_DOSEME, # dökülmesi root
    
    "işçilik": SERVICE_ISCILIK,
    "iscilik": SERVICE_ISCILIK,
    "işçiliği": SERVICE_ISCILIK,
    
    "montaj": SERVICE_MONTAJ,
    "yerine koyma": SERVICE_MONTAJ,
    
    "sıkıştırma": SERVICE_SIKISTIRMA,
    "sıkıştır": SERVICE_SIKISTIRMA, # sıkıştırılması
    "silindiraj": SERVICE_SIKISTIRMA,
    
    "sulama": SERVICE_SULAMA,
}

def normalize_text(text: str) -> str:
    """Normalize text for consistent parsing."""
    if not text:
        return ""
    
    text = text.lower()
    # Replace turkish chars
    text = text.replace('İ', 'i').replace('I', 'ı').replace('Ğ', 'ğ').replace('Ü', 'ü').replace('Ş', 'ş').replace('Ö', 'ö').replace('Ç', 'ç')
    
    # Normalize abbreviations
    text = re.sub(r'\bnak\.', 'nakliye', text)
    text = re.sub(r'\bvb\.', '', text)
    
    return text

def extract_included_services(description: str) -> Set[str]:
    """
    Parses a description string to find services explicitly marked as included.
    Returns a set of canonical service names (e.g., {'nakliye', 'döşeme'}).
    """
    included_services = set()
    norm_desc = normalize_text(description)
    
    if not norm_desc:
        return included_services

    # Patterns to catch "X dahil", "X ve Y dahil", "X, Y dahil"
    # We look for the word "dahil" or "içinde"
    
    # Check simple clauses first
    # Example: "nakliye ve yerine dökme dahil"
    # Example: "her şey dahil" -> dangerous, maybe ignore?
    
    # Split by basic separators to isolate clauses slightly, but regex is better spanning
    # Let's try to find segments ending with "dahil"
    
    dahil_matches = re.finditer(r'([^,.;]*?)\s+(?:dahil|içinde)', norm_desc)
    
    for match in dahil_matches:
        clause = match.group(1)
        # Check keywords in this clause
        for keyword, canonical in KEYWORD_MAPPING.items():
            # word boundary check. Allow optional dot for abbreviations.
            if re.search(r'\b' + re.escape(keyword) + r'\.?\b', clause):
                included_services.add(canonical)
                
    # Special case: "X nakli" usually implies transport is the item itself, NOT included extra.
    # BUT if the main item is "Hazır beton", and description says "nakli dahil", then we filter separate transport.
    
    # [FIX] Ready-mixed concrete specific logic
    # "Hazır beton" description specifically includes transport usually.
    # If the text mentions "Hazır beton" AND ("nakli dahil" OR "nakliye dahil" OR "pompalanması")
    if "hazır beton" in norm_desc or "hazir beton" in norm_desc:
        if "nakli" in norm_desc or "nakliye" in norm_desc or "pompa" in norm_desc:
             included_services.add(SERVICE_NAKLIYE)
             
    # [FIX] Handle parenthesis content like "(Nakliye dahil)" or "(... dahil)"
    # The previous regex might miss it if it's on a new line or isolated.
    # Let's look for explicit "( ... dahil )" blocks
    parenthesis_matches = re.finditer(r'\(([^)]*?dahil[^)]*?)\)', norm_desc)
    for match in parenthesis_matches:
        content = match.group(1)
        if "nakliye" in content or "nakli" in content:
            included_services.add(SERVICE_NAKLIYE)
        if "işçilik" in content:
            included_services.add(SERVICE_ISCILIK)
        if "malzeme" in content:
             # Malzeme is rarely excluded but good to mark if we had a service for it
             pass

    return included_services

def should_exclude_component(component_name: str, component_type: str, excluded_services: Set[str]) -> bool:
    """
    Determines if a component should be excluded based on the list of excluded services.
    
    Args:
        component_name: Name of the component (e.g. "Beton nakli")
        component_type: Type of the component (e.g. "Nakliye", "İşçilik")
        excluded_services: Set of canonical services to exclude (e.g. {'nakliye'})
    """
    if not excluded_services:
        return False
        
    norm_name = normalize_text(component_name)
    norm_type = normalize_text(component_type)
    
    # Check specific component types
    if SERVICE_NAKLIYE in excluded_services:
        if "nakliye" in norm_type or "nakliye" in norm_name or "taşıma" in norm_name or "sevk" in norm_name or "nakli" in norm_name:
            return True
            
    if SERVICE_DOSEME in excluded_services:
        # If filtered service is "döşeme" (casting/laying), we filter items that look like laying work
        if any(x in norm_name for x in ["döşeme", "döşen", "serim", "döküm", "dökül", "yerleştirme"]):
             if component_type in ["İşçilik", "Makine"]: # Usually these are labor/machine items
                 return True
                 
    if SERVICE_ISCILIK in excluded_services:
        if "işçilik" in norm_type or "işçilik" in norm_name or "işçiliği" in norm_name:
            return True
            
    if SERVICE_MONTAJ in excluded_services:
        if "montaj" in norm_name:
            return True
            
    return False
