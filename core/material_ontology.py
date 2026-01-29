"""
İnşaat Malzeme Ontoloji Sistemi
================================

Bu modül, inşaat imalat türleri için zorunlu ve opsiyonel malzeme kurallarını tanımlar.
Amaç: AI analizinin tutarlılığını ve eksiksizliğini garantilemek.

Kullanım:
    from core.material_ontology import get_material_rules, validate_material_completeness

    rules = get_material_rules("betonarme")
    validation = validate_material_completeness("betonarme", materials_list)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class MaterialType(Enum):
    """Malzeme kategorileri"""
    BETON = "beton"
    DEMIR = "demir"
    KALIP = "kalıp"
    CIMENTO = "çimento"
    KUM = "kum"
    CAKIL = "çakıl"
    TUGLA = "tuğla"
    HARÇ = "harç"
    YAPI_KIMYASALLARI = "yapı_kimyasalları"
    SU = "su"


class ComponentType(Enum):
    """Bileşen kategorileri"""
    MALZEME = "Malzeme"
    ISCILIK = "İşçilik"
    MAKINE = "Makine"
    NAKLIYE = "Nakliye"
    DIGER = "Diğer"


@dataclass
class MaterialRule:
    """Malzeme kuralı yapısı"""
    material_type: str  # Malzeme tipi (ör: "beton", "demir")
    unit: str  # Birim (ör: "m³", "ton", "kg")
    coefficient: Optional[float] = None  # Sabit katsayı (ör: 1.0 için beton)
    coefficient_formula: Optional[str] = None  # Dinamik hesaplama formülü
    is_mandatory: bool = True  # Zorunlu mu?
    poz_pattern: Optional[str] = None  # Poz kodu paterni (ör: "10.130.15*")
    notes: str = ""  # Açıklama


@dataclass
class LaborRule:
    """İşçilik kuralı yapısı"""
    labor_type: str  # İşçilik tipi (ör: "betoncu", "demirci")
    unit: str = "sa"  # Saat cinsinden
    is_mandatory: bool = True
    poz_pattern: Optional[str] = None
    notes: str = ""


@dataclass
class ConstructionTypeRule:
    """İmalat tipi için tam kural seti"""
    construction_type: str  # İmalat tipi kodu
    display_name: str  # Görünen ad
    keywords: List[str]  # Tespit için anahtar kelimeler
    materials: List[MaterialRule]  # Malzeme kuralları
    labor: List[LaborRule]  # İşçilik kuralları
    requires_transport: bool = True  # Nakliye zorunlu mu?
    requires_machinery: bool = False  # Makine zorunlu mu?
    notes: str = ""


# ============================================
# İMALAT TİPİ KURALLARI
# ============================================

CONSTRUCTION_TYPE_RULES: Dict[str, ConstructionTypeRule] = {

    # BETONARME İMALATI
    "betonarme": ConstructionTypeRule(
        construction_type="betonarme",
        display_name="Betonarme İmalat",
        keywords=["betonarme", "betonarm", "donatı", "donatılı beton", "hasır donatı"],
        materials=[
            MaterialRule(
                material_type="beton",
                unit="m³",
                coefficient=1.0,
                is_mandatory=True,
                poz_pattern="10.130.15*",
                notes="Beton sınıfı (C20/25, C25/30, C30/37 vb.) belirtilmeli"
            ),
            MaterialRule(
                material_type="demir",
                unit="ton",
                coefficient=0.12,  # Ortalama %12 donatı oranı
                is_mandatory=True,
                poz_pattern="10.140.*",
                notes="Nervürlü betonarme çeliği S420. Oran proje tipine göre 0.08-0.20 arası değişir"
            ),
            MaterialRule(
                material_type="kalıp",
                unit="m²",
                coefficient_formula="surface_area",
                is_mandatory=True,
                poz_pattern="04.*",
                notes="Ahşap veya metal kalıp. Yüzey alanı hesaplanmalı"
            ),
            MaterialRule(
                material_type="yapi_kimyasallari",
                unit="kg",
                coefficient=0.02,
                is_mandatory=False,
                notes="Kimyasal katkı (akışkanlaştırıcı, geciktirici vb.) - opsiyonel"
            )
        ],
        labor=[
            LaborRule("betoncu", unit="sa", is_mandatory=True, notes="Beton dökümü ve vibrasyonu"),
            LaborRule("demirci", unit="sa", is_mandatory=True, notes="Donatı yerleştirme ve bağlama"),
            LaborRule("kalıpçı", unit="sa", is_mandatory=True, notes="Kalıp kurma ve sökme")
        ],
        requires_transport=True,
        requires_machinery=False,
        notes="Betonarme için beton+demir+kalıp üçlüsü zorunludur"
    ),

    # BETON İMALATI (donatısız)
    "beton_imalati": ConstructionTypeRule(
        construction_type="beton_imalati",
        display_name="Beton İmalat (Donatısız)",
        keywords=["beton", "beton dökü", "düz beton", "yalın beton", "lean concrete"],
        materials=[
            MaterialRule(
                material_type="beton",
                unit="m³",
                coefficient=1.0,
                is_mandatory=True,
                poz_pattern="10.130.15*",
                notes="Sınıfı belirtilmeli (C16/20, C20/25 vb.)"
            ),
            MaterialRule(
                material_type="kalip",
                unit="m²",
                coefficient_formula="surface_area",
                is_mandatory=True,
                poz_pattern="04.*",
                notes="Düz beton için de kalıp gerekir"
            )
        ],
        labor=[
            LaborRule("betoncu", unit="sa", is_mandatory=True, notes="Beton dökümü")
        ],
        requires_transport=True,
        requires_machinery=False,
        notes="Donatısız beton - sadece beton+kalıp"
    ),

    # KALIP İŞLERİ
    "kalip_isleri": ConstructionTypeRule(
        construction_type="kalip_isleri",
        display_name="Kalıp İşleri",
        keywords=["kalıp", "kalıp kurma", "kalıp sökme", "ahşap kalıp", "metal kalıp"],
        materials=[
            MaterialRule(
                material_type="kalip",
                unit="m²",
                coefficient=1.0,
                is_mandatory=True,
                poz_pattern="04.*",
                notes="Kalıp tipi belirtilmeli (ahşap/metal)"
            )
        ],
        labor=[
            LaborRule("kalıpçı", unit="sa", is_mandatory=True, notes="Kalıp kurma/sökme işçiliği")
        ],
        requires_transport=True,
        requires_machinery=False,
        notes="Sadece kalıp malzemesi ve işçiliği"
    ),

    # DEMİR İMALATI
    "demir_imalati": ConstructionTypeRule(
        construction_type="demir_imalati",
        display_name="Betonarme Demiri İmalat",
        keywords=["demir", "donatı", "betonarme demiri", "nervürlü", "hasır"],
        materials=[
            MaterialRule(
                material_type="demir",
                unit="ton",
                coefficient=1.0,
                is_mandatory=True,
                poz_pattern="10.140.*",
                notes="S420 nervürlü betonarme çeliği"
            )
        ],
        labor=[
            LaborRule("demirci", unit="sa", is_mandatory=True, notes="Demir kesme, bükme, yerleştirme")
        ],
        requires_transport=True,
        requires_machinery=False,
        notes="Sadece donatı malzemesi ve işçiliği"
    ),

    # KAGIR DUVAR
    "kagir_duvar": ConstructionTypeRule(
        construction_type="kagir_duvar",
        display_name="Kâgir Duvar İmalat",
        keywords=["tuğla", "duvar", "kâgir", "kagir", "briket", "gazbeton"],
        materials=[
            MaterialRule(
                material_type="tugla",
                unit="adet",
                coefficient_formula="wall_area_to_brick",
                is_mandatory=True,
                poz_pattern="10.130.2*",
                notes="Tuğla tipi belirtilmeli (delikli, yatay delikli, gazbeton vb.)"
            ),
            MaterialRule(
                material_type="harç",
                unit="m³",
                coefficient=0.25,  # m² duvar başına yaklaşık harç
                is_mandatory=True,
                poz_pattern="10.130.11*",
                notes="Kireç harcı veya çimento harcı"
            )
        ],
        labor=[
            LaborRule("duvarcı", unit="sa", is_mandatory=True, notes="Tuğla örme işçiliği")
        ],
        requires_transport=True,
        requires_machinery=False,
        notes="Tuğla duvar için tuğla+harç gerekir"
    ),

    # SIIVA İŞLERİ
    "siva": ConstructionTypeRule(
        construction_type="siva",
        display_name="Sıva İşleri",
        keywords=["sıva", "siva", "alçı sıva", "çimento sıva", "harç sıva"],
        materials=[
            MaterialRule(
                material_type="harç",
                unit="m³",
                coefficient=0.015,  # m² başına yaklaşık sıva kalınlığı
                is_mandatory=True,
                poz_pattern="10.130.11*",
                notes="Sıva tipi belirtilmeli"
            )
        ],
        labor=[
            LaborRule("sıvacı", unit="sa", is_mandatory=True, notes="Sıva uygulama işçiliği")
        ],
        requires_transport=True,
        requires_machinery=False
    ),

    # HAFRIYAT
    "hafriyat": ConstructionTypeRule(
        construction_type="hafriyat",
        display_name="Hafriyat İşleri",
        keywords=["hafriyat", "kazı", "temel kazı", "kanal kazı", "ekskavatör"],
        materials=[],  # Malzeme gerekmez
        labor=[
            LaborRule("makinist", unit="sa", is_mandatory=True, notes="Ekskavatör operatörü")
        ],
        requires_transport=True,  # Hafriyat nakli gerekir
        requires_machinery=True,
        notes="Hafriyat için genelde makine (ekskavatör) gerekir"
    ),

    # DOLGU
    "dolgu": ConstructionTypeRule(
        construction_type="dolgu",
        display_name="Dolgu İşleri",
        keywords=["dolgu", "toprak dolgu", "kum dolgu", "stabilize"],
        materials=[
            MaterialRule(
                material_type="kum",
                unit="m³",
                coefficient=1.0,
                is_mandatory=True,
                poz_pattern="10.130.1004",
                notes="Dolgu malzemesi (kum, stabilize vb.)"
            )
        ],
        labor=[
            LaborRule("kompaktör operatörü", unit="sa", is_mandatory=True, notes="Sıkıştırma işçiliği")
        ],
        requires_transport=True,
        requires_machinery=True,
        notes="Dolgu için malzeme+nakliye+sıkıştırma gerekir"
    )
}


# ============================================
# FONKSİYONLAR
# ============================================

def detect_construction_type(description: str) -> Optional[str]:
    """
    Poz açıklamasından imalat tipini tespit et

    Args:
        description: Poz açıklaması (ör: "C25/30 betonarme temel")

    Returns:
        İmalat tipi kodu veya None
    """
    description_lower = description.lower()

    # En spesifikten genel olana doğru kontrol et
    scores = {}
    for type_code, rule in CONSTRUCTION_TYPE_RULES.items():
        score = 0
        for keyword in rule.keywords:
            if keyword.lower() in description_lower:
                score += len(keyword)  # Uzun kelimeler daha spesifik
        if score > 0:
            scores[type_code] = score

    if scores:
        # En yüksek skoru döndür
        return max(scores, key=scores.get)

    return None


def get_material_rules(construction_type: str) -> Optional[ConstructionTypeRule]:
    """
    İmalat tipi için malzeme kurallarını getir

    Args:
        construction_type: İmalat tipi kodu

    Returns:
        ConstructionTypeRule veya None
    """
    return CONSTRUCTION_TYPE_RULES.get(construction_type)


def validate_material_completeness(
    construction_type: str,
    materials: List[Dict[str, Any]],
    labor: List[Dict[str, Any]] = None,
    strict_mode: bool = False
) -> Dict[str, Any]:
    """
    Malzeme listesinin eksiksiz olup olmadığını kontrol et

    Args:
        construction_type: İmalat tipi kodu
        materials: Malzeme listesi [{"name": "...", "type": "Malzeme", ...}, ...]
        labor: İşçilik listesi (opsiyonel)
        strict_mode: Strict mod (tüm opsiyonel malzemeler de kontrol edilir)

    Returns:
        {
            "valid": bool,
            "missing_materials": List[str],
            "missing_labor": List[str],
            "missing_transport": bool,
            "warnings": List[str],
            "suggestions": List[str]
        }
    """
    rule = CONSTRUCTION_TYPE_RULES.get(construction_type)

    if not rule:
        return {
            "valid": True,
            "missing_materials": [],
            "missing_labor": [],
            "missing_transport": False,
            "warnings": [f"İmalat tipi '{construction_type}' için kural tanımlı değil"],
            "suggestions": []
        }

    missing_materials = []
    missing_labor = []
    warnings = []
    suggestions = []

    # Malzeme kontrolü
    material_names_lower = [m.get("name", "").lower() for m in materials]

    for material_rule in rule.materials:
        if not material_rule.is_mandatory and not strict_mode:
            continue

        # Malzeme var mı kontrol et
        found = any(material_rule.material_type in name for name in material_names_lower)

        if not found:
            if material_rule.is_mandatory:
                missing_materials.append(material_rule.material_type)
            else:
                suggestions.append(
                    f"Opsiyonel malzeme eklenebilir: {material_rule.material_type} "
                    f"({material_rule.notes})"
                )

    # İşçilik kontrolü
    if labor:
        labor_names_lower = [l.get("name", "").lower() for l in labor]

        for labor_rule in rule.labor:
            if not labor_rule.is_mandatory:
                continue

            found = any(labor_rule.labor_type in name for name in labor_names_lower)

            if not found:
                missing_labor.append(labor_rule.labor_type)

    # Nakliye kontrolü
    has_transport = any(
        m.get("type", "").lower() == "nakliye"
        for m in (materials + (labor or []))
    )
    missing_transport = rule.requires_transport and not has_transport

    # Makine kontrolü
    if rule.requires_machinery:
        has_machinery = any(
            m.get("type", "").lower() == "makine"
            for m in (materials + (labor or []))
        )
        if not has_machinery:
            warnings.append("Bu imalat için makine kullanımı önerilir")

    # Sonuç
    is_valid = (
        len(missing_materials) == 0 and
        len(missing_labor) == 0 and
        not missing_transport
    )

    return {
        "valid": is_valid,
        "missing_materials": missing_materials,
        "missing_labor": missing_labor,
        "missing_transport": missing_transport,
        "warnings": warnings,
        "suggestions": suggestions
    }


def get_expected_material_quantity(
    construction_type: str,
    material_type: str,
    base_quantity: float,
    unit: str
) -> Optional[float]:
    """
    İmalat tipi ve ana miktar bazında beklenen malzeme miktarını hesapla

    Args:
        construction_type: İmalat tipi kodu
        material_type: Malzeme tipi (ör: "demir", "kalıp")
        base_quantity: Ana miktar (ör: beton için 10 m³)
        unit: Birim

    Returns:
        Beklenen miktar veya None
    """
    rule = CONSTRUCTION_TYPE_RULES.get(construction_type)
    if not rule:
        return None

    for material_rule in rule.materials:
        if material_rule.material_type == material_type:
            if material_rule.coefficient is not None:
                return base_quantity * material_rule.coefficient
            else:
                # Dinamik formül gerektiriyor - burada hesaplanamaz
                return None

    return None


def get_all_construction_types() -> List[Dict[str, str]]:
    """Tüm imalat tiplerini listele"""
    return [
        {
            "code": code,
            "name": rule.display_name,
            "keywords": ", ".join(rule.keywords)
        }
        for code, rule in CONSTRUCTION_TYPE_RULES.items()
    ]


# ============================================
# TEST VE ÖRNEK KULLANIM
# ============================================

if __name__ == "__main__":
    # Test 1: İmalat tipi tespiti
    print("=== TEST 1: İmalat Tipi Tespiti ===")
    test_descriptions = [
        "C25/30 betonarme temel",
        "Tuğla duvar imalatı",
        "Düz beton döşeme",
        "Demir hasır donatı",
    ]

    for desc in test_descriptions:
        detected = detect_construction_type(desc)
        print(f"{desc:<40} → {detected}")

    print("\n=== TEST 2: Malzeme Validasyonu ===")
    # Test 2: Betonarme için eksik malzeme
    materials = [
        {"name": "Beton C25/30", "type": "Malzeme", "quantity": 10, "unit": "m³"},
        {"name": "Betonarme Demiri", "type": "Malzeme", "quantity": 1.2, "unit": "ton"}
        # Kalıp eksik!
    ]

    validation = validate_material_completeness("betonarme", materials)
    print(f"Valid: {validation['valid']}")
    print(f"Eksik Malzemeler: {validation['missing_materials']}")
    print(f"Nakliye Eksik: {validation['missing_transport']}")

    print("\n=== TEST 3: Beklenen Miktar Hesaplama ===")
    # 10 m³ betonarme için beklenen demir miktarı
    expected_demir = get_expected_material_quantity("betonarme", "demir", 10.0, "m³")
    print(f"10 m³ betonarme için beklenen demir: {expected_demir} ton")
