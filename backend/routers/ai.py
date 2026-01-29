from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.ai_service import AIAnalysisService
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional
from database import DatabaseManager
from pathlib import Path
import json

router = APIRouter(prefix="/ai", tags=["AI"])

# Database for feedback
db = DatabaseManager(str(Path(__file__).parent.parent.parent / "data.db"))


class AnalysisRequest(BaseModel):
    description: str
    unit: str
    context_data: str = ""


# ============================================
# POZ DATA ERİŞİM FONKSİYONLARI
# ============================================

def get_poz_data() -> Dict[str, Any]:
    """main.py'den POZ_DATA'ya erişim - sys.modules üzerinden güncel referans"""
    import sys
    try:
        # Önce app.state'e erişmeyi dene (en güncel)
        if 'backend.main' in sys.modules:
            main_module = sys.modules['backend.main']
            if hasattr(main_module, 'app'):
                app_state = getattr(main_module.app, 'state', None)
                if app_state and hasattr(app_state, 'poz_data'):
                    return app_state.poz_data

        # Sys.modules üzerinden güncel modüle eriş (fallback)
        if 'main' in sys.modules:
            return sys.modules['main'].__dict__.get('POZ_DATA', {})
        elif 'backend.main' in sys.modules:
            return sys.modules['backend.main'].__dict__.get('POZ_DATA', {})
        else:
            # Modül henüz yüklenmemiş, import et ve eriş
            import backend.main as main_module
            return main_module.__dict__.get('POZ_DATA', {})
    except Exception as e:
        print(f"POZ_DATA erişim hatası: {e}")
        return {}


def parse_price(price_str: str) -> float:
    """Türkçe formatlı fiyatı float'a çevir (1.234,56 -> 1234.56)"""
    if not price_str:
        return 0.0
    try:
        cleaned = str(price_str).replace('.', '').replace(',', '.')
        return float(cleaned)
    except:
        return 0.0


# ============================================
# CONTEXT OLUŞTURMA (AI'ya gönderilecek veri)
# ============================================

def calculate_similarity(text1: str, text2: str) -> float:
    """İki metin arasındaki benzerlik oranını hesapla (0-1)"""
    if not text1 or not text2:
        return 0.0
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()
    return SequenceMatcher(None, text1, text2).ratio()


def extract_keywords(description: str) -> List[str]:
    """Açıklamadan anahtar kelimeleri çıkar"""
    # Türkçe stop words
    stop_words = {'ve', 'ile', 'için', 'bir', 'bu', 'de', 'da', 'den', 'dan', 'nin', 'nın', 'ın', 'in'}

    words = description.lower().replace('/', ' ').replace('-', ' ').split()
    keywords = [w for w in words if len(w) > 2 and w not in stop_words]
    return keywords


