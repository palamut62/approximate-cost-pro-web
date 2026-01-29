"""
Malzeme Analizi Güven Skoru Sistemi
===================================

Her malzeme için güvenilirlik skoru hesaplar ve kullanıcı onayı gerekip gerekmediğini belirler.

Güven Skoru Bileşenleri:
- Kural tabanlı eşleşme: +50 puan
- CSV poz database tam eşleşme: +30 puan
- Benzer proje eşleşmesi: +20 puan
- AI feedback öğrenmesi: +15 puan
- Birim uyumu: +10 puan
- Malzeme tipi mantığı: +10 puan

Toplam: 0-135 puan arası (100+ mükemmel, 70-100 iyi, 50-70 şüpheli, <50 riskli)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re


class ConfidenceLevel(Enum):
    """Güven seviyeleri"""
    EXCELLENT = "excellent"  # 100+
    GOOD = "good"  # 70-100
    QUESTIONABLE = "questionable"  # 50-70
    RISKY = "risky"  # <50


@dataclass
class ConfidenceScore:
    """Güven skoru detayı"""
    total_score: float  # Toplam skor
    level: ConfidenceLevel  # Güven seviyesi
    requires_review: bool  # Kullanıcı onayı gerekli mi?
    breakdown: Dict[str, float]  # Skor dağılımı
    reasons: List[str]  # Açıklamalar
    suggestions: List[str]  # İyileştirme önerileri


class ConfidenceScorer:
    """Güven skoru hesaplayıcı"""

    def __init__(self, poz_data: Dict = None, db_manager=None):
        """
        Args:
            poz_data: CSV poz veritabanı
            db_manager: DatabaseManager instance (feedback için)
        """
        self.poz_data = poz_data or {}
        self.db_manager = db_manager

    def calculate_confidence(
        self,
        material: Dict[str, Any],
        construction_type: Optional[str] = None,
        is_rule_based: bool = False,
        description: str = "",
        unit: str = ""
    ) -> ConfidenceScore:
        """
        Malzeme için güven skoru hesapla

        Args:
            material: Malzeme dict {"name": "...", "type": "...", "code": "...", ...}
            construction_type: İmalat tipi (ör: "betonarme")
            is_rule_based: Kural tabanlı sistem tarafından mı eklendi?
            description: Poz açıklaması
            unit: Birim

        Returns:
            ConfidenceScore
        """
        score = 0.0
        breakdown = {}
        reasons = []
        suggestions = []

        # 1. KURAL TABANLI EŞLEŞMESİ (+50)
        if is_rule_based:
            points = 50
            score += points
            breakdown["rule_based"] = points
            reasons.append("Kural tabanlı sistemden geldi (zorunlu malzeme)")
        else:
            breakdown["rule_based"] = 0

        # 2. CSV POZ DATABASE TAM EŞLEŞMESİ (+30)
        poz_match_score = self._check_poz_database_match(material)
        score += poz_match_score
        breakdown["poz_database"] = poz_match_score
        if poz_match_score > 20:
            reasons.append(f"CSV veritabanında güçlü eşleşme bulundu ({poz_match_score} puan)")
        elif poz_match_score > 0:
            reasons.append(f"CSV veritabanında kısmi eşleşme ({poz_match_score} puan)")
        else:
            suggestions.append("CSV veritabanında eşleşme bulunamadı - manuel kontrol önerilir")

        # 3. BENZERİ PROJE EŞLEŞMESİ (+20)
        similar_project_score = self._check_similar_projects(material, construction_type)
        score += similar_project_score
        breakdown["similar_projects"] = similar_project_score
        if similar_project_score > 0:
            reasons.append(f"Benzer projelerde kullanılmış ({similar_project_score} puan)")

        # 4. AI FEEDBACK ÖĞRENMESI (+15)
        feedback_score = self._check_feedback_history(material, description, unit)
        score += feedback_score
        breakdown["feedback_learning"] = feedback_score
        if feedback_score > 0:
            reasons.append(f"Geçmiş kullanıcı düzeltmelerinden öğrenildi ({feedback_score} puan)")

        # 5. BİRİM UYUMU (+10)
        unit_match_score = self._check_unit_consistency(material, construction_type)
        score += unit_match_score
        breakdown["unit_consistency"] = unit_match_score
        if unit_match_score == 10:
            reasons.append("Birim tutarlı ve uygun")
        elif unit_match_score > 0:
            reasons.append("Birim kabul edilebilir")
        else:
            suggestions.append(f"Birim uyumsuzluğu var: {material.get('unit', 'N/A')}")

        # 6. MALZEME TİPİ MANTIĞI (+10)
        logic_score = self._check_material_logic(material, construction_type, description)
        score += logic_score
        breakdown["material_logic"] = logic_score
        if logic_score > 5:
            reasons.append("Malzeme tipi mantıklı")
        else:
            suggestions.append("Malzeme seçimi beklenmedik - kontrol ediniz")

        # GÜVEN SEVİYESİ BELİRLE
        if score >= 100:
            level = ConfidenceLevel.EXCELLENT
            requires_review = False
        elif score >= 70:
            level = ConfidenceLevel.GOOD
            requires_review = False
        elif score >= 50:
            level = ConfidenceLevel.QUESTIONABLE
            requires_review = True
            suggestions.append("Orta düzey güven - manuel kontrol önerilir")
        else:
            level = ConfidenceLevel.RISKY
            requires_review = True
            suggestions.append("⚠️ Düşük güven - mutlaka kontrol ediniz!")

        return ConfidenceScore(
            total_score=score,
            level=level,
            requires_review=requires_review,
            breakdown=breakdown,
            reasons=reasons,
            suggestions=suggestions
        )

    def _check_poz_database_match(self, material: Dict) -> float:
        """CSV poz database'inde eşleşme kontrolü"""
        if not self.poz_data:
            return 0.0

        poz_code = material.get("code", "")
        material_name = material.get("name", "").lower()

        # Tam poz kodu eşleşmesi
        if poz_code and poz_code in self.poz_data:
            poz_info = self.poz_data[poz_code]
            # İsim benzerliği kontrol et
            db_name = poz_info.get("description", "").lower()
            similarity = self._calculate_similarity(material_name, db_name)

            if similarity > 0.8:
                return 30.0  # Tam eşleşme
            elif similarity > 0.5:
                return 20.0  # İyi eşleşme
            else:
                return 10.0  # Zayıf eşleşme

        # Poz kodu yok ama isim benzerliği var mı?
        best_similarity = 0.0
        for poz_info in self.poz_data.values():
            db_name = poz_info.get("description", "").lower()
            similarity = self._calculate_similarity(material_name, db_name)
            best_similarity = max(best_similarity, similarity)

        if best_similarity > 0.7:
            return 15.0
        elif best_similarity > 0.5:
            return 10.0
        elif best_similarity > 0.3:
            return 5.0

        return 0.0

    def _check_similar_projects(self, material: Dict, construction_type: Optional[str]) -> float:
        """Benzer projelerde kullanılmış mı kontrol et"""
        if not self.db_manager:
            return 0.0

        try:
            # Database'den benzer analizleri çek
            # NOT: Bu özellik için database query gerekir
            # Şimdilik basit bir yaklaşım kullanıyoruz
            return 0.0  # TODO: Implement similar project matching
        except:
            return 0.0

    def _check_feedback_history(self, material: Dict, description: str, unit: str) -> float:
        """Kullanıcı feedback geçmişini kontrol et"""
        if not self.db_manager:
            return 0.0

        try:
            # Geçmiş düzeltmeleri kontrol et
            feedback_list = self.db_manager.get_relevant_feedback(description, unit, limit=5)

            if not feedback_list:
                return 0.0

            material_name = material.get("name", "").lower()

            # Feedback'lerde bu malzeme kullanılmış mı?
            for feedback in feedback_list:
                correct_components = feedback.get("correct_components", {})
                if isinstance(correct_components, str):
                    import json
                    correct_components = json.loads(correct_components)

                components = correct_components.get("components", [])
                for comp in components:
                    if material_name in comp.get("name", "").lower():
                        return 15.0  # Feedback'den öğrenildi

            return 5.0  # Benzer pozlar için feedback var ama bu malzeme yok

        except:
            return 0.0

    def _check_unit_consistency(self, material: Dict, construction_type: Optional[str]) -> float:
        """Birim tutarlılığı kontrolü"""
        unit = material.get("unit", "").lower()
        material_type = material.get("type", "").lower()
        material_name = material.get("name", "").lower()

        # Malzeme birim kontrolü
        if material_type == "malzeme":
            # Beton → m³
            if any(keyword in material_name for keyword in ["beton", "harç"]):
                return 10.0 if unit in ["m³", "m3"] else 0.0

            # Demir → ton/kg
            if any(keyword in material_name for keyword in ["demir", "donatı", "çelik"]):
                return 10.0 if unit in ["ton", "kg"] else 0.0

            # Tuğla → adet
            if any(keyword in material_name for keyword in ["tuğla", "briket", "blok"]):
                return 10.0 if unit in ["adet", "ad"] else 5.0

            # Kalıp → m²
            if "kalıp" in material_name:
                return 10.0 if unit in ["m²", "m2"] else 0.0

            return 5.0  # Genel malzeme, kabul edilebilir

        # İşçilik birim kontrolü
        elif material_type in ["işçilik", "iscilik"]:
            return 10.0 if unit in ["sa", "saat", "gün"] else 5.0

        # Nakliye birim kontrolü
        elif material_type == "nakliye":
            return 10.0 if unit in ["ton", "m³", "m3"] else 5.0

        # Makine birim kontrolü
        elif material_type == "makine":
            return 10.0 if unit in ["sa", "saat"] else 5.0

        return 5.0

    def _check_material_logic(
        self,
        material: Dict,
        construction_type: Optional[str],
        description: str
    ) -> float:
        """Malzeme mantığı kontrolü"""
        material_name = material.get("name", "").lower()
        desc_lower = description.lower()

        # Betonarme kontrolü
        if construction_type == "betonarme" or "betonarme" in desc_lower:
            # Beton, demir, kalıp varsa mantıklı
            if any(kw in material_name for kw in ["beton", "demir", "kalıp", "donatı"]):
                return 10.0
            # Diğer malzemeler şüpheli
            return 3.0

        # Tuğla duvar kontrolü
        if "tuğla" in desc_lower or "duvar" in desc_lower:
            if any(kw in material_name for kw in ["tuğla", "harç", "briket"]):
                return 10.0
            return 3.0

        # Kalıp işleri
        if "kalıp" in desc_lower:
            if "kalıp" in material_name:
                return 10.0
            return 3.0

        # Genel durum
        return 5.0

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """İki metin arasında benzerlik hesapla (0.0-1.0)"""
        if not text1 or not text2:
            return 0.0

        # Basit kelime tabanlı benzerlik
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def score_all_materials(
        self,
        materials: List[Dict[str, Any]],
        construction_type: Optional[str] = None,
        rule_based_materials: List[str] = None,
        description: str = "",
        unit: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Tüm malzemelere güven skoru ekle

        Args:
            materials: Malzeme listesi
            construction_type: İmalat tipi
            rule_based_materials: Kural tabanlı malzeme isimleri listesi
            description: Poz açıklaması
            unit: Birim

        Returns:
            Skorlanmış malzeme listesi (her malzemeye confidence field eklenir)
        """
        rule_based_materials = rule_based_materials or []
        scored_materials = []

        for material in materials:
            is_rule_based = material.get("name", "") in rule_based_materials

            confidence = self.calculate_confidence(
                material=material,
                construction_type=construction_type,
                is_rule_based=is_rule_based,
                description=description,
                unit=unit
            )

            # Malzeme'ye confidence bilgisini ekle
            material_with_score = material.copy()
            material_with_score["confidence"] = {
                "score": confidence.total_score,
                "level": confidence.level.value,
                "requires_review": confidence.requires_review,
                "breakdown": confidence.breakdown,
                "reasons": confidence.reasons,
                "suggestions": confidence.suggestions
            }

            scored_materials.append(material_with_score)

        return scored_materials

    def get_materials_requiring_review(
        self,
        materials: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Kullanıcı onayı gereken malzemeleri filtrele"""
        return [
            m for m in materials
            if m.get("confidence", {}).get("requires_review", False)
        ]


# ============================================
# TEST VE ÖRNEK KULLANIM
# ============================================

if __name__ == "__main__":
    print("=== Güven Skoru Sistemi Test ===\n")

    # Test POZ data
    test_poz_data = {
        "10.130.1501": {
            "description": "Beton C25/30",
            "unit": "m³",
            "unit_price": 1500
        },
        "10.140.1001": {
            "description": "Nervürlü Betonarme Çeliği S420",
            "unit": "ton",
            "unit_price": 25000
        }
    }

    scorer = ConfidenceScorer(poz_data=test_poz_data)

    # Test malzemeler
    test_materials = [
        {
            "name": "Beton C25/30",
            "type": "Malzeme",
            "code": "10.130.1501",
            "unit": "m³",
            "quantity": 10
        },
        {
            "name": "Betonarme Demiri S420",
            "type": "Malzeme",
            "code": "10.140.1001",
            "unit": "ton",
            "quantity": 1.2
        },
        {
            "name": "Gizemli Malzeme X",
            "type": "Malzeme",
            "code": "",
            "unit": "adet",
            "quantity": 100
        }
    ]

    # Skorlama
    scored = scorer.score_all_materials(
        materials=test_materials,
        construction_type="betonarme",
        rule_based_materials=["Beton C25/30", "Betonarme Demiri S420"],
        description="C25/30 betonarme temel",
        unit="m³"
    )

    # Sonuçları göster
    for material in scored:
        conf = material["confidence"]
        print(f"Malzeme: {material['name']}")
        print(f"  Skor: {conf['score']:.1f} / 135")
        print(f"  Seviye: {conf['level']}")
        print(f"  Onay Gerekli: {conf['requires_review']}")
        print(f"  Breakdown: {conf['breakdown']}")
        print(f"  Nedenler: {', '.join(conf['reasons'])}")
        if conf['suggestions']:
            print(f"  Öneriler: {', '.join(conf['suggestions'])}")
        print()

    # Onay gereken malzemeler
    review_needed = scorer.get_materials_requiring_review(scored)
    print(f"\n{len(review_needed)} malzeme kullanıcı onayı bekliyor:")
    for m in review_needed:
        print(f"  - {m['name']} (Skor: {m['confidence']['score']:.1f})")
