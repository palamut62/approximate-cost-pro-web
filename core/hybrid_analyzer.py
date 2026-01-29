"""
Hibrit Analiz Sistemi
====================

Kural tabanlı sistem + AI analizini birleştirir.
Güvenilir, tutarlı ve akıllı malzeme analizi sağlar.

Çalışma Mantığı:
1. İmalat tipi tespit edilir (betonarme, beton, kalıp vb.)
2. Zorunlu malzemeler kural tabanlı olarak eklenir
3. AI ek analiz yapar (miktar hesaplamaları, opsiyonel malzemeler)
4. Sonuçlar birleştirilir
5. Eksiklik kontrolü yapılır
6. Güven skoru hesaplanır
7. Düşük güvenli malzemeler kullanıcı onayına sunulur
"""

from typing import Dict, List, Any, Optional, Tuple
from core.material_ontology import (
    detect_construction_type,
    get_material_rules,
    validate_material_completeness,
    get_expected_material_quantity,
    MaterialRule,
    LaborRule
)
from core.confidence_scorer import ConfidenceScorer
import json


class HybridAnalyzer:
    """Hibrit analiz motoru"""

    def __init__(self, poz_data: Dict = None, db_manager=None):
        """
        Args:
            poz_data: CSV poz veritabanı
            db_manager: DatabaseManager instance
        """
        self.poz_data = poz_data or {}
        self.db_manager = db_manager
        self.confidence_scorer = ConfidenceScorer(poz_data=poz_data, db_manager=db_manager)

    def analyze(
        self,
        description: str,
        quantity: float,
        unit: str,
        ai_components: List[Dict[str, Any]] = None,
        ai_explanation: str = "",
        strict_validation: bool = False
    ) -> Dict[str, Any]:
        """
        Hibrit analiz yap: Kural tabanlı + AI

        Args:
            description: Poz açıklaması (ör: "C25/30 betonarme temel")
            quantity: Miktar (ör: 10)
            unit: Birim (ör: "m³")
            ai_components: AI'den gelen bileşenler (opsiyonel - yoksa sadece kural tabanlı)
            ai_explanation: AI açıklaması
            strict_validation: Katı validasyon modu

        Returns:
            {
                "components": List[Dict],  # Birleştirilmiş malzemeler
                "explanation": str,  # Açıklama
                "construction_type": str,  # İmalat tipi
                "validation": Dict,  # Validasyon sonucu
                "requires_review": bool,  # Kullanıcı onayı gerekli mi?
                "review_materials": List[Dict],  # Onay gereken malzemeler
                "rule_based_count": int,  # Kural tabanlı malzeme sayısı
                "ai_count": int  # AI'den gelen malzeme sayısı
            }
        """
        # 1. İMALAT TİPİ TESPİTİ
        construction_type = detect_construction_type(description)

        # 2. KURAL TABANLI MALZEMELER
        rule_based_materials = []
        rule_based_labor = []
        rule_based_names = []

        if construction_type:
            rules = get_material_rules(construction_type)
            if rules:
                # Zorunlu malzemeleri ekle
                rule_based_materials = self._apply_material_rules(
                    rules.materials,
                    quantity,
                    unit,
                    description
                )
                rule_based_names = [m["name"] for m in rule_based_materials]

                # Zorunlu işçilikleri ekle
                rule_based_labor = self._apply_labor_rules(
                    rules.labor,
                    quantity,
                    unit
                )

        # 3. AI BİLEŞENLERİNİ AYIR
        ai_materials = []
        ai_labor = []
        ai_transport = []
        ai_machinery = []

        if ai_components:
            for comp in ai_components:
                comp_type = comp.get("type", "").lower()

                # Eğer AI'nin önerdiği malzeme kural tabanlı listede yoksa ekle
                if comp_type == "malzeme":
                    # Duplicate kontrolü
                    if not self._is_duplicate(comp, rule_based_materials):
                        ai_materials.append(comp)

                elif comp_type in ["işçilik", "iscilik"]:
                    if not self._is_duplicate(comp, rule_based_labor):
                        ai_labor.append(comp)

                elif comp_type == "nakliye":
                    ai_transport.append(comp)

                elif comp_type == "makine":
                    ai_machinery.append(comp)

        # 4. BİRLEŞTİR
        combined_materials = rule_based_materials + ai_materials
        combined_labor = rule_based_labor + ai_labor
        all_components = combined_materials + combined_labor + ai_transport + ai_machinery

        # 5. VALİDASYON
        validation = validate_material_completeness(
            construction_type=construction_type or "unknown",
            materials=all_components,
            labor=combined_labor,
            strict_mode=strict_validation
        )

        # 6. EKSİK MALZEME VARSA UYAR
        if not validation["valid"]:
            missing_info = []
            if validation["missing_materials"]:
                missing_info.append(f"Eksik malzemeler: {', '.join(validation['missing_materials'])}")
            if validation["missing_labor"]:
                missing_info.append(f"Eksik işçilikler: {', '.join(validation['missing_labor'])}")
            if validation["missing_transport"]:
                missing_info.append("Nakliye eksik")

            # Açıklamaya ekle
            validation_warning = "\n\n⚠️ VALİDASYON UYARISI:\n" + "\n".join(f"- {info}" for info in missing_info)
        else:
            validation_warning = "\n\n✅ Validasyon başarılı: Tüm zorunlu malzemeler mevcut."

        # 7. GÜVEN SKORU HESAPLA
        scored_components = self.confidence_scorer.score_all_materials(
            materials=all_components,
            construction_type=construction_type,
            rule_based_materials=rule_based_names,
            description=description,
            unit=unit
        )

        # 8. ONAY GEREKENLERİ AYIR
        review_materials = self.confidence_scorer.get_materials_requiring_review(scored_components)
        requires_review = len(review_materials) > 0

        # 9. AÇIKLAMA OLUŞTUR
        explanation_parts = []

        if construction_type:
            explanation_parts.append(f"🏗️ İmalat Tipi: {construction_type.upper()}")

        if rule_based_materials:
            explanation_parts.append(
                f"✅ Kural tabanlı sistem {len(rule_based_materials)} zorunlu malzeme ekledi: "
                f"{', '.join(rule_based_names)}"
            )

        if ai_materials:
            explanation_parts.append(
                f"🤖 AI {len(ai_materials)} ek malzeme önerdi"
            )

        if ai_explanation:
            explanation_parts.append(f"\n💡 AI Açıklaması:\n{ai_explanation}")

        explanation_parts.append(validation_warning)

        if requires_review:
            explanation_parts.append(
                f"\n⚠️ {len(review_materials)} malzeme düşük güven skoruna sahip - manuel kontrol önerilir."
            )

        combined_explanation = "\n".join(explanation_parts)

        # 10. SONUÇ
        return {
            "components": scored_components,
            "explanation": combined_explanation,
            "construction_type": construction_type or "unknown",
            "validation": validation,
            "requires_review": requires_review,
            "review_materials": review_materials,
            "rule_based_count": len(rule_based_materials),
            "ai_count": len(ai_materials),
            "total_count": len(scored_components)
        }

    def _apply_material_rules(
        self,
        material_rules: List[MaterialRule],
        quantity: float,
        unit: str,
        description: str
    ) -> List[Dict[str, Any]]:
        """Malzeme kurallarını uygula ve bileşen listesi oluştur"""
        materials = []

        for rule in material_rules:
            if not rule.is_mandatory:
                continue

            # Miktar hesaplama
            if rule.coefficient is not None:
                calculated_quantity = quantity * rule.coefficient
            elif rule.coefficient_formula == "surface_area":
                # Yüzey alanı hesaplaması - şimdilik basit yaklaşım
                # Gerçek uygulamada geometrik hesaplama yapılmalı
                calculated_quantity = quantity * 6.0  # Ortalama 6 yüz (küp varsayımı)
            elif rule.coefficient_formula == "wall_area_to_brick":
                # Tuğla hesaplaması (m² başına ~65 tuğla)
                calculated_quantity = quantity * 65
            else:
                calculated_quantity = quantity

            # Poz kodu tahmini
            poz_code = self._find_best_poz_code(
                rule.material_type,
                rule.poz_pattern,
                description
            )

            material = {
                "type": "Malzeme",
                "code": poz_code or rule.poz_pattern or "",
                "name": self._generate_material_name(rule.material_type, description),
                "unit": rule.unit,
                "quantity": round(calculated_quantity, 2),
                "unit_price": self._estimate_unit_price(rule.material_type, poz_code),
                "notes": rule.notes,
                "source": "rule_based"
            }

            materials.append(material)

        return materials

    def _apply_labor_rules(
        self,
        labor_rules: List[LaborRule],
        quantity: float,
        unit: str
    ) -> List[Dict[str, Any]]:
        """İşçilik kurallarını uygula"""
        labor_list = []

        for rule in labor_rules:
            if not rule.is_mandatory:
                continue

            # Basit işçilik tahmini (gerçek uygulamada daha detaylı olmalı)
            estimated_hours = quantity * 0.5  # m³/m² başına 0.5 saat varsayımı

            labor = {
                "type": "İşçilik",
                "code": rule.poz_pattern or "01.000.0000",
                "name": rule.labor_type.capitalize(),
                "unit": rule.unit,
                "quantity": round(estimated_hours, 2),
                "unit_price": 150.0,  # Ortalama saat ücreti
                "notes": rule.notes,
                "source": "rule_based"
            }

            labor_list.append(labor)

        return labor_list

    def _is_duplicate(self, component: Dict, existing_list: List[Dict]) -> bool:
        """Bileşenin listede zaten var olup olmadığını kontrol et"""
        comp_name = component.get("name", "").lower()
        comp_type = component.get("type", "").lower()

        for existing in existing_list:
            existing_name = existing.get("name", "").lower()
            existing_type = existing.get("type", "").lower()

            # Tip ve isim benzerliği kontrolü
            if existing_type == comp_type:
                # Anahtar kelime eşleşmesi
                comp_keywords = set(comp_name.split())
                existing_keywords = set(existing_name.split())
                overlap = comp_keywords.intersection(existing_keywords)

                if len(overlap) >= 2:  # En az 2 ortak kelime
                    return True

        return False

    def _find_best_poz_code(
        self,
        material_type: str,
        pattern: Optional[str],
        description: str
    ) -> Optional[str]:
        """En uygun poz kodunu bul"""
        if not self.poz_data:
            return None

        # Pattern varsa pattern'e uyan pozları ara
        if pattern:
            pattern_regex = pattern.replace("*", ".*")
            import re
            matches = []

            for poz_code, poz_info in self.poz_data.items():
                if re.match(pattern_regex, poz_code):
                    matches.append((poz_code, poz_info))

            # En uygun eşleşmeyi bul
            if matches:
                # Basit string benzerliği
                best_match = None
                best_score = 0

                for poz_code, poz_info in matches:
                    poz_desc = poz_info.get("description", "").lower()
                    score = sum(1 for word in material_type.split() if word in poz_desc)

                    if score > best_score:
                        best_score = score
                        best_match = poz_code

                return best_match

        return None

    def _generate_material_name(self, material_type: str, description: str) -> str:
        """Malzeme adı oluştur"""
        # Açıklamadan önemli bilgileri çıkar
        desc_lower = description.lower()

        if material_type == "beton":
            # Beton sınıfını bul
            import re
            concrete_class = re.search(r'c\d{2}/\d{2}', desc_lower)
            if concrete_class:
                return f"Beton {concrete_class.group().upper()}"
            return "Beton C25/30"  # Varsayılan

        elif material_type == "demir":
            return "Nervürlü Betonarme Çeliği S420"

        elif material_type == "kalıp":
            if "metal" in desc_lower:
                return "Metal Kalıp"
            return "Ahşap Kalıp"

        elif material_type == "tugla":
            if "gazbeton" in desc_lower:
                return "Gazbeton Blok"
            return "Delikli Tuğla"

        elif material_type == "harç":
            return "Çimento Harcı"

        elif material_type == "kum":
            return "Kum Dolgu"

        else:
            return material_type.capitalize()

    def _estimate_unit_price(self, material_type: str, poz_code: Optional[str]) -> float:
        """Birim fiyat tahmini"""
        # Eğer poz_code varsa ve poz_data'da fiyat varsa onu kullan
        if poz_code and self.poz_data:
            poz_info = self.poz_data.get(poz_code)
            if poz_info:
                price = poz_info.get("unit_price")
                if price:
                    try:
                        return float(price)
                    except:
                        pass

        # Yoksa ortalama fiyat tahmini
        price_estimates = {
            "beton": 1500.0,  # TL/m³
            "demir": 25000.0,  # TL/ton
            "kalıp": 50.0,  # TL/m²
            "tugla": 5.0,  # TL/adet
            "harç": 800.0,  # TL/m³
            "kum": 300.0,  # TL/m³
            "cimento": 3000.0,  # TL/ton
        }

        return price_estimates.get(material_type, 0.0)