def build_context_from_poz_data(description: str, unit: str, max_results: int = 15) -> str:
    """
    Poz tanımına göre POZ_DATA'dan benzer pozları bul ve AI için context oluştur.
    Bu context AI'ya gönderilecek ve daha gerçekçi fiyatlar üretmesini sağlayacak.
    """
    poz_data = get_poz_data()
    if not poz_data:
        return ""

    keywords = extract_keywords(description)
    matches = []

    for poz_no, poz_info in poz_data.items():
        poz_desc = poz_info.get('description', '')
        poz_unit = poz_info.get('unit', '')

        # Benzerlik puanı hesapla
        score = 0

        # 1. Açıklama benzerliği (en önemli)
        desc_similarity = calculate_similarity(description, poz_desc)
        score += desc_similarity * 50

        # 2. Anahtar kelime eşleşmesi
        poz_desc_lower = poz_desc.lower()
        keyword_matches = sum(1 for kw in keywords if kw in poz_desc_lower)
        score += keyword_matches * 10

        # 3. Birim eşleşmesi
        if unit.lower() == poz_unit.lower():
            score += 15

        # 4. Poz tipi eşleşmesi (malzeme, işçilik vb.)
        if any(kw in poz_desc_lower for kw in ['malzeme', 'çimento', 'demir', 'beton', 'kum', 'taş']):
            if any(kw in description.lower() for kw in ['malzeme', 'çimento', 'demir', 'beton', 'kum', 'taş']):
                score += 10

        if score > 5:  # Minimum eşik
            matches.append({
                'poz_no': poz_no,
                'description': poz_desc,
                'unit': poz_unit,
                'unit_price': poz_info.get('unit_price', '0'),
                'score': score
            })

    # En yüksek puanlıları al
    matches.sort(key=lambda x: x['score'], reverse=True)
    top_matches = matches[:max_results]

    if not top_matches:
        return ""

    # Context string oluştur
    context_lines = ["MEVCUT VERİTABANINDAN BULUNAN BENZER POZLAR:"]
    context_lines.append("=" * 60)

    # Kategorilere ayır
    materials = []
    labor = []
    transport = []
    other = []

    for m in top_matches:
        poz_no = m['poz_no']
        if poz_no.startswith('10.') or poz_no.startswith('15.') or poz_no.startswith('04.'):
            materials.append(m)
        elif poz_no.startswith('01.') or poz_no.startswith('02.'):
            labor.append(m)
        elif poz_no.startswith('07.'):
            transport.append(m)
        else:
            other.append(m)

    if materials:
        context_lines.append("\n📦 MALZEMELER:")
        for m in materials[:5]:
            price = parse_price(m['unit_price'])
            context_lines.append(f"  • {m['poz_no']}: {m['description'][:50]} = {price:,.2f} TL/{m['unit']}")

    if labor:
        context_lines.append("\n👷 İŞÇİLİKLER:")
        for m in labor[:4]:
            price = parse_price(m['unit_price'])
            context_lines.append(f"  • {m['poz_no']}: {m['description'][:50]} = {price:,.2f} TL/{m['unit']}")

    if transport:
        context_lines.append("\n🚚 NAKLİYE:")
        for m in transport[:3]:
            price = parse_price(m['unit_price'])
            context_lines.append(f"  • {m['poz_no']}: {m['description'][:50]} = {price:,.2f} TL/{m['unit']}")

    if other:
        context_lines.append("\n📋 DİĞER İLGİLİ POZLAR:")
        for m in other[:3]:
            price = parse_price(m['unit_price'])
            context_lines.append(f"  • {m['poz_no']}: {m['description'][:50]} = {price:,.2f} TL/{m['unit']}")

    context_lines.append("\n" + "=" * 60)
    context_lines.append("NOT: Yukarıdaki fiyatlar 2025 yılı Çevre ve Şehircilik Bakanlığı rayiçleridir.")
    context_lines.append("Analiz oluştururken bu fiyatları referans alın.")

    return "\n".join(context_lines)


# ============================================
# FEEDBACK CONTEXT (Kullanıcı Düzeltmelerinden Öğrenme)
# ============================================

def build_feedback_context(description: str, unit: str) -> str:
    """
    Benzer sorgular için geçmiş kullanıcı düzeltmelerini context olarak hazırla.
    Bu sayede AI, daha önce yapılan hatalardan öğrenir.
    """
    feedback_list = db.get_relevant_feedback(description, unit, limit=3)

    if not feedback_list:
        return ""

    context_lines = [
        "\n" + "=" * 60,
        "⚠️ ÖNCEKİ KULLANICI DÜZELTMELERİ (ÖNEMLİ!):",
        "=" * 60,
        "Aşağıdaki düzeltmeler benzer sorgular için yapılmıştır.",
        "Bu bilgileri DİKKATE AL ve aynı hataları TEKRARLAMA!\n"
    ]

    for i, fb in enumerate(feedback_list, 1):
        try:
            components = fb.get('correct_components', [])
            if isinstance(components, str):
                components = json.loads(components)
        except:
            components = []

        context_lines.append(f"📝 Düzeltme #{i}:")
        context_lines.append(f"   Orijinal sorgu: \"{fb.get('original_prompt', '')}\"")
        context_lines.append(f"   Sorun: {fb.get('correction_description', '')}")

        if components:
            context_lines.append(f"   Doğru bileşenler:")
            for comp in components[:5]:  # Max 5 bileşen göster
                context_lines.append(
                    f"     • {comp.get('type', '')}: {comp.get('name', '')} "
                    f"({comp.get('quantity', 0)} {comp.get('unit', '')}) = {comp.get('unit_price', 0)} TL"
                )

        context_lines.append("")

        # Kullanım sayısını artır
        if fb.get('id'):
            try:
                db.increment_feedback_use_count(fb['id'])
            except:
                pass

    context_lines.append("=" * 60)
    context_lines.append("YUKARIDAKİ DÜZELTMELERİ DİKKATE AL!")
    context_lines.append("=" * 60)

    return "\n".join(context_lines)


# ============================================
# FİYAT EŞLEŞTİRME FONKSİYONLARI
# ============================================

def find_price_by_code(code: str, poz_data: Dict) -> Optional[float]:
    """Poz koduna göre doğrudan fiyat bul"""
    if code in poz_data:
        return parse_price(poz_data[code].get('unit_price', '0'))
    return None


