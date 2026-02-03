
class ChainOfThoughtService:
    """
    Chain-of-Thought ile adım adım analiz.
    AI önce düşünür, sonra analiz oluşturur.
    """
    
    def build_cot_prompt(self, description: str, unit: str, context: str) -> str:
        """CoT prompt oluştur"""
        
        return f"""Sen 20+ yıl deneyimli bir Yaklaşık Maliyet Uzmanı İnşaat Mühendisisin.

GÖREV: Aşağıdaki imalat için birim fiyat analizi oluştur.

📌 TANIM: {description}
📌 BİRİM: {unit}

{context}

═══════════════════════════════════════════════════════════════
                    ADIM ADIM DÜŞÜN
═══════════════════════════════════════════════════════════════

Analiz oluşturmadan ÖNCE, aşağıdaki soruları yanıtla:

<thinking>
1. İMALAT TİPİ NEDİR?
   - [ ] Betonarme mi? (Demir ZORUNLU)
   - [ ] Yalın beton mu? (Demir YOK)
   - [ ] Hazır beton mu? (Çimento/kum/çakıl YOK)
   - [ ] Duvar mı? (Harç ZORUNLU)
   - [ ] Kazı mı?
   - [ ] Kaplama mı?
   - [ ] Diğer: ___

2. DOĞRU BİRİM NEDİR?
   - Kanal, boru = m (metre)
   - Duvar, döşeme, kaplama = m²
   - Kazı, beton hacim = m³
   - Prefabrik = adet
   
   → Bu imalat için doğru birim: ___

3. ZORUNLU BİLEŞENLER:
   - Bu imalat tipi için MUTLAKA olması gerekenler:
     □ ___
     □ ___
     □ ___

4. YASAK BİLEŞENLER:
   - Bu imalat için OLMAMASI gerekenler:
     ⛔ ___
     ⛔ ___

5. MİKTAR KONTROLÜ:
   - Emsal pozlara göre tipik miktarlar:
     - Malzeme X: ___ birim
     - İşçilik Y: ___ saat
     - Nakliye: ___ ton/m³

6. FİYAT KONTROLÜ:
   - Veritabanı/piyasa fiyatları:
     - Malzeme X: ___ TL
     - İşçilik Y: ___ TL/saat
</thinking>

═══════════════════════════════════════════════════════════════
                    SÖZLEŞME VE FORMAT
═══════════════════════════════════════════════════════════════

Yukarıdaki düşünme sürecini tamamladıktan sonra, sadece JSON formatında analiz sonucunu ver.
<thinking> taglarını çıktıya DAHİL ETME.
"""
