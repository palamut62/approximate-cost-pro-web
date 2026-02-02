"""
Critic Service - AI Analiz Sonuçlarını Kontrol Eden Eleştirmen Sistemi

Bu servis, Analist AI'nın ürettiği sonuçları kritik hatalar için kontrol eder.
Kural tabanlı yaklaşım kullanır (hızlı ve ücretsiz).

Kontrol Edilen Kurallar:
1. Fiziksel Mantık (betonarme-demir, duvar-harç)
2. Miktar Oranları (beton/demir oranı vb.)
3. Fiyat Anomalileri (sektör ortalamalarıyla karşılaştırma)
4. Eksik Bileşenler
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class Issue:
    """Tespit edilen sorun"""
    severity: str  # "critical", "warning", "info"
    category: str  # "Eksik Malzeme", "Mantık Hatası", "Fiyat Anomali"
    message: str
    suggestion: str

@dataclass
class CriticReview:
    """Eleştirmen inceleme sonucu"""
    status: str  # "ok", "warning", "error"
    issues: List[Issue]
    suggestions: List[str]
    auto_fix_available: bool = False

class CriticService:
    """Analiz sonuçlarını kritik hatalar için kontrol eder"""
    
    def __init__(self):
        # Tipik sektör oranları (referans değerler)
        self.typical_ratios = {
            'rebar_per_concrete': (0.08, 0.15),  # ton/m³ (80-150 kg/m³)
            'formwork_per_concrete': (5, 8),     # m²/m³
            'mortar_per_wall_m2': (0.02, 0.05),  # m³/m²
        }
        
        # Tipik fiyat aralıkları (m² başına, TL)
        self.typical_prices_per_m2 = {
            'duvar': (500, 2500),
            'döşeme': (1000, 3500),
            'betonarme': (1500, 4000),
            'seramik': (300, 1500),
            'boya': (50, 150),
        }
    
    def review_analysis(self, 
                       analysis_result: Dict,
                       description: str) -> CriticReview:
        """
        Analist AI sonucunu inceler ve sorunları tespit eder
        
        Args:
            analysis_result: AI analiz sonucu
            description: Kullanıcının girdiği tanım
            
        Returns:
            CriticReview: Tespit edilen sorunlar ve öneriler
        """
        components = analysis_result.get('components', [])
        all_issues = []
        
        # 1. Betonarme kontrolleri
        all_issues.extend(self.check_reinforced_concrete(components, description))
        
        # 2. Duvar kontrolleri
        all_issues.extend(self.check_wall_components(components, description))
        
        # 3. Miktar oranları
        all_issues.extend(self.check_quantity_ratios(components))
        
        # 4. Fiyat anomalileri
        all_issues.extend(self.check_price_deviation(analysis_result, description))
        
        # 5. Genel eksik kontroller
        all_issues.extend(self.check_missing_labor(components))
        
        # Durum belirle
        has_critical = any(i.severity == "critical" for i in all_issues)
        has_warning = any(i.severity == "warning" for i in all_issues)
        
        if has_critical:
            status = "error"
        elif has_warning:
            status = "warning"
        else:
            status = "ok"
        
        # Önerileri topla
        suggestions = [issue.suggestion for issue in all_issues if issue.suggestion]
        
        return CriticReview(
            status=status,
            issues=all_issues,
            suggestions=suggestions,
            auto_fix_available=False
        )
    
    def check_reinforced_concrete(self, components: List[Dict], description: str) -> List[Issue]:
        """Betonarme yapılar için kontrol"""
        issues = []
        
        desc_lower = description.lower()
        
        # "betonarme" kelimesi var mı?
        has_betonarme_keyword = 'betonarme' in desc_lower
        
        # Bileşenleri kontrol et
        has_concrete = any('beton' in c.get('name', '').lower() for c in components)
        has_rebar = any('demir' in c.get('name', '').lower() for c in components)
        has_formwork = any('kalıp' in c.get('name', '').lower() for c in components)
        
        if has_betonarme_keyword or (has_concrete and 'döşeme' in desc_lower):
            # Betonarme tespit edildi
            if not has_rebar:
                issues.append(Issue(
                    severity="critical",
                    category="Eksik Malzeme",
                    message="Betonarme yapı için demir bulunamadı",
                    suggestion="Ø12-Ø16 arası nervürlü inşaat demiri ekleyin (tipik: 100-120 kg/m³)"
                ))
            
            if not has_formwork:
                issues.append(Issue(
                    severity="critical",
                    category="Eksik Malzeme",
                    message="Betonarme yapı için kalıp bulunamadı",
                    suggestion="Ahşap veya metal kalıp sistemi ekleyin (tipik: 6-7 m²/m³ beton)"
                ))
        
        return issues
    
    def check_wall_components(self, components: List[Dict], description: str) -> List[Issue]:
        """Duvar yapıları için kontrol"""
        issues = []
        
        desc_lower = description.lower()
        
        # Duvar var mı?
        has_wall_keyword = any(kw in desc_lower for kw in ['duvar', 'tuğla', 'briket', 'blok'])
        has_brick = any('tuğla' in c.get('name', '').lower() or 'briket' in c.get('name', '').lower() 
                       for c in components)
        has_mortar = any('harç' in c.get('name', '').lower() or 'çimento' in c.get('name', '').lower() 
                        for c in components)
        
        if has_wall_keyword or has_brick:
            if not has_mortar and 'harç hariç' not in desc_lower:
                issues.append(Issue(
                    severity="warning",
                    category="Eksik Malzeme",
                    message="Duvar örülmesi için harç bulunamadı",
                    suggestion="Hazır kireç harcı veya çimento harcı ekleyin (tipik: 0.03 m³/m² duvar)"
                ))
        
        return issues
    
    def check_quantity_ratios(self, components: List[Dict]) -> List[Issue]:
        """Miktar oranlarını kontrol et"""
        issues = []
        
        # Beton ve demir oranı
        concrete = next((c for c in components if 'beton' in c.get('name', '').lower() 
                        and c.get('type') == 'Malzeme'), None)
        rebar = next((c for c in components if 'demir' in c.get('name', '').lower()), None)
        
        if concrete and rebar:
            concrete_m3 = concrete.get('quantity', 0)
            rebar_ton = rebar.get('quantity', 0)
            
            if concrete_m3 > 0:
                ratio = rebar_ton / concrete_m3
                min_ratio, max_ratio = self.typical_ratios['rebar_per_concrete']
                
                if ratio > max_ratio * 2:  # 2x fazla
                    issues.append(Issue(
                        severity="warning",
                        category="Mantık Hatası",
                        message=f"Beton-demir oranı normalin çok üzerinde ({ratio:.3f} ton/m³ = {ratio*1000:.0f} kg/m³)",
                        suggestion=f"Tipik betonarme oran 80-150 kg/m³ arasındadır. Miktarı kontrol edin."
                    ))
                elif ratio < min_ratio / 2:  # Yarısı kadar az
                    issues.append(Issue(
                        severity="warning",
                        category="Mantık Hatası",
                        message=f"Beton-demir oranı normalin altında ({ratio:.3f} ton/m³ = {ratio*1000:.0f} kg/m³)",
                        suggestion=f"Betonarme için en az 80 kg/m³ demir gerekir. Eksik olabilir."
                    ))
        
        # Kalıp-beton oranı
        formwork = next((c for c in components if 'kalıp' in c.get('name', '').lower()), None)
        
        if concrete and formwork:
            concrete_m3 = concrete.get('quantity', 0)
            formwork_m2 = formwork.get('quantity', 0)
            
            if concrete_m3 > 0:
                ratio = formwork_m2 / concrete_m3
                min_ratio, max_ratio = self.typical_ratios['formwork_per_concrete']
                
                if ratio > max_ratio * 2:
                    issues.append(Issue(
                        severity="info",
                        category="Miktar Kontrol",
                        message=f"Kalıp-beton oranı yüksek ({ratio:.1f} m²/m³)",
                        suggestion="İnce elemanlarda (kolon, kiriş) bu normal olabilir."
                    ))
        
        return issues
    
    def check_price_deviation(self, result: Dict, description: str) -> List[Issue]:
        """Fiyat sapmalarını kontrol et"""
        issues = []
        
        components = result.get('components', [])
        total_price = sum(c.get('total_price', 0) for c in components)
        
        if total_price == 0:
            return issues
        
        # Alan bilgisi varsa m² başına fiyat hesapla
        area_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', description)
        if area_match:
            area = float(area_match.group(1).replace(',', '.'))
            if area > 0:
                price_per_m2 = total_price / area
                
                # Tanıma göre tipik fiyat aralığı bul
                desc_lower = description.lower()
                for keyword, (min_price, max_price) in self.typical_prices_per_m2.items():
                    if keyword in desc_lower:
                        if price_per_m2 > max_price * 1.5:
                            issues.append(Issue(
                                severity="warning",
                                category="Fiyat Anomali",
                                message=f"{keyword.capitalize()} m² fiyatı sektör ortalamasının üzerinde ({price_per_m2:.0f} TL/m²)",
                                suggestion=f"Normal aralık {min_price}-{max_price} TL/m². Kontrol edin."
                            ))
                        elif price_per_m2 < min_price * 0.5:
                            issues.append(Issue(
                                severity="warning",
                                category="Fiyat Anomali",
                                message=f"{keyword.capitalize()} m² fiyatı sektör ortalamasının altında ({price_per_m2:.0f} TL/m²)",
                                suggestion=f"Normal aralık {min_price}-{max_price} TL/m². Eksik kalem olabilir."
                            ))
                        break
        
        return issues
    
    def check_missing_labor(self, components: List[Dict]) -> List[Issue]:
        """İşçilik eksikliği kontrol et"""
        issues = []
        
        has_material = any(c.get('type') == 'Malzeme' for c in components)
        has_labor = any(c.get('type') == 'İşçilik' for c in components)
        
        if has_material and not has_labor:
            issues.append(Issue(
                severity="warning",
                category="Eksik Kalem",
                message="Malzeme var ama işçilik bulunamadı",
                suggestion="İnşaat işlerinde genellikle işçilik gerekir. Kontrol edin."
            ))
        
        return issues

# Singleton instance
_critic_service = None

def get_critic_service() -> CriticService:
    """Critic service singleton'ını döndür"""
    global _critic_service
    if _critic_service is None:
        _critic_service = CriticService()
    return _critic_service
