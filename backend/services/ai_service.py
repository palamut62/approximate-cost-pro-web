import json
import requests
import re
import os
from typing import Dict, Any, Optional


class AIAnalysisService:
    def __init__(self,
                 openrouter_key: Optional[str] = None,
                 gemini_key: Optional[str] = None,
                 model: str = "google/gemini-2.0-flash-001",
                 base_url: str = "https://openrouter.ai/api/v1"):
        self.openrouter_key = openrouter_key or os.getenv("OPENROUTER_API_KEY")
        self.gemini_key = gemini_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.base_url = base_url

    def refine_feedback_description(self, text: str) -> str:
        """Kullanıcının girdiği düzeltme metnini profesyonel bir dile çevirir."""
        prompt = f"""Bir inşaat mühendisi gibi davran. Aşağıdaki gayri resmi düzeltme açıklamasını, 
gelecekteki analizlerde referans alınabilecek profesyonel, teknik ve net bir inşaat mühendisi 
talimatına (düzeltme notuna) dönüştür.

GİRİŞ: "{text}"

TALİMAT:
- Teknik terimler kullan (örn: imalat, metraj, rayiç, keşif).
- Net ve emir kipi/bilgi verici tonda ol.
- Sadece düzeltilmiş metni yaz, başka hiçbir şey ekleme.
"""
        
        # OpenRouter or Gemini
        messages = [
            {"role": "system", "content": "Sen uzman bir inşaat mühendisisin."},
            {"role": "user", "content": prompt}
        ]

        if self.openrouter_key:
            try:
                headers = {
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.3
                }
                response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=30)
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content'].strip()
            except Exception as e:
                print(f"Refine Error (OpenRouter): {e}")

        if self.gemini_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_key}"
                data = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.3}
                }
                response = requests.post(url, json=data, timeout=30)
                response.raise_for_status()
                return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            except Exception as e:
                print(f"Refine Error (Gemini): {e}")

        return text # Hata durumunda orijinali döndür

    def generate_analysis(self, description: str, unit: str, context_data: str = "") -> Dict[str, Any]:
        """Analiz oluşturma ana fonksiyonu"""
        prompt = self._build_professional_prompt(description, unit, context_data)

        # Try OpenRouter first if key exists
        if self.openrouter_key:
            try:
                return self._call_openrouter(prompt)
            except Exception as e:
                print(f"OpenRouter Error: {e}")

        # Fallback to Gemini if key exists
        if self.gemini_key:
            try:
                return self._call_gemini(prompt)
            except Exception as e:
                print(f"Gemini Error: {e}")

        raise Exception("AI API anahtarı bulunamadı veya tüm servisler başarısız oldu.")

    def _build_professional_prompt(self, description: str, unit: str, context_data: str) -> str:
        """
        Türkiye inşaat sektörüne özel, profesyonel ve detaylı prompt.
        2025 yılı Çevre ve Şehircilik Bakanlığı normlarına uygun.
        """
        return f"""Sen Türkiye'de 20+ yıl deneyimli bir İnşaat Metraj ve Hakediş Mühendisisin.
Çevre ve Şehircilik Bakanlığı birim fiyat analiz formatlarına hakimsin.

═══════════════════════════════════════════════════════════════
                        GÖREV
═══════════════════════════════════════════════════════════════

Aşağıdaki poz tanımı için detaylı birim fiyat analizi oluştur:

📌 POZ TANIMI: {description}
📌 BİRİM: {unit}

═══════════════════════════════════════════════════════════════
                   MEVCUT VERİTABANI BİLGİLERİ
═══════════════════════════════════════════════════════════════

{context_data if context_data else "Veritabanında benzer poz bulunamadı. Genel bilgilerini kullan."}

═══════════════════════════════════════════════════════════════
                        KURALLAR
═══════════════════════════════════════════════════════════════

⚠️ KRİTİK UYARI - BETON VE BETONARME FARKI:

🔴 EĞER POZ AÇIKLAMASINDA "BETON" YAZIYORSA VE "BETONARME/DONATILI/DEMİR" YAZMIYORSA:
   → Bu DONATISIZ BETON'dur (Yalın beton, düz beton)
   → SADECE: Beton + Kalıp + İşçilik
   → ❌ ASLA DEMİR EKLEME! Donatı yok!

🟢 EĞER POZ AÇIKLAMASINDA "BETONARME/DONATILI/HASIR/ARMATURELİ" YAZIYORSA:
   → Bu BETONARME'dir
   → ZORUNLU: Beton + Demir + Kalıp + İşçilik
   → ✅ Mutlaka demir ekle!

ÖRNEKLER:
✅ "Beton trapez" → BETON + KALIP (demir yok!)
✅ "C20/25 yalın beton" → BETON + KALIP (demir yok!)
✅ "Düz beton döşeme" → BETON + KALIP (demir yok!)
❌ "Betonarme temel" → BETON + DEMİR + KALIP
❌ "Hasır donatılı döşeme" → BETON + DEMİR + KALIP

═══════════════════════════════════════════════════════════════

1. POZ KODLARI (ÇŞB 2025 STANDARDI):
   ⚠️ ÇOK ÖNEMLİ: Aşağıdaki KOD YAPILARINI kesinlikle kullan:

   • MALZEMELER: 10.130.xxxx serisini kullan (örnekler)
     - Çimento: 10.130.1202 (Portland çimentosu, ton)
     - Kum: 10.130.1004 (İnce agrega/kum, m³)
     - Çakıl: 10.130.1001 (İri agrega/çakıl, m³)
     - Tuğla: 10.130.2001 (Yatay delikli tuğla, adet)
     - Su: 10.130.9991 (Su, m³, 38.50 TL)
     - Beton: 10.130.1501-1510 (C serisi beton, m³)
     - Demir: 10.140.xxxx serisi

   • İŞÇİLİKLER: 10.100.xxxx serisini kullan (örnekler)
     - Duvarcı ustası: 10.100.1013 (sa)
     - Duvarcı yardımcısı: 10.100.1045 (sa)
     - Betoncu ustası: 10.100.1015 (sa)
     - Demirci ustası: 10.100.1019 (sa)

   • NAKLİYE: 15.100.xxxx serisini kullan
     - 15.100.1001: 1 ton malzeme nakliyesi
     - 15.100.1002: 1 m³ malzeme nakliyesi

   • MAKİNE: 03.xxx serisi (varsa)

   ⚠️ ASLA 01.xxx, 04.xxx, 07.005 gibi kodları KULLANMA!
   ⚠️ Bu kodlar veritabanında YOK!

2. MİKTAR HESAPLAMA (1 {unit} için):
   • Malzeme fire payı: %3-5 ekle
   • İşçilik verimsizlik payı: %10 ekle
   • Standart işçilik normları kullan:
     - Duvar örme: 0.8-1.2 sa/m²
     - Beton dökme: 1.5-2.0 sa/m³
     - Sıva: 0.6-0.8 sa/m²
     - Demir işçiliği: 8-12 sa/ton

3. NAKLİYE HESABI (varsayılan 20 km):
   • Her malzeme için nakliye kalemi ekle
   • Birim: ton veya m³
   • Yoğunluklar: Beton=2.4 t/m³, Kum=1.6 t/m³, Demir=7.85 t/m³, Taş=2.5 t/m³

4. FİYATLAR:
   • Eğer yukarıda veritabanı fiyatları verilmişse, ONLARI KULLAN
   • Verilmemişse 2025 yılı piyasa rayiçlerini tahmin et
   • Fiyatlar TL cinsinden, virgülsüz yaz (örn: 125.50)

═══════════════════════════════════════════════════════════════
                      ÇIKTI FORMATI
═══════════════════════════════════════════════════════════════

SADECE aşağıdaki JSON formatında yanıt ver, başka hiçbir şey yazma:

{{
  "suggested_unit": "m2/m3/adet/ton/kg - Bu poz için EN UYGUN birim",
  "explanation": "Bu analiz [kısa açıklama]. Malzeme miktarları [norm/kaynak] esas alınarak, işçilik süreleri [norm] baz alınarak hesaplanmıştır. Nakliye 20 km mesafe için eklenmiştir.",
  "components": [
    {{
      "type": "Malzeme",
      "code": "10.130.1202",
      "name": "Malzeme adı (kalite/özellik)",
      "unit": "kg/m³/adet/ton",
      "quantity": 0.0000,
      "unit_price": 0.00
    }},
    {{
      "type": "İşçilik",
      "code": "10.100.1013",
      "name": "İşçilik adı",
      "unit": "sa",
      "quantity": 0.0000,
      "unit_price": 0.00
    }},
    {{
      "type": "Nakliye",
      "code": "15.100.1001",
      "name": "Malzeme nakliyesi (20 km)",
      "unit": "ton",
      "quantity": 0.0000,
      "unit_price": 0.00
    }}
  ]
}}

ÖNEMLİ:
• Her malzeme için ayrı nakliye kalemi ekle
• Miktarları 4 ondalık basamakla yaz
• Fiyatları 2 ondalık basamakla yaz
• JSON dışında hiçbir şey yazma"""

    def _call_openrouter(self, prompt: str) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://approximatecostpro.com",
            "X-Title": "Approximate Cost Pro"
        }
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Sen Türkiye'de çalışan uzman bir inşaat metraj mühendisisin. Sadece JSON formatında yanıt verirsin."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # Daha tutarlı sonuçlar için düşürüldü
            "max_tokens": 4000
        }
        response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=90)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        return self._process_response(content)

    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_key}"
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
                "maxOutputTokens": 4000
            }
        }
        response = requests.post(url, json=data, timeout=90)
        response.raise_for_status()
        content = response.json()['candidates'][0]['content']['parts'][0]['text']
        return self._process_response(content)

    def _process_response(self, content: str) -> Dict[str, Any]:
        """JSON temizleme ve onarma"""
        # Markdown bloklarını temizle
        content = re.sub(r'```json\s*|\s*```', '', content).strip()

        # Önce doğrudan parse etmeyi dene
        try:
            return self._finalize_data(json.loads(content))
        except json.JSONDecodeError:
            pass

        # JSON'ı metin içinden ayıkla (en dıştaki { })
        match = re.search(r'(\{[\s\S]*\})', content)
        if match:
            try:
                return self._finalize_data(json.loads(match.group(1)))
            except json.JSONDecodeError as e:
                # JSON onarma dene
                repaired = self._repair_json(match.group(1))
                try:
                    return self._finalize_data(json.loads(repaired))
                except:
                    raise Exception(f"AI yanıtı geçerli JSON'a dönüştürülemedi: {str(e)}")

        raise Exception(f"AI yanıtında JSON bulunamadı: {content[:200]}...")

    def _repair_json(self, json_str: str) -> str:
        """Bozuk JSON'ı onarmaya çalış"""
        # Trailing comma'ları kaldır
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

        # Eksik tırnakları tamamla
        json_str = re.sub(r':\s*([^"\[\]{},\s][^,}\]]*[^"\[\]{},\s])\s*([,}\]])',
                         r': "\1"\2', json_str)

        return json_str

    def _finalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Veri yapısını doğrula ve hesaplamaları yap"""
        if "components" not in data:
            data["components"] = []

        if "explanation" not in data:
            data["explanation"] = "AI tarafından oluşturulan analiz."

        for comp in data["components"]:
            # Gerekli alanları kontrol et
            comp.setdefault("type", "Diğer")
            comp.setdefault("code", "")
            comp.setdefault("name", "")
            comp.setdefault("unit", "")

            # Sayısal değerleri güvenli hale getir
            try:
                qty = comp.get("quantity", 0)
                if isinstance(qty, str):
                    qty = qty.replace(',', '.')
                comp["quantity"] = round(float(qty), 4)
            except (ValueError, TypeError):
                comp["quantity"] = 0.0

            try:
                price = comp.get("unit_price", 0)
                if isinstance(price, str):
                    price = price.replace(',', '.')
                comp["unit_price"] = round(float(price), 2)
            except (ValueError, TypeError):
                comp["unit_price"] = 0.0

            # Tutarı hesapla
            comp["total_price"] = round(comp["quantity"] * comp["unit_price"], 2)

        return data