# ============================================
# TEST VE ÖRNEK KULLANIM
# ============================================

if __name__ == "__main__":
    print("=== Hibrit Analiz Sistemi Test ===\n")

    # Test POZ data
    test_poz_data = {
        "10.130.1501": {
            "description": "Beton C25/30",
            "unit": "m³",
            "unit_price": "1500"
        },
        "10.140.1001": {
            "description": "Nervürlü Betonarme Çeliği S420",
            "unit": "ton",
            "unit_price": "25000"
        },
        "04.001.1001": {
            "description": "Ahşap Kalıp",
            "unit": "m²",
            "unit_price": "50"
        }
    }

    analyzer = HybridAnalyzer(poz_data=test_poz_data)

    # Test 1: Sadece kural tabanlı
    print("=== TEST 1: Sadece Kural Tabanlı ===")
    result1 = analyzer.analyze(
        description="C25/30 betonarme temel",
        quantity=10.0,
        unit="m³"
    )

    print(f"İmalat Tipi: {result1['construction_type']}")
    print(f"Toplam Bileşen: {result1['total_count']}")
    print(f"Kural Tabanlı: {result1['rule_based_count']}")
    print(f"AI: {result1['ai_count']}")
    print(f"Validasyon: {result1['validation']['valid']}")
    print()

    # Test 2: Hibrit (Kural + AI)
    print("=== TEST 2: Hibrit Analiz ===")
    ai_components = [
        {
            "type": "Malzeme",
            "name": "Kimyasal Katkı",
            "code": "10.130.9999",
            "unit": "kg",
            "quantity": 0.2,
            "unit_price": 50.0
        },
        {
            "type": "Nakliye",
            "name": "Beton Nakliyesi",
            "code": "07.005/K",
            "unit": "ton",
            "quantity": 24.0,
            "unit_price": 12.5
        }
    ]

    result2 = analyzer.analyze(
        description="C25/30 betonarme temel",
        quantity=10.0,
        unit="m³",
        ai_components=ai_components,
        ai_explanation="Standart betonarme analizi yapıldı. Nakliye KGM formülü ile hesaplandı."
    )

    print(f"İmalat Tipi: {result2['construction_type']}")
    print(f"Toplam Bileşen: {result2['total_count']}")
    print(f"Kural Tabanlı: {result2['rule_based_count']}")
    print(f"AI: {result2['ai_count']}")
    print(f"Onay Gerekli: {result2['requires_review']}")
    print(f"\nAçıklama:\n{result2['explanation']}")
    print()

    # Güven skorları
    print("=== Güven Skorları ===")
    for comp in result2['components']:
        conf = comp.get('confidence', {})
        print(f"{comp['name']:<30} | Skor: {conf.get('score', 0):.1f} | Seviye: {conf.get('level', 'N/A')}")