def find_price_by_similar_code(code: str, poz_data: Dict) -> Optional[float]:
    """Benzer poz koduna göre fiyat bul (örn: 15.150.1001 için 15.150.* ara)"""
    if not code:
        return None

    parts = code.split('.')
    best_match = None
    best_score = 0

    for poz_no, poz_info in poz_data.items():
        poz_parts = poz_no.split('.')

        score = 0
        for i, part in enumerate(parts):
            if i < len(poz_parts) and poz_parts[i] == part:
                score += 1
            else:
                break

        if score >= 2 and score > best_score:
            best_match = poz_info
            best_score = score

    if best_match:
        return parse_price(best_match.get('unit_price', '0'))
    return None


def find_price_by_description(name: str, unit: str, poz_data: Dict) -> Optional[float]:
    """Açıklama benzerliğine göre fiyat bul"""
    if not name:
        return None

    best_match = None
    best_score = 0.0

    keywords = extract_keywords(name)

    for poz_no, poz_info in poz_data.items():
        poz_desc = poz_info.get('description', '')
        poz_unit = poz_info.get('unit', '')

        # Benzerlik hesapla
        similarity = calculate_similarity(name, poz_desc)

        # Anahtar kelime bonusu
        poz_desc_lower = poz_desc.lower()
        keyword_bonus = sum(0.1 for kw in keywords if kw in poz_desc_lower)

        # Birim bonusu
        unit_bonus = 0.15 if unit.lower() == poz_unit.lower() else 0

        total_score = similarity + keyword_bonus + unit_bonus

        if total_score > best_score and total_score > 0.4:  # Minimum eşik
            best_match = poz_info
            best_score = total_score

    if best_match:
        return parse_price(best_match.get('unit_price', '0'))
    return None


def match_prices_from_poz_data(result: Dict) -> Dict:
    """
    AI analiz sonuçlarındaki bileşenler için POZ_DATA'dan birim fiyatları eşleştir.
    Çoklu strateji kullanır: kod eşleşmesi -> benzer kod -> açıklama benzerliği
    """
    poz_data = get_poz_data()

    if not poz_data or "components" not in result:
        return result

    for comp in result["components"]:
        code = comp.get("code", "")
        name = comp.get("name", "")
        unit = comp.get("unit", "")
        current_price = float(comp.get("unit_price", 0))

        # Eğer AI zaten makul bir fiyat verdiyse ve fiyat > 0 ise, koruyabiliriz
        # Ama PDF'den daha doğru fiyat bulmaya çalışalım

        matched_price = None
        match_method = None

        # Strateji 1: Doğrudan kod eşleşmesi
        matched_price = find_price_by_code(code, poz_data)
        if matched_price and matched_price > 0:
            match_method = "exact_code"

        # Strateji 2: Benzer kod eşleşmesi
        if not matched_price or matched_price == 0:
            matched_price = find_price_by_similar_code(code, poz_data)
            if matched_price and matched_price > 0:
                match_method = "similar_code"

        # Strateji 3: Açıklama benzerliği
        if not matched_price or matched_price == 0:
            matched_price = find_price_by_description(name, unit, poz_data)
            if matched_price and matched_price > 0:
                match_method = "description"

        # Fiyatı güncelle
        if matched_price and matched_price > 0:
            comp["unit_price"] = matched_price
            comp["price_source"] = match_method  # Debug için
        elif current_price > 0:
            comp["price_source"] = "ai_generated"
        else:
            comp["price_source"] = "not_found"

        # Tutarı hesapla
        quantity = float(comp.get("quantity", 0))
        unit_price = float(comp.get("unit_price", 0))
        comp["total_price"] = round(quantity * unit_price, 2)

    return result


# ============================================
# ANA API ENDPOINT
# ============================================


# ============================================
# VALIDATION LOGIC (Beton/Betonarme Kontrolü)
# ============================================

