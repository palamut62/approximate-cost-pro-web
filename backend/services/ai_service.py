import json
import requests
import re
import os
import time
import logging
from typing import Dict, Any, Optional
from services.settings_service import get_settings_service

# Logger setup
logger = logging.getLogger("ai_service")


class APIError(Exception):
    """Custom exception for API errors with details"""
    def __init__(self, message: str, provider: str, status_code: int = None, retryable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.retryable = retryable


class AIAnalysisService:
    def __init__(self,
                 openrouter_key: Optional[str] = None,
                 model: str = None, # Dynamic from settings
                 base_url: str = "https://openrouter.ai/api/v1"):
        self.openrouter_key = openrouter_key or os.getenv("OPENROUTER_API_KEY")
        self.gemini_key = None # GEMINI DISABLED BY USER REQUEST
        self.settings_service = get_settings_service()
        self.model = model # If override provided, use it, else dynamic
        self.base_url = base_url

    def get_model(self, task: str = "analyze") -> str:
        """Get model ID from settings unless manually overridden"""
        if self.model:
            return self.model
        return self.settings_service.get_model_for_task(task)

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
                    "model": self.get_model("refine"),
                    "messages": messages,
                    "temperature": 0.3
                }
                response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=30)
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content'].strip()
            except Exception as e:
                logger.error(f"Refine Error (OpenRouter): {e}")

        return text # Hata durumunda orijinali döndür

    def refine_construction_request(self, text: str) -> str:
        """
        Kullanıcının basit talebini profesyonel bir poz analiz talebine dönüştürür.
        Örnek: "beton kanal" → "Beton trapeze kanal imalatı, C25/30 kaliteli hazır beton ile"
        """
        prompt = f"""Sen 20+ yıl deneyimli bir Yaklaşık Maliyet ve İhale Uzmanı İnşaat Mühendisisin.
Kullanıcının basit ve gayri resmi inşaat talebini, DETAYLI ve TEKNİK bir poz analiz talebine dönüştür.

═══════════════════════════════════════════════════════════════
KULLANICI TALEBİ: "{text}"
═══════════════════════════════════════════════════════════════

GÖREV:
Bu talebi, Çevre ve Şehircilik Bakanlığı birim fiyat analizi formatına uygun,
detaylı ve profesyonel bir poz tanımına dönüştür.

KURALLAR:
1. Teknik terimler kullan: imalat, metraj, rayiç, keşif, poz, birim fiyat
2. Malzeme kalitelerini belirt (C25/30, S420, vb.)
3. İmalat yöntemini netleştir (santral, elle, makine, vb.)
4. Ölçü birimlerini tahmin et (m, m², m³, adet)
5. Eksik detayları makul varsayımlarla tamamla

ÖRNEKLER:
❌ "beton kanal"
✅ "Beton trapeze kanal imalatı (40x60 cm), C25/30 kaliteli hazır beton ile santral pompası kullanılarak döküm"

❌ "duvar"
✅ "20 cm kalınlığında yatay delikli tuğla duvar örülmesi, çimento harcı ile"

❌ "kazı"
✅ "Temel kazısı (her türlü zemin), ekskavatör ile 0-2 metre derinlik"

❌ "santral beton"
✅ "Hazır beton C25/30 kaliteli, beton santrali ile pompa ile sevk ve yerleştirilmesi"

ÇIKTI:
- SADECE dönüştürülmüş profesyonel metni yaz
- Hiçbir açıklama veya ek yorum ekleme
- Kısa, öz ve teknik ol (max 2 satır)
"""

        messages = [
            {"role": "system", "content": "Sen Yaklaşık Maliyet ve İhale Uzmanı bir İnşaat Mühendisisin. Basit talepleri profesyonel poz tanımlarına dönüştürürsün."},
            {"role": "user", "content": prompt}
        ]

        if self.openrouter_key:
            try:
                headers = {
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": self.get_model("refine"),
                    "messages": messages,
                    "temperature": 0.4
                }
                response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=30)
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content'].strip()
            except Exception as e:
                print(f"Refine Request Error (OpenRouter): {e}")



        return text  # Hata durumunda orijinali döndür

    def review_analysis(self, analysis_data: Dict[str, Any], description: str) -> Dict[str, Any]:
        """
        Analizi LLM (Kıdemli Mühendis) ile inceler.
        Mantık hatalarını, eksik kalemleri ve fiyat tutarsızlıklarını semantik olarak kontrol eder.
        """
        prompt = f"""Sen Çevre ve Şehircilik Bakanlığı standartlarına hakim, 30 yıllık tecrübeli bir KIDEMLİ İHALE BAŞMÜHENDİSİSİN.
Görevin, önüne gelen birim fiyat analizini (yaklaşık maliyet cetvelini) denetlemek ve hataları bulmaktır.

═══════════════════════════════════════════════════════════════
ANALİZ EDİLECEK İŞ TANIMI:
"{description}"

MEVCUT ANALİZ VERİLERİ:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}
═══════════════════════════════════════════════════════════════

DENETİM VE ELEŞTİRİ KURALLARI:

1. YAPIM TEKNİĞİ VE MANTIK KONTROLÜ:
   - Seçilen imalat yöntemi, iş tanımına uygun mu?
   - Örneğin: "Beton santrali" denmişse, elle karışım pozları (çimento+kum+çakıl) OLMAMALIDIR! Hazır beton olmalıdır.
   - Örneğin: "Betonarme" denmişse, DEMİR ve KALIP mutlaka olmalıdır.
   - Örneğin: "Duvar" varsa, HARÇ mutlaka olmalıdır (harçsız duvar hariç).

2. EKSİK KALEM KONTROLÜ:
   - İşin tamamlanması için zorunlu olan yan imalatlar var mı?
   - Örn: Kazı varsa dolgu veya nakliye var mı?
   - Örn: Boya varsa astar var mı?

3. FİYAT VE MİKTAR TUTARLILIĞI:
   - Miktarlar gerçekçi mi? (Örn: 1 m³ beton için 2 m³ kum yazılmışsa HATA)
   - Fiyatlar güncel piyasa/ÇŞB rayiçleriyle uyumlu mu? (Aşırı düşük/yüksek mi?)

4. ŞÜPHELİ DURUMLAR:
   - Aynı iş için hem makine hem el işçiliği mükerrer yazılmış mı?
   - Uyumsuz birimler var mı? (Metre tül işi m³ olarak hesaplanmış mı?)

═══════════════════════════════════════════════════════════════
ÇIKTI FORMATI (SADECE JSON):

{{
  "status": "ok" | "warning" | "error",
  "issues": [
    {{
      "severity": "critical" | "warning" | "info",
      "category": "Mantık Hatası" | "Eksik Kalem" | "Fiyat Hatası" | "Miktar Hatası",
      "message": "Hata açıklaması (kısa ve net)",
      "suggestion": "Nasıl düzeltilmeli? (teknik öneri)"
    }}
  ],
  "general_comment": "Genel değerlendirme notun (opsiyonel)"
}}

Eğer analiz MÜKEMMEL ise "issues" listesini boş bırak ve status="ok" döndür.
Çok katı ve dikkatli ol. Hata yoksa zorlama.
"""

        errors = []

        # Try OpenRouter first (LLM call)
        if self.openrouter_key:
            try:
                headers = {
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json",
                     "HTTP-Referer": "https://approximatecostpro.com",
                     "X-Title": "Approximate Cost Pro"
                }
                data = {
                    "model": self.get_model("critic"), 
                    "messages": [
                        {"role": "system", "content": "Sen hata affetmeyen, titiz bir Başmühendissin. JSON formatında yanıt verirsin."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                }
                logger.info("LLM Critic (OpenRouter) çağrılıyor...")
                response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=60)
                response.raise_for_status()
                content = response.json()['choices'][0]['message']['content']
                return self._process_response(content)
            except Exception as e:
                errors.append(f"OpenRouter Critic Error: {e}")

        # Try Gemini (LLM call)
            except Exception as e:
                errors.append(f"OpenRouter Critic Error: {e}")

        # If LLM fails, return empty result (let rule-based system handle it)
        print(f"LLM Critic Failed: {errors}")
        return {"status": "ok", "issues": [], "general_comment": "LLM servisi yanıt vermedi, yerel kurallar geçerli."}

    def generate_analysis(
        self,
        description: str,
        unit: str,
        context_data: str = "",
        model: str = None,
        temperature: float = None
    ) -> Dict[str, Any]:
        """
        Analiz oluşturma ana fonksiyonu.
        Retry mekanizması ve fallback desteği ile.

        Args:
            description: İmalat tanımı
            unit: Birim (m, m², m³, adet, vb.)
            context_data: RAG context verisi
            model: Kullanılacak model (None ise varsayılan)
            temperature: LLM temperature (None ise varsayılan 0.1)
        """
        prompt = self._build_professional_prompt(description, unit, context_data)
        errors = []

        # Try OpenRouter first if key exists (with retry)
        if self.openrouter_key:
            for attempt in range(3):
                try:
                    logger.info(f"OpenRouter API çağrısı (deneme {attempt + 1}/3)")
                    return self._call_openrouter(prompt, model=model, temperature=temperature)
                except APIError as e:
                    errors.append(f"OpenRouter: {e}")
                    if e.retryable and attempt < 2:
                        wait_time = (attempt + 1) * 2  # 2, 4 saniye
                        logger.warning(f"Retry beklemesi: {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    break
                except Exception as e:
                    errors.append(f"OpenRouter: {e}")
                    logger.error(f"OpenRouter hatası: {e}")
                    break

        # Fallback to Gemini if key exists (with retry)
                    logger.error(f"OpenRouter hatası: {e}")
                    break

        # All providers failed
        error_summary = "; ".join(errors) if errors else "API anahtarı bulunamadı"
        raise Exception(f"AI servisleri başarısız: {error_summary}")

    def _build_professional_prompt(self, description: str, unit: str, context_data: str) -> str:
        """
        Türkiye inşaat sektörüne özel, profesyonel ve detaylı prompt.
        2025 yılı Çevre ve Şehircilik Bakanlığı normlarına uygun.
        """
        return f"""Sen Türkiye'de 20+ yıl deneyimli bir YAKLAŞIK MALİYET ve İHALE UZMANI İnşaat Mühendisisin.

UZMANLIKLARIN:
• Çevre ve Şehircilik Bakanlığı birim fiyat analiz formatları
• İhale dosyası hazırlama ve keşif metrajı düzenleme
• Piyasa rayiç fiyatları ve maliyet optimizasyonu
• Teknik şartname ve poz analizi oluşturma
• Kamu İhale Kanunu ve ÇŞB standartları

SEN BİR İHALE UZMANISIN, bu nedenle:
✓ Fiyatlar gerçekçi ve piyasa rayiçlerine uygun olmalı
✓ Her poz detaylı ve ihale dosyasına eklemeye hazır olmalı
✓ Malzeme kaliteleri ve normlar açıkça belirtilmeli
✓ Hesaplamalar ÇŞB standartlarına uygun olmalı

═══════════════════════════════════════════════════════════════
                        GÖREV
═══════════════════════════════════════════════════════════════

Aşağıdaki poz tanımı için detaylı birim fiyat analizi oluştur:

📌 POZ TANIMI: {description}
📌 BİRİM (REFERANS): {unit} (Bu sadece referanstır, sen imalat türüne göre EN UYGUN birimi belirle!)

═══════════════════════════════════════════════════════════════
                   MEVCUT VERİTABANI BİLGİLERİ
═══════════════════════════════════════════════════════════════

{context_data if context_data else "Veritabanında benzer poz bulunamadı. Genel bilgilerini kullan."}

⚠️ ÖNEMLİ: Yukarıdaki pozlar SEMANTİK ETİKET SİSTEMİ ile filtrelenmiştir.
Eğer "🏷️ ARANAN ÖZELLİKLER" kısmı varsa, o etiketlere uygun pozları kullan!
Örnek: "hazir_beton" etiketi varsa → 15.150.xxxx kodlu HAZIR BETON pozlarını kullan
Örnek: "beton_harci" etiketi varsa → Çimento + Kum + Çakıl karışımı kullan

═══════════════════════════════════════════════════════════════
                        KURALLAR
═══════════════════════════════════════════════════════════════

⚠️ KRİTİK UYARI 1 - BİRİM BELİRLEME:

🎯 İMALAT TÜRÜNE GÖRE DOĞRU BİRİMİ OTOMATIK BELİRLE:

📏 UZUNLUK İMALATLARI (m):
   • Boru döşeme, kanal imalatı, hendek kazısı
   • Boru (her türlü), kanal, mazgal, yol şeridi
   • Hat boyunca devam eden işler
   • Örnek: "Beton trapeze kanal imalatı" → m
   • Örnek: "PVC boru döşeme" → m
   • Örnek: "Bordür taşı döşeme" → m

📐 ALAN İMALATLARI (m²):
   • Duvar, döşeme (düz), çatı, kaplama, sıva, boya
   • Yüzey işleri, kaplama işleri
   • Örnek: "20 cm gazbeton duvar" → m²
   • Örnek: "Seramik kaplama" → m²
   • Örnek: "Sıva işleri" → m²

📦 HACİM İMALATLARI (m³):
   • Kazı, dolgu, moloz, beton (hacim olarak)
   • Hacim hesabı gerektiren işler
   • Örnek: "Temel kazısı" → m³
   • Örnek: "Kum dolgu" → m³
   • Örnek: "Beton dolgu" → m³

🔢 ADET/TON/KG İMALATLARI:
   • Prefabrik elemanlar → adet
   • Demir/çelik malzeme → ton veya kg
   • Kapı, pencere, cihaz → adet
   • Örnek: "Prefabrik direk" → adet
   • Örnek: "Nervürlü demir" → ton

⚠️ DİKKAT: Yukarıdaki referans birim "{unit}" ise GÖRMEZDEN GEL!
İmalat türüne göre EN UYGUN birimi "suggested_unit" alanına yaz!

═══════════════════════════════════════════════════════════════

⚠️ KRİTİK UYARI 2 - BETON SANTRALI vs BETON HARCI:

🏭 BETON SANTRALI İLE GETİRİLEN BETON (HAZIR BETON):
   • Anahtar kelimeler: "santral", "santrali ile", "santralde hazır", "pompa ile"
   • Malzeme: 15.150.xxxx kodlu HAZIR BETON (örn: C25/30 hazır beton)
   • Birim: m³
   • İşçilik: Sadece DÖKME işçiliği (karıştırma yok!)
   • Örnek: "Beton santrali ile dökülen C25 beton" → 15.150.1005 Hazır Beton C25/30

🧱 ŞANTİYEDE KARILAN BETON HARCI (GELENEKSEL):
   • Anahtar kelimeler: "harcı", "karışım", "elle", "şantiyede"
   • Malzemeler: Çimento + Kum + Çakıl + Su (AYRI AYRI!)
   • İşçilik: Karıştırma + Dökme
   • Örnek: "Beton harcı" → Çimento 10.130.1202 + Kum + Çakıl

⚠️ DİKKAT: "Beton santrali" ifadesi görürsen ASLA çimento+kum+çakıl yazma!
Sadece HAZIR BETON poz numarasını kullan!

⚠️ ASLA HAZIR BETON + ÇİMENTO/KUM/ÇAKIL BIRLIKTE OLMASIN!
Bu mantıken yanlış! Hazır beton zaten karıştırılmış gelir.

═══════════════════════════════════════════════════════════════

⚠️ KRİTİK UYARI 2.5 - GROBETON (AYRI MALZEME!):

🔷 GROBETON NEDİR?
   • Düşük kaliteli beton (genelde C15/20 veya C20/25)
   • Temel altı, taban dolgu, dolgu işleri için kullanılır
   • ANA BETON'DAN AYRI BİR MALZEMEDIR!

🔷 GROBETON NASIL EKLENİR?
   Eğer kullanıcı "grobeton", "taban betonu", "dolgu betonu" diyorsa:

   → AYRI bir malzeme kalemi olarak ekle:

   MALZEME:
   1. C30/37 Hazır Beton (Ana yapı için) - X m³
   2. C15/20 Grobeton (Taban dolgu için) - Y m³  ← AYRI KALEM!

   NAKLİYE:
   1. C30/37 Beton nakliyesi
   2. Grobeton nakliyesi  ← AYRI NAKLİYE!

🔷 ÖRNEK (YANLIŞ vs DOĞRU):

❌ YANLIŞ:
   • C30/37 Hazır Beton: 1.0 m³
   • Grobeton nakliyesi: 0.25 m³  (Malzeme yok, sadece nakliye!)

✅ DOĞRU:
   • C30/37 Hazır Beton: 1.0 m³
   • C15/20 Grobeton: 0.25 m³  (AYRI MALZEME!)
   • C30/37 Beton nakliyesi: 1.0 m³
   • Grobeton nakliyesi: 0.25 m³

═══════════════════════════════════════════════════════════════

⚠️ KRİTİK UYARI 3 - BETON VE BETONARME FARKI:

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

2. MİKTAR HESAPLAMA (1 {unit} için) - KİK STANDARTLARI:

   ⚠️ KRİTİK: Miktarlar RASTGELE yazılamaz! Resmî analizler ve ÇŞB normları esas alınmalıdır.

   📌 MALZEME FİRE ORANLARI (4734 sayılı KİK kabul gören değerler):
     • Demir/Çelik: %3-5 fire
     • Beton: %1-2 fire
     • Kalıp: %5-10 fire (yıpranma)
     • Tuğla/Blok: %3-5 fire
     • Çimento: %2-3 fire
     • Agregalar: %3-5 fire

   📌 İŞÇİLİK SÜRELERİ (adam/saat veya adam/gün formatında):
     ⚠️ Bu süreler KİK resmî analizlerinden alınmıştır, keyfi değildir!
     • Duvar örme: 0.8-1.2 adam/saat per m²
     • Beton dökme: 1.5-2.0 adam/saat per m³
     • Sıva işleri: 0.6-0.8 adam/saat per m²
     • Demir işçiliği: 8-12 adam/saat per ton
     • Kazı (elle): 0.4-0.6 adam/saat per m³
     • Kalıp yapma: 1.5-2.5 adam/saat per m²

   📌 MAKİNE SÜRELERİ VE KAPASİTELER:
     • Beton pompası: 30-40 m³/saat kapasiteli → 1 m³ için 0.025-0.033 saat
     • Ekskavatör (kazı): 40-60 m³/saat → 1 m³ için 0.017-0.025 saat
     • Betoniyer: 0.5-1.0 m³/saat → 1 m³ için 1.0-2.0 saat
     • Vibratör: Genelde işçilik içinde, ayrıca yazılmaz

   ⚠️ EMSAL POZ KULLANIMI:
     • Yukarıda veritabanından gelen pozlar EMSAL POZ'dur
     • Özel poz yazıyorsan mutlaka benzer emsal poza referans ver
     • Miktarları emsal pozdan uyarla, sıfırdan uydurma!

3. NAKLİYE HESABI (4734 KİK - varsayılan 20 km):
   • Her malzeme için nakliye kalemi ZORUNLU
   • Nakliye mesafesi: 20 km (varsayılan)
   • Birim: ton veya m³
   • Yoğunluklar (standart değerler):
     - Beton: 2.4 t/m³
     - Kum: 1.6 t/m³
     - Çakıl: 1.8 t/m³
     - Demir: 7.85 t/m³
     - Taş: 2.5 t/m³
     - Tuğla: 1.4 t/m³

4. FİYATLAR (İHALE UZMANI YAKLAŞIMI - 4734 KİK):
   • ✅ ÖNCE: Yukarıdaki veritabanı fiyatlarını KULLAN (ÇŞB resmî rayiçleri)
   • ⚠️ Veritabanında yoksa: 2025 yılı piyasa ortalaması tahmin et
   • Fiyatlar GERÇEKÇI ve İHALE DOSYASINDAKİ KALİTEDE olmalı
   • Fiyatlar TL cinsinden, virgülsüz yaz (örn: 125.50)
   • ❌ Çok düşük fiyat → Aşırı düşük sorgulamasında elenme sebebi!
   • ❌ Çok yüksek fiyat → İhale kayıp!

   📌 GENEL GİDER + KÂR:
     • %25 (Yüklenici kârı + genel giderler)
     • ⚠️ ASLA ayrı satır olarak yazma!
     • Birim fiyatlara yedirilmiş kabul edilir (explanation'da belirt)

5. İHALE DOSYASI UYGUNLUĞU:
   • Her poz açıklaması net ve teknik olmalı
   • Malzeme kaliteleri belirtilmeli (C25/30, S420 vb.)
   • İmalat yöntemi netleştirilmeli (santral, elle, makine vb.)
   • Ölçü birimleri doğru seçilmeli

═══════════════════════════════════════════════════════════════
                      ÇIKTI FORMATI
═══════════════════════════════════════════════════════════════

SADECE aşağıdaki JSON formatında yanıt ver, başka hiçbir şey yazma:

{{
  "suggested_unit": "İMALAT TÜRÜNE GÖRE BELİRLEDİĞİN BİRİM (m/m²/m³/adet/ton/kg)",
  "explanation": "Bu poz analizi 4734 sayılı Kamu İhale Kanunu ve Çevre Şehircilik Bakanlığı 2025 yılı standartlarına uygun olarak hazırlanmıştır.

📋 DAYANAK NORMLAR:
• Malzeme miktarları: [ÇŞB/DSİ/Karayolları] birim fiyat analizleri esas alınmıştır
• İşçilik süreleri: Resmî işçilik normları (adam/saat) kullanılmıştır
• Fire oranları: KİK kabul gören standart değerler uygulanmıştır (Demir %3-5, Beton %1-2, Kalıp %5-10)
• Birim fiyatlar: 2025 yılı ÇŞB veritabanı fiyatları ve piyasa rayiçleri baz alınmıştır
• Nakliye mesafesi: 20 km kabul edilmiştir

⚠️ ÖZEL NOTLAR:
• Genel gider ve yüklenici kârı (%25) birim fiyatlara yedirilmiştir
• Bu analiz ihale dosyalarında kullanıma uygun formattadır
• Emsal poz referansları veritabanından alınmıştır",
  "technical_specification": "Beton üretimine uygun komple beton tesisinde (asgari 60m³/sa kapasiteli...) standardına uygun...
  
Ölçü: Projedeki boyutlar üzerinden hesaplanır.
  
Not: 
1) Üretilen betonun TSE belgeli olması zorunludur.
2) Pompa bedeli analizden düşülür.",
  "components": [
    {{
      "type": "Malzeme",
      "code": "10.130.1202",
      "name": "Portland Çimentosu CEM I 42.5 R (%3 fire dahil)",
      "unit": "ton",
      "quantity": 0.3090,
      "unit_price": 4250.00
    }},
    {{
      "type": "Malzeme",
      "code": "10.130.1004",
      "name": "İnce agrega (kum) 0-5 mm (%5 fire dahil)",
      "unit": "m³",
      "quantity": 0.4725,
      "unit_price": 350.00
    }},
    {{
      "type": "İşçilik",
      "code": "10.100.1015",
      "name": "Betoncu ustası (1.5 adam/saat)",
      "unit": "sa",
      "quantity": 1.5000,
      "unit_price": 185.50
    }},
    {{
      "type": "İşçilik",
      "code": "10.100.1045",
      "name": "Betoncu yardımcısı (2.0 adam/saat)",
      "unit": "sa",
      "quantity": 2.0000,
      "unit_price": 165.00
    }},
    {{
      "type": "Nakliye",
      "code": "15.100.1001",
      "name": "Çimento nakliyesi 20 km (0.31 ton × 2.4 t/m³)",
      "unit": "ton",
      "quantity": 0.7440,
      "unit_price": 25.00
    }}
  ]
}}

⚠️ ÖNEMLİ KURALLAR:
1. Malzeme name alanında FİRE ORANINI belirt: "(%3 fire dahil)"
2. İşçilik name alanında ADAM/SAAT süresini belirt: "(1.5 adam/saat)"
3. Nakliye name alanında HESAPLAMA DETAYlarını belirt: "(0.31 ton × 2.4)"
4. Quantity değerleri REALİSTİK olmalı, emsal pozlardan uyarla
5. Her component name NET ve TEKNİK olmalı (ihale dosyasında kullanılacak)

ÖNEMLİ:
• Her malzeme için ayrı nakliye kalemi ekle
• Miktarları 4 ondalık basamakla yaz
• Fiyatları 2 ondalık basamakla yaz
• JSON dışında hiçbir şey yazma"""

    def _call_openrouter(self, prompt: str, model: str = None, temperature: float = None) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://approximatecostpro.com",
            "X-Title": "Approximate Cost Pro"
        }
        data = {
            "model": model or self.get_model("analyze"),
            "messages": [
                {
                    "role": "system",
                    "content": "Sen Türkiye'de çalışan Yaklaşık Maliyet ve İhale Uzmanı bir İnşaat Mühendisisin. 4734 sayılı Kamu İhale Kanunu, ÇŞB/DSİ/Karayolları birim fiyat analizleri ve resmî işçilik normlarına hâkimsin. İhale dosyaları hazırlama konusunda 20+ yıl deneyime sahipsin. Poz analizleri oluştururken:\n\n• Malzeme miktarlarını ÇŞB resmî analizlerinden alırsın\n• Fire oranlarını KİK kabul gören değerlerde uygularsın (Demir %3-5, Beton %1-2, Kalıp %5-10)\n• İşçilik sürelerini adam/saat formatında ve resmî normlara uygun yazarsın\n• Makine kapasitelerini ve sürelerini gerçekçi hesaplarsın\n• Emsal poz referanslarını mutlaka kullanırsın\n• Nakliye mesafesini 20 km kabul edersin\n• Genel gider + kâr (%25) birim fiyatlara yedirilmiştir, ayrı satır yazmassın\n\nSadece JSON formatında, aşırı düşük sorgulamasında geçebilecek kalitede, gerçekçi ve piyasa rayiçlerine uygun analiz yanıtları verirsin."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature if temperature is not None else 0.1,
            "max_tokens": 4000
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=120
            )
        except requests.exceptions.Timeout:
            raise APIError("İstek zaman aşımına uğradı (120s)", "OpenRouter", retryable=True)
        except requests.exceptions.ConnectionError:
            raise APIError("Bağlantı hatası", "OpenRouter", retryable=True)

        # Handle HTTP errors
        if response.status_code == 429:
            raise APIError("Rate limit aşıldı", "OpenRouter", 429, retryable=True)
        elif response.status_code == 401:
            raise APIError("API anahtarı geçersiz", "OpenRouter", 401, retryable=False)
        elif response.status_code == 503:
            raise APIError("Servis geçici olarak kullanılamıyor", "OpenRouter", 503, retryable=True)
        elif response.status_code >= 500:
            raise APIError(f"Sunucu hatası ({response.status_code})", "OpenRouter", response.status_code, retryable=True)
        elif response.status_code >= 400:
            error_detail = response.text
            try:
                error_detail = response.json()
            except:
                pass
            raise APIError(f"İstek hatası ({response.status_code}): {error_detail}", "OpenRouter", response.status_code, retryable=False)

        response.raise_for_status()
        resp_json = response.json()
        logger.debug(f"OpenRouter Response: {json.dumps(resp_json)[:1000]}...") # Log first 1000 chars
        content = resp_json['choices'][0]['message']['content']
        return self._process_response(content)



    def _process_response(self, content: str) -> Dict[str, Any]:
        """JSON temizleme ve onarma"""
        # Markdown bloklarını temizle
        content = re.sub(r'```json\s*|\s*```', '', content).strip()

        # Önce doğrudan parse etmeyi dene
        try:
            return self._finalize_data(json.loads(content, strict=False))
        except json.JSONDecodeError:
            pass

        # JSON'ı metin içinden ayıkla (en dıştaki { })
        match = re.search(r'(\{[\s\S]*\})', content)
        if match:
            json_str = match.group(1)

            # Geçersiz kontrol karakterlerini temizle
            json_str = self._clean_control_characters(json_str)

            try:
                return self._finalize_data(json.loads(json_str, strict=False))
            except Exception as e:
                # JSON onarma dene
                repaired = self._repair_json(json_str)
                try:
                    return self._finalize_data(json.loads(repaired, strict=False))
                except Exception as json_err:
                    logger.error(f"JSON Decode Error. Raw content:\n{content}")
                    raise Exception(f"AI yanıtı geçerli JSON'a dönüştürülemedi: {str(json_err)} | RAW: {content[:500]}...")

        logger.error(f"No JSON found in response. Raw content:\n{content}")
        raise Exception(f"AI yanıtında JSON bulunamadı: {content[:500]}...")

    def _clean_control_characters(self, json_str: str) -> str:
        """JSON string içindeki geçersiz kontrol karakterlerini temizle"""
        # ASCII control characters (0-31) hariç \t, \n, \r
        # Bu karakterleri boşluk ile değiştir
        cleaned = ''
        for char in json_str:
            code = ord(char)
            # 0-31 arasındaki kontrol karakterleri, ama \t(9), \n(10), \r(13) hariç
            if 0 <= code < 32 and code not in (9, 10, 13):
                cleaned += ' '  # Geçersiz karakteri boşlukla değiştir
            else:
                cleaned += char
        return cleaned

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
