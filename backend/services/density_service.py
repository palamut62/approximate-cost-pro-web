from typing import Dict, Optional, Tuple
import re

# Standart Yoğunluklar (ton/m³) - ÇŞB/KİK Normları
DENSITIES: Dict[str, float] = {
    # Beton ve Harçlar
    "beton_donatisiz": 2.400,
    "beton_donatili": 2.500,  # +100kg demir payı
    "hazir_beton": 2.400,
    "beton_harci": 2.400,
    "grobeton": 2.300,
    "c20": 2.400,
    "c25": 2.400,
    "c30": 2.400,
    "c35": 2.400,
    
    # Agregalar
    "kum": 1.600,
    "cakil": 1.700, # 1.6-1.8 arası
    "kirmatas": 1.600,
    "stabilize": 1.800,
    "toprak_dogal": 1.600,
    "toprak_gecsek": 1.800, # kazılmış sıkışmış
    "moloz": 1.500, # ortalama
    
    # Bağlayıcılar
    "cimento": 1.200, # torbalı dökme değişir ama ortalama
    "kirec": 0.600,   # toz
    
    # Metaller
    "demir": 7.850,
    "celik": 7.850,
    "aluminyum": 2.700,
    
    # Duvar Malzemeleri
    "tugla": 1.000, # adet hesabı daha yaygın ama m3 hesabı için (boşluklu)
    "gazbeton": 0.600, 
    "bims": 0.700,
    
    # Kaplamalar
    "seramik": 2.300,
    "mermer": 2.700,
    "granit": 2.700,
    
    # Diğer
    "su": 1.000,
    "ahsap": 0.600, # ortalama çam
    "cam": 2.500
}

# Malzeme kelime haritası
KEYWORD_MAPPING = {
    "betonarme": "beton_donatili",
    "hazır beton": "hazir_beton",
    "hazir beton": "hazir_beton",
    "grobeton": "grobeton",
    "c 20": "c20", "c-20": "c20", "c20": "c20",
    "c 25": "c25", "c-25": "c25", "c25": "c25",
    "c 30": "c30", "c-30": "c30", "c30": "c30",
    "kum": "kum",
    "çakıl": "cakil", "cakil": "cakil", "agrega": "cakil",
    "çimento": "cimento", "cimento": "cimento",
    "demir": "demir", "donatı": "demir", "çelik": "demir",
    "tuğla": "tugla", "tugla": "tugla",
    "gazbeton": "gazbeton", "ytong": "gazbeton",
    "su": "su",
    "kazı": "toprak_dogal", "hafriyat": "toprak_dogal",
    "moloz": "moloz"
}

def normalize_name(name: str) -> str:
    return name.lower().replace('İ','i').replace('I','ı')

def get_material_density(material_name: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Malzeme isminden yoğunluğunu bulur.
    Returns: (density, matched_key) or (None, None)
    """
    norm_name = normalize_name(material_name)
    
    # 1. Direkt Eşleşme
    if norm_name in DENSITIES:
        return DENSITIES[norm_name], norm_name
        
    # 2. Keyword Arama (En uzun eşleşmeyi tercih et)
    best_match = None
    max_len = 0
    
    for kw, key in KEYWORD_MAPPING.items():
        if kw in norm_name:
            if len(kw) > max_len:
                best_match = key
                max_len = len(kw)
                
    if best_match:
        # C20, C25 gibi özel betonlar donatılı ise 2.5, değilse 2.4
        if "donatı" in norm_name or "betonarme" in norm_name or "demir" in norm_name:
            if best_match in ["hazir_beton", "c20", "c25", "c30", "c35"]:
                return DENSITIES["beton_donatili"], "beton_donatili"
                
        return DENSITIES[best_match], best_match
        
    return None, None

def calculate_transport_tonnage(material_name: str, quantity: float, unit: str) -> Optional[float]:
    """
    Verilen malzemenin miktarını tona çevirir.
    Nakliye her zaman TON veya M3 üzerinden hesaplanır, ancak fiyat analizi ton üzerinden ise bu çeviri gereklidir.
    """
    density, _ = get_material_density(material_name)
    
    if not density:
        return None
        
    norm_unit = normalize_name(unit)
    
    # M3 -> Ton
    if norm_unit in ["m3", "m³", "metreküp"]:
        return quantity * density
        
    # Ton -> Ton (Zaten ton)
    if norm_unit in ["ton", "t"]:
        return quantity
        
    # Kg -> Ton
    if norm_unit in ["kg", "kilogram"]:
        return quantity / 1000.0
        
    # M2 -> Ton (Kalınlık bilinmiyor, tahmin zor)
    # Burada varsayımlar yapılabilir ancak riskli.
    # Örn: 20cm duvar -> 0.2 m3/m2
    
    return None