def validate_beton_betonarme(components: List[Dict], description: str) -> List[Dict]:
    """
    Beton ve betonarme ayrımını kontrol et ve gerekirse düzelt
    Desktop uygulamasındaki mantığın aynısı
    """
    if not components:
        return components

    desc_lower = description.lower()

    # Beton mu betonarme mi tespit et
    is_betonarme = any(keyword in desc_lower for keyword in [
        'betonarme', 'betonarm', 'donatı', 'donatılı', 'hasır', 'armatüre',
        'armature', 'reinforced', 'demir', 'nervürlü'
    ])

    is_beton = any(keyword in desc_lower for keyword in [
        'beton', 'concrete'
    ])

    # BETON (donatısız) ise
    if is_beton and not is_betonarme:
        # Demir varsa KALDIR
        original_count = len(components)
        components = [
            comp for comp in components
            if not any(kw in comp.get('name', '').lower() for kw in [
                'demir', 'donatı', 'nervürlü', 'hasır', 'çelik', 'armatür'
            ])
        ]

        if len(components) < original_count:
            print(f"[VALIDATION] {original_count - len(components)} demir kalemi kaldırıldı (beton donatısız)")

        # Kalıp var mı kontrol et
        has_kalip = any('kalıp' in comp.get('name', '').lower() for comp in components)
        has_beton = any('beton' in comp.get('name', '').lower() for comp in components if comp.get('type', '').lower() == 'malzeme')

        if has_beton and not has_kalip:
            # Kalıp ekle
            components.append({
                'type': 'Malzeme',
                'code': '04.001.1001',
                'name': 'Ahşap Kalıp',
                'unit': 'm²',
                'quantity': 0.0,
                'unit_price': 50.0,
                'total_price': 0.0,
                'price_source': 'validation_rule',
                'notes': '[OTOMATIK EKLENDI] Beton için kalıp zorunludur'
            })

    # BETONARME ise
    elif is_betonarme:
        # Zorunlu malzemeler kontrolü
        has_beton = any('beton' in comp.get('name', '').lower() for comp in components if comp.get('type', '').lower() == 'malzeme')
        has_demir = any(kw in comp.get('name', '').lower() for kw in ['demir', 'donatı', 'nervürlü', 'hasır', 'çelik'] for comp in components if comp.get('type', '').lower() == 'malzeme')
        has_kalip = any('kalıp' in comp.get('name', '').lower() for comp in components)

        # Eksik malzemeleri ekle
        if has_beton and not has_demir:
            components.append({
                'type': 'Malzeme',
                'code': '10.140.1001',
                'name': 'Nervürlü Betonarme Çeliği S420',
                'unit': 'ton',
                'quantity': 0.0,
                'unit_price': 25000.0,
                'total_price': 0.0,
                'price_source': 'validation_rule',
                'notes': '[OTOMATIK EKLENDI] Betonarme için demir zorunludur'
            })

        if has_beton and not has_kalip:
            components.append({
                'type': 'Malzeme',
                'code': '04.001.1001',
                'name': 'Ahşap Kalıp',
                'unit': 'm²',
                'quantity': 0.0,
                'unit_price': 50.0,
                'total_price': 0.0,
                'price_source': 'validation_rule',
                'notes': '[OTOMATIK EKLENDI] Betonarme için kalıp zorunludur'
            })

    return components

@router.post("/analyze")
async def analyze_poz(request: AnalysisRequest):
    """
    AI analizi yap ve birim fiyatları PDF verilerinden eşleştir.

    İyileştirmeler:
    1. POZ_DATA'dan benzer pozları bulup AI'ya context olarak gönderir
    2. Geçmiş kullanıcı düzeltmelerini context'e ekler (feedback learning)
    3. AI yanıtındaki fiyatları PDF verileriyle eşleştirir (kod + açıklama benzerliği)
    4. Daha detaylı ve Türkiye'ye özel prompt kullanır
    """
    service = AIAnalysisService()

    try:
        # 1. Context oluştur (POZ_DATA'dan benzer pozları bul)
        poz_context = build_context_from_poz_data(request.description, request.unit)

        # 2. Feedback context oluştur (geçmiş düzeltmelerden öğren)
        feedback_context = build_feedback_context(request.description, request.unit)

        # 3. Tüm context'leri birleştir
        full_context = poz_context
        if feedback_context:
            full_context += "\n" + feedback_context
        if request.context_data:
            full_context += "\n\nKULLANICI EK BİLGİLERİ:\n" + request.context_data

        # 4. AI analizini al (zenginleştirilmiş context ile)
        result = service.generate_analysis(
            description=request.description,
            unit=request.unit,
            context_data=full_context
        )

        # 5. POZ_DATA (Validasyon Sonrası)
        if "components" in result:
             result["components"] = validate_beton_betonarme(result["components"], request.description)

        # 6. PDF verilerinden birim fiyatları eşleştir
        result = match_prices_from_poz_data(result)

        # 6. Özet bilgi ekle
        result["metadata"] = {
            "poz_data_count": len(get_poz_data()),
            "context_provided": bool(full_context),
            "feedback_used": bool(feedback_context),
            "price_sources": summarize_price_sources(result)
        }

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def summarize_price_sources(result: Dict) -> Dict[str, int]:
    """Fiyat kaynaklarının özetini çıkar"""
    sources = {"exact_code": 0, "similar_code": 0, "description": 0, "ai_generated": 0, "not_found": 0}

    for comp in result.get("components", []):
        source = comp.get("price_source", "not_found")
        if source in sources:
            sources[source] += 1

    return sources
