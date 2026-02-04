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
from typing import List, Dict
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
        from config import get_validation_config
        _cfg = get_validation_config()

        self.typical_ratios = {
            'rebar_per_concrete': _cfg.REBAR_PER_CONCRETE,
            'formwork_per_concrete': _cfg.FORMWORK_PER_CONCRETE,
            'mortar_per_wall_m2': _cfg.MORTAR_PER_WALL_M2,
        }

        self.typical_prices_per_m2 = _cfg.PRICE_RANGES_PER_M2
        
        from services.rule_service import RuleService
        self.rule_service = RuleService()

        # AI Service (Lazy load to avoid circular imports if any)
        from services.ai_service import AIAnalysisService
        self.ai_service = AIAnalysisService()
    
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
        
        # 5. Genel eksik ve mantık kontrolleri
        all_issues.extend(self.check_missing_labor(components))
        all_issues.extend(self.check_plain_concrete_no_rebar(components, description))
        all_issues.extend(self.check_ready_mix_consistency(components, description))

        # 6. Imalat-spesifik eksiklik kontrolleri
        all_issues.extend(self.check_paint_primer(components, description))
        all_issues.extend(self.check_betonarme_paspayi(components, description))
        all_issues.extend(self.check_pipe_bedding(components, description))

        # 7. Kullanıcı Tanımlı Kurallar (Öğrenen AI)
        all_issues.extend(self.check_user_rules(components, description))

        # 7. LLM Tabanlı Semantik Kontrol (YENİ - Gerçek Agent)
        # Sadece kritik hata yoksa veya kullanıcı özellikle istediyse çalıştırılabilir
        # Şimdilik her zaman çalıştırıyoruz (User Request)
        try:
            from services.ai_service import logger
            logger.info("LLM Critic başlatılıyor...")
            
            llm_result = self.ai_service.review_analysis(analysis_result, description)
            
            if llm_result.get("status") != "error": # LLM çalıştıysa
                llm_issues = llm_result.get("issues", [])
                # Existing messages joined → dedupe check against rule-based issues
                existing_msgs = " ".join(i.message.lower() for i in all_issues)
                # Trigger words: if both existing and new issue mention same material → duplicate
                dedup_keywords = ['demir', 'kalıp', 'harç', 'iskele', 'nakliye',
                                  'çimento', 'çakıl', 'kum', 'beton', 'tuğla', 'astar']

                for issue in llm_issues:
                    msg_lower = issue.get("message", "").lower()
                    # Mevcut issues ile örtüşen material keyword varsa atla
                    shared = [kw for kw in dedup_keywords if kw in msg_lower and kw in existing_msgs]
                    if shared:
                        continue  # Rule-based check daha spesifik → LLM duplicate atılır

                    all_issues.append(Issue(
                        severity=issue.get("severity", "warning"),
                        category=f"AI: {issue.get('category', 'Genel')}",
                        message=issue.get("message", ""),
                        suggestion=issue.get("suggestion", "")
                    ))
        except Exception as e:
            print(f"LLM Critic Integration Error: {e}")
        
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
        # Demir/çelik aramak için daha geniş keyword listesi
        rebar_keywords = ['demir', 'çelik', 'donatı', 's420', 's500', 'nervürlü', 'hasır']
        has_rebar = any(any(kw in c.get('name', '').lower() for kw in rebar_keywords) for c in components)
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
            rebar_qty = rebar.get('quantity', 0)
            # Unit normalization: kg → ton
            rebar_unit = rebar.get('unit', 'ton').lower()
            rebar_ton = rebar_qty / 1000 if rebar_unit == 'kg' else rebar_qty

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
    
    def check_plain_concrete_no_rebar(self, components: List[Dict], description: str) -> List[Issue]:
        """Yalın betonda demir olmamalı"""
        issues = []
        desc_lower = description.lower()
        
        # Yalın beton tespiti
        # "beton" var, "betonarme" yok, "döşeme" veya "temel" olabilir ama "betonarme" denmemiş
        is_plain_concrete = (
            'beton' in desc_lower and
            'betonarme' not in desc_lower and
            'donatı' not in desc_lower and
            'hasır' not in desc_lower and
            'demir' not in desc_lower
        )
        
        if not is_plain_concrete:
            return issues
        
        # Demir var mı kontrol et
        has_steel = any(
            any(kw in c.get('name', '').lower() for kw in ['demir', 'çelik', 'donatı', 's420', 's500'])
            for c in components
        )
        
        if has_steel:
            issues.append(Issue(
                severity="critical",
                category="Mantık Hatası",
                message="YALIN BETON imalatında demir/donatı bulunmamalıdır.",
                suggestion="Yalın beton sadece beton ve kalıptan oluşur (bazen kalıp da olmaz). Demir kalemini çıkarın."
            ))
        
        return issues
        
    def check_ready_mix_consistency(self, components: List[Dict], description: str) -> List[Issue]:
        """Hazır betonda çimento/kum/çakıl ayrı olmamalı"""
        issues = []
        desc_lower = description.lower()
        
        # Hazır beton/santral tespiti
        is_ready_mix = any(kw in desc_lower for kw in ['santral', 'hazır beton', 'pompa ile', 'transmikser'])
        
        has_ready_mix_comp = any(
            'hazır beton' in c.get('name', '').lower() or 
            str(c.get('code', '')).startswith('15.150') 
            for c in components
        )
        
        if not is_ready_mix and not has_ready_mix_comp:
            return issues
        
        # Çimento/kum/çakıl var mı?
        aggregates = ['çimento', 'kum', 'çakıl', 'agrega']
        has_aggregate = any(
            any(agg in c.get('name', '').lower() for agg in aggregates)
            for c in components if c.get('type') == 'Malzeme'
        )
        
        if has_aggregate:
            issues.append(Issue(
                severity="critical",
                category="Mükerrer Malzeme",
                message="HAZIR BETON imalatında çimento/kum/çakıl ayrıca YAZILMAZ.",
                suggestion="Hazır beton zaten bu bileşenleri içerir. Agrega ve çimento kalemlerini silin."
            ))

        # Hazır beton nakliyesi kontrolü: transmikser ile gelir → ayrı nakliye satırı olmamalı
        has_beton_nakliye = any(
            any(kw in c.get('name', '').lower() for kw in ['beton nakliye', 'hazır beton nakliye'])
            for c in components if c.get('type', '') == 'Nakliye'
        )
        if has_beton_nakliye:
            issues.append(Issue(
                severity="critical",
                category="Mükerrer Nakliye",
                message="HAZIR BETON nakliyesi birim fiyata dahildir — ayrı satır olarak yazılmamalı.",
                suggestion="Hazır beton transmikser ile doğrudan sahasına gelir. 'Beton nakliyesi' kalemini silin."
            ))

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

    def check_paint_primer(self, components: List[Dict], description: str) -> List[Issue]:
        """Boya imalatında astar zorunlu"""
        issues = []
        desc_lower = description.lower()

        has_paint_keyword = any(kw in desc_lower for kw in ['boya', 'boyama', 'badana'])
        has_paint_comp = any('boya' in c.get('name', '').lower() or 'badana' in c.get('name', '').lower()
                            for c in components)

        if not (has_paint_keyword or has_paint_comp):
            return issues

        has_primer = any('astar' in c.get('name', '').lower() for c in components)
        if not has_primer and 'astar hariç' not in desc_lower:
            issues.append(Issue(
                severity="critical",
                category="Eksik Malzeme",
                message="Boya imalatında astar bulunamadı",
                suggestion="Astar olmadan boya yapılmaz. Astar malzeme kalemini ekleyin."
            ))

        return issues

    def check_betonarme_paspayi(self, components: List[Dict], description: str) -> List[Issue]:
        """Betonarme imalatında paspayı kontrolü"""
        issues = []
        desc_lower = description.lower()

        is_betonarme = 'betonarme' in desc_lower
        has_rebar = any(any(kw in c.get('name', '').lower() for kw in ['demir', 'donatı', 'nervürlü'])
                       for c in components)

        if not (is_betonarme and has_rebar):
            return issues

        has_paspayi = any('paspayı' in c.get('name', '').lower() or 'paspa' in c.get('name', '').lower()
                         for c in components)
        if not has_paspayi and 'paspayı hariç' not in desc_lower:
            issues.append(Issue(
                severity="warning",
                category="Eksik Malzeme",
                message="Betonarme imalatında paspayı bulunamadı",
                suggestion="Demir altı paspayı (tipik 2-3 cm) teknik bir zorunluluktur. Ekleyin."
            ))

        return issues

    def check_pipe_bedding(self, components: List[Dict], description: str) -> List[Issue]:
        """Boru döşemede yatek malzeme kontrolü"""
        issues = []
        desc_lower = description.lower()

        has_pipe = any(kw in desc_lower for kw in ['boru döşeme', 'boru hatı', 'boru imalat'])
        has_pipe_comp = any('boru' in c.get('name', '').lower() for c in components)

        if not (has_pipe or has_pipe_comp):
            return issues

        has_bedding = any(any(kw in c.get('name', '').lower() for kw in ['yatek', 'kum', 'dolgu'])
                         for c in components)
        if not has_bedding and 'yatek hariç' not in desc_lower:
            issues.append(Issue(
                severity="warning",
                category="Eksik Malzeme",
                message="Boru döşemede yatek malzeme (kum/dolgu) bulunamadı",
                suggestion="Boru altı yatek tabakası (tipik kum veya dolgu) döşemede zorunludur."
            ))

        return issues

    def check_user_rules(self, components: List[Dict], description: str) -> List[Issue]:
        """Kullanıcı tarafından öğretilen kuralları kontrol et"""
        issues = []
        matching_rules = self.rule_service.find_matching_rules(description)
        
        for rule in matching_rules:
            missing_items = []
            for required_item in rule['required_items']:
                # Göz gevşek kontrol: isim içinde geçiyor mu?
                # Örn: required="Harç" -> components içerisinde "harç" veya "çimento" var mı?
                req_name_lower = required_item['name'].lower()
                
                is_present = any(req_name_lower in c.get('name', '').lower() for c in components)
                
                if not is_present:
                    missing_items.append(required_item['name'])
            
            if missing_items:
                # Kural ihlali
                issues.append(Issue(
                    severity="warning",
                    category="Öğrenilmiş Kural",
                    message=f"Eksik kalemler tespit edildi: {', '.join(missing_items)}",
                    suggestion=f"Daha önce bu iş için şu kuralı kaydettiniz: {rule['condition_text']}. {', '.join(missing_items)} eklemeniz önerilir."
                ))
                # Kural işe yaradı, sayacı artır
                try:
                    self.rule_service.increment_usage(rule['id'])
                except:
                    pass

        return issues

# Singleton instance
_critic_service = None

def get_critic_service() -> CriticService:
    """Critic service singleton'ını döndür"""
    global _critic_service
    if _critic_service is None:
        _critic_service = CriticService()
    return _critic_service
