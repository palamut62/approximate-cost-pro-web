"""
İnşaat Malzeme Analizi Validasyon Dataset'i
===========================================

AI ve hibrit analiz sisteminin doğruluğunu test etmek için kullanılır.
Gerçek inşaat senaryolarından oluşan test case'leri içerir.

Her test case şunları içerir:
- Input: Poz açıklaması, miktar, birim
- Expected: Beklenen malzemeler, işçilikler, nakliye
- Tolerances: Kabul edilebilir miktar aralıkları
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class TestSeverity(Enum):
    """Test başarısızlık ciddiyeti"""
    CRITICAL = "critical"  # Zorunlu malzeme eksik
    WARNING = "warning"  # Opsiyonel malzeme veya miktar farkı
    INFO = "info"  # Bilgi amaçlı


@dataclass
class ValidationCase:
    """Validasyon test case yapısı"""
    id: str
    description: str  # Test açıklaması
    input_poz: str  # Poz açıklaması
    input_quantity: float
    input_unit: str
    expected_construction_type: str  # Beklenen imalat tipi
    expected_materials: List[Dict[str, Any]]  # Beklenen malzemeler
    expected_labor: List[str]  # Beklenen işçilikler
    expected_transport: bool  # Nakliye zorunlu mu?
    notes: str = ""


# ============================================
# BETONARME İMALATI TEST CASE'LERİ
# ============================================

BETONARME_CASES = [
    ValidationCase(
        id="BA-001",
        description="Standart betonarme temel - C25/30",
        input_poz="C25/30 betonarme temel",
        input_quantity=10.0,
        input_unit="m³",
        expected_construction_type="betonarme",
        expected_materials=[
            {
                "name_contains": "beton",
                "name_pattern": ".*c25.*30.*",
                "unit": "m³",
                "quantity_min": 9.5,
                "quantity_max": 10.5,
                "is_mandatory": True
            },
            {
                "name_contains": "demir",
                "unit": "ton",
                "quantity_min": 0.8,  # %8 donatı oranı
                "quantity_max": 2.0,  # %20 donatı oranı
                "is_mandatory": True
            },
            {
                "name_contains": "kalıp",
                "unit": "m²",
                "quantity_min": 20.0,  # Minimum yüzey alanı
                "is_mandatory": True
            }
        ],
        expected_labor=["betoncu", "demirci", "kalıpçı"],
        expected_transport=True,
        notes="Standart betonarme için beton+demir+kalıp zorunludur"
    ),

    ValidationCase(
        id="BA-002",
        description="Yüksek donatılı betonarme kolon - C30/37",
        input_poz="C30/37 betonarme kolon",
        input_quantity=5.0,
        input_unit="m³",
        expected_construction_type="betonarme",
        expected_materials=[
            {
                "name_contains": "beton",
                "unit": "m³",
                "quantity_min": 4.8,
                "quantity_max": 5.2,
                "is_mandatory": True
            },
            {
                "name_contains": "demir",
                "unit": "ton",
                "quantity_min": 0.6,  # Kolonlar için minimum %12
                "quantity_max": 1.0,  # Maksimum %20
                "is_mandatory": True
            },
            {
                "name_contains": "kalıp",
                "unit": "m²",
                "is_mandatory": True
            }
        ],
        expected_labor=["betoncu", "demirci", "kalıpçı"],
        expected_transport=True,
        notes="Kolonlar genelde yüksek donatı oranına sahiptir"
    ),

    ValidationCase(
        id="BA-003",
        description="Betonarme döşeme - hasır donatılı",
        input_poz="C25/30 betonarme döşeme, hasır donatılı",
        input_quantity=100.0,
        input_unit="m²",
        expected_construction_type="betonarme",
        expected_materials=[
            {
                "name_contains": "beton",
                "unit": "m³",
                "quantity_min": 10.0,  # 10 cm döşeme
                "quantity_max": 20.0,  # 20 cm döşeme
                "is_mandatory": True
            },
            {
                "name_contains": "demir",
                "unit": "ton",
                "quantity_min": 1.0,
                "is_mandatory": True
            },
            {
                "name_contains": "kalıp",
                "unit": "m²",
                "quantity_min": 100.0,
                "is_mandatory": True
            }
        ],
        expected_labor=["betoncu", "demirci", "kalıpçı"],
        expected_transport=True
    )
]


# ============================================
# BETON İMALATI TEST CASE'LERİ
# ============================================

BETON_CASES = [
    ValidationCase(
        id="BE-001",
        description="Düz beton - yalın beton",
        input_poz="C20/25 düz beton döşeme",
        input_quantity=15.0,
        input_unit="m³",
        expected_construction_type="beton_imalati",
        expected_materials=[
            {
                "name_contains": "beton",
                "unit": "m³",
                "quantity_min": 14.5,
                "quantity_max": 15.5,
                "is_mandatory": True
            },
            {
                "name_contains": "kalıp",
                "unit": "m²",
                "is_mandatory": True
            }
        ],
        expected_labor=["betoncu"],
        expected_transport=True,
        notes="Düz beton - demir olmamalı"
    ),

    ValidationCase(
        id="BE-002",
        description="Yalın beton temel",
        input_poz="Yalın beton temel",
        input_quantity=8.0,
        input_unit="m³",
        expected_construction_type="beton_imalati",
        expected_materials=[
            {
                "name_contains": "beton",
                "unit": "m³",
                "quantity_min": 7.5,
                "quantity_max": 8.5,
                "is_mandatory": True
            }
        ],
        expected_labor=["betoncu"],
        expected_transport=True
    )
]


# ============================================
# KAGİR DUVAR TEST CASE'LERİ
# ============================================

KAGIR_CASES = [
    ValidationCase(
        id="KA-001",
        description="Tuğla duvar - delikli tuğla",
        input_poz="Delikli tuğla duvar",
        input_quantity=50.0,
        input_unit="m²",
        expected_construction_type="kagir_duvar",
        expected_materials=[
            {
                "name_contains": "tuğla",
                "unit": "adet",
                "quantity_min": 3000,  # ~60 adet/m²
                "quantity_max": 4000,  # ~80 adet/m²
                "is_mandatory": True
            },
            {
                "name_contains": "harç",
                "unit": "m³",
                "quantity_min": 10.0,
                "quantity_max": 15.0,
                "is_mandatory": True
            }
        ],
        expected_labor=["duvarcı"],
        expected_transport=True,
        notes="Tuğla duvar için tuğla+harç zorunludur"
    ),

    ValidationCase(
        id="KA-002",
        description="Gazbeton duvar",
        input_poz="Gazbeton duvar imalatı",
        input_quantity=75.0,
        input_unit="m²",
        expected_construction_type="kagir_duvar",
        expected_materials=[
            {
                "name_contains": ["gazbeton", "blok"],
                "unit": "adet",
                "is_mandatory": True
            },
            {
                "name_contains": "harç",
                "unit": "m³",
                "is_mandatory": True
            }
        ],
        expected_labor=["duvarcı"],
        expected_transport=True
    )
]


# ============================================
# HAFRİYAT VE DOLGU TEST CASE'LERİ
# ============================================

EARTHWORK_CASES = [
    ValidationCase(
        id="HA-001",
        description="Temel hafriyatı - kazı",
        input_poz="Temel hafriyatı kazısı",
        input_quantity=100.0,
        input_unit="m³",
        expected_construction_type="hafriyat",
        expected_materials=[],  # Hafriyat için malzeme gerekmez
        expected_labor=["makinist"],
        expected_transport=True,  # Hafriyat nakli gerekir
        notes="Hafriyat için malzeme yok, nakliye var"
    ),

    ValidationCase(
        id="DO-001",
        description="Kum dolgu ve sıkıştırma",
        input_poz="Kum dolgu ve sıkıştırma",
        input_quantity=50.0,
        input_unit="m³",
        expected_construction_type="dolgu",
        expected_materials=[
            {
                "name_contains": "kum",
                "unit": "m³",
                "quantity_min": 48.0,
                "quantity_max": 55.0,  # Sıkışma payı
                "is_mandatory": True
            }
        ],
        expected_labor=["kompaktör"],
        expected_transport=True
    )
]


# ============================================
# TÜM TEST CASE'LERİ
# ============================================

ALL_VALIDATION_CASES = (
    BETONARME_CASES +
    BETON_CASES +
    KAGIR_CASES +
    EARTHWORK_CASES
)


# ============================================
# VALİDASYON FONKSİYONLARI
# ============================================

def validate_material(
    material: Dict[str, Any],
    expected: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Tek bir malzemeyi beklenen değerlerle karşılaştır

    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str]
        }
    """
    errors = []
    warnings = []

    material_name = material.get("name", "").lower()

    # İsim kontrolü
    name_contains = expected.get("name_contains")
    if isinstance(name_contains, list):
        if not any(kw in material_name for kw in name_contains):
            errors.append(f"Malzeme adı '{name_contains}' içermiyor")
    elif name_contains:
        if name_contains.lower() not in material_name:
            errors.append(f"Malzeme adı '{name_contains}' içermiyor")

    # Pattern kontrolü
    name_pattern = expected.get("name_pattern")
    if name_pattern:
        import re
        if not re.search(name_pattern, material_name):
            errors.append(f"Malzeme adı pattern'e uymuyor: {name_pattern}")

    # Birim kontrolü
    expected_unit = expected.get("unit")
    if expected_unit:
        material_unit = material.get("unit", "").lower()
        if material_unit not in [expected_unit.lower(), expected_unit.replace("²", "2").lower()]:
            errors.append(f"Birim uyumsuzluğu: beklenen {expected_unit}, bulunan {material_unit}")

    # Miktar kontrolü
    quantity_min = expected.get("quantity_min")
    quantity_max = expected.get("quantity_max")
    if quantity_min is not None or quantity_max is not None:
        material_quantity = material.get("quantity", 0)

        if quantity_min is not None and material_quantity < quantity_min:
            warnings.append(f"Miktar çok düşük: {material_quantity} < {quantity_min}")

        if quantity_max is not None and material_quantity > quantity_max:
            warnings.append(f"Miktar çok yüksek: {material_quantity} > {quantity_max}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def run_validation_test(
    test_case: ValidationCase,
    analysis_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analiz sonucunu test case ile karşılaştır

    Args:
        test_case: ValidationCase
        analysis_result: Hibrit analiz sonucu

    Returns:
        {
            "passed": bool,
            "score": float,  # 0-100
            "errors": List[str],
            "warnings": List[str],
            "details": Dict
        }
    """
    errors = []
    warnings = []
    details = {}

    components = analysis_result.get("components", [])
    construction_type = analysis_result.get("construction_type", "")

    # 1. İmalat tipi kontrolü
    if construction_type != test_case.expected_construction_type:
        errors.append(
            f"İmalat tipi yanlış: beklenen '{test_case.expected_construction_type}', "
            f"bulunan '{construction_type}'"
        )
        details["construction_type"] = "FAILED"
    else:
        details["construction_type"] = "PASSED"

    # 2. Malzeme kontrolü
    materials = [c for c in components if c.get("type", "").lower() == "malzeme"]
    material_results = []

    for expected_mat in test_case.expected_materials:
        # Bu malzeme var mı?
        found = False
        for material in materials:
            result = validate_material(material, expected_mat)
            if result["valid"]:
                found = True
                material_results.append({
                    "material": material["name"],
                    "status": "FOUND",
                    "warnings": result["warnings"]
                })
                warnings.extend(result["warnings"])
                break

        if not found and expected_mat.get("is_mandatory", False):
            errors.append(f"Zorunlu malzeme eksik: {expected_mat.get('name_contains', 'Unknown')}")
            material_results.append({
                "material": expected_mat.get('name_contains', 'Unknown'),
                "status": "MISSING",
                "severity": "CRITICAL"
            })

    details["materials"] = material_results

    # 3. İşçilik kontrolü
    labor_components = [c for c in components if c.get("type", "").lower() in ["işçilik", "iscilik"]]
    labor_names = [l.get("name", "").lower() for l in labor_components]

    missing_labor = []
    for expected_labor in test_case.expected_labor:
        if not any(expected_labor.lower() in name for name in labor_names):
            missing_labor.append(expected_labor)

    if missing_labor:
        warnings.append(f"Eksik işçilikler: {', '.join(missing_labor)}")
        details["labor"] = "INCOMPLETE"
    else:
        details["labor"] = "PASSED"

    # 4. Nakliye kontrolü
    has_transport = any(c.get("type", "").lower() == "nakliye" for c in components)

    if test_case.expected_transport and not has_transport:
        errors.append("Nakliye eksik (zorunlu)")
        details["transport"] = "MISSING"
    else:
        details["transport"] = "PASSED" if has_transport else "NOT_REQUIRED"

    # 5. Skor hesaplama
    total_checks = 4  # construction_type, materials, labor, transport
    passed_checks = sum([
        1 if details["construction_type"] == "PASSED" else 0,
        1 if len([m for m in material_results if m["status"] == "FOUND"]) == len(test_case.expected_materials) else 0,
        1 if details["labor"] == "PASSED" else 0,
        1 if details["transport"] in ["PASSED", "NOT_REQUIRED"] else 0
    ])

    score = (passed_checks / total_checks) * 100

    return {
        "test_id": test_case.id,
        "test_description": test_case.description,
        "passed": len(errors) == 0,
        "score": score,
        "errors": errors,
        "warnings": warnings,
        "details": details
    }


def run_all_tests(analyzer, verbose: bool = True) -> Dict[str, Any]:
    """
    Tüm validasyon testlerini çalıştır

    Args:
        analyzer: HybridAnalyzer instance
        verbose: Detaylı çıktı

    Returns:
        Test sonuçları özeti
    """
    results = []
    total_score = 0

    for test_case in ALL_VALIDATION_CASES:
        # Analiz yap
        analysis = analyzer.analyze(
            description=test_case.input_poz,
            quantity=test_case.input_quantity,
            unit=test_case.input_unit
        )

        # Validasyon yap
        result = run_validation_test(test_case, analysis)
        results.append(result)
        total_score += result["score"]

        if verbose:
            status = "✅ PASSED" if result["passed"] else "❌ FAILED"
            print(f"{status} | {result['test_id']} | {result['test_description']} | Score: {result['score']:.1f}%")

            if result["errors"]:
                for error in result["errors"]:
                    print(f"  ❌ {error}")

            if result["warnings"]:
                for warning in result["warnings"]:
                    print(f"  ⚠️  {warning}")

            print()

    # Özet
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count
    avg_score = total_score / len(results) if results else 0

    summary = {
        "total_tests": len(results),
        "passed": passed_count,
        "failed": failed_count,
        "average_score": avg_score,
        "results": results
    }

    if verbose:
        print("=" * 60)
        print(f"TOPLAM: {passed_count}/{len(results)} test başarılı")
        print(f"Ortalama Skor: {avg_score:.1f}%")
        print("=" * 60)

    return summary


# ============================================
# TEST ÇALIŞTIRMA
# ============================================

if __name__ == "__main__":
    print("=== İnşaat Malzeme Analizi Validasyon Testleri ===\n")

    # HybridAnalyzer'ı import et ve test et
    try:
        from core.hybrid_analyzer import HybridAnalyzer

        analyzer = HybridAnalyzer()
        summary = run_all_tests(analyzer, verbose=True)

        # JSON çıktı
        import json
        with open("validation_results.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\nSonuçlar 'validation_results.json' dosyasına kaydedildi.")

    except ImportError as e:
        print(f"Hata: {e}")
        print("core.hybrid_analyzer modülü bulunamadı.")
