# 🔄 AI Feedback Sistemi Entegrasyonu

**Tarih:** 2026-01-29
**Durum:** ✅ Tamamlandı ve Aktif

---

## 📋 Özet

Desktop uygulamasına AI feedback (geri bildirim) sistemi entegre edildi. Kullanıcılar AI sonuçlarını düzelttiğinde, bu düzeltmeler kaydedilir ve gelecekteki AI analizlerinde kullanılır. Sistem böylece **sürekli öğrenir ve gelişir**.

---

## 🎯 Amaç

### Sorun
- AI bazen yanlış malzeme ekliyor (ör: "beton trapez" için demir eklemesi)
- AI bazen gerekli malzemeleri unutuyor (ör: kalıp eksikliği)
- Kullanıcı her seferinde manuel düzeltme yapıyor
- **Düzeltmeler kayboluyordu, AI öğrenmiyordu**

### Çözüm
1. ✅ Kullanıcı AI sonucunu düzeltir
2. ✅ "📝 AI Düzeltmesi Kaydet" butonuna basar
3. ✅ Düzeltme tipi ve açıklama girer
4. ✅ Sistem düzeltmeyi veritabanına kaydeder
5. ✅ Gelecekte benzer poz için AI analiz yaparken, **bu düzeltmelerden öğrenir**
6. ✅ AI sürekli iyileşir

---

## 🔧 Teknik Uygulama

### 1. Yeni Dosyalar

#### `ui/feedback_dialog.py` (NEW - ~500 satır)

**AIFeedbackDialog Sınıfı:**
- Kullanıcıya AI vs Düzeltilmiş bileşenleri gösterir
- Düzeltme tipi seçimi:
  - ❌ Eksik Malzeme/İşçilik
  - ⚠️ Yanlış Malzeme Eklendi
  - 📊 Miktar Yanlış
  - 💰 Fiyat Yanlış
  - 🔧 Yöntem/Mantık Hatası
  - 📝 Diğer
- Düzeltme açıklaması text alanı
- Değişiklik özeti (eklenen/çıkarılan malzemeler)
- Paylaşım ayarları (anonim)

**FeedbackManagerDialog Sınıfı:**
- Kaydedilmiş feedback'leri listeleme
- Feedback istatistikleri
- Feedback silme/yönetme

---

### 2. Değişiklikler - `analysis_builder.py`

#### Import Eklendi (Satır 9)
```python
from ui.feedback_dialog import AIFeedbackDialog
```

#### Feedback Butonu Eklendi (Satır 815-822)
```python
# AI Feedback butonu
self.feedback_btn = QPushButton("📝 AI Düzeltmesi Kaydet")
self.feedback_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 12px; font-weight: bold;")
self.feedback_btn.clicked.connect(self.save_ai_feedback)
self.feedback_btn.setEnabled(False)  # Başlangıçta deaktif
self.feedback_btn.setToolTip("AI sonucunu düzelttiyseniz, düzeltmenizi kaydedin.\nBu sayede AI gelecekte daha iyi sonuçlar üretir.")
save_btns_layout.addWidget(self.feedback_btn)
```

#### on_ai_finished() Metoduna Ekleme (Satır 1079-1081)
```python
# Orijinal AI sonucunu sakla (feedback için)
self.original_ai_components = components.copy()

# Feedback butonunu aktifleştir
self.feedback_btn.setEnabled(True)
```

#### Feedback Context Entegrasyonu (Satır 918-921)
```python
# Feedback context'ini ekle (kullanıcı düzeltmelerinden öğren)
feedback_context = self.get_feedback_context(desc, unit)
if feedback_context:
    context_text += "\n" + feedback_context
```

#### Yeni Metodlar

**1. `save_ai_feedback()` (Satır 1619-1694)**
```python
def save_ai_feedback(self):
    """AI sonucunun kullanıcı düzeltmelerini kaydet"""

    # 1. Orijinal AI sonucu var mı kontrol et
    # 2. Mevcut tablodan düzeltilmiş bileşenleri topla
    # 3. Değişiklik var mı kontrol et
    # 4. AIFeedbackDialog aç
    # 5. Kullanıcı onaylarsa veritabanına kaydet
    # 6. Başarı mesajı göster
```

**2. `_components_equal()` (Satır 1696-1713)**
```python
def _components_equal(self, components1, components2):
    """İki bileşen listesinin eşit olup olmadığını kontrol et"""

    # İsim, tip, miktar, fiyat karşılaştırması
    # Küçük farklılıkları tolere eder (0.001 miktar, 0.01 fiyat)
```

**3. `get_feedback_context()` (Satır 1715-1772)**
```python
def get_feedback_context(self, description, unit=None):
    """Benzer pozlar için kullanıcı düzeltmelerini getir"""

    # 1. Veritabanından ilgili feedback'leri al (limit=3)
    # 2. Her feedback için:
    #    - Düzeltme tipi ve açıklamayı formatla
    #    - Eklenen/çıkarılan malzemeleri göster
    # 3. AI'ye uyarı context'i döndür
```

---

### 3. Veritabanı (database.py)

**Mevcut Metodlar (Değişiklik yok):**

```python
def save_ai_feedback(
    self,
    original_prompt,
    original_unit,
    correction_type,
    correction_description,
    ai_components,
    correct_components,
    share_enabled=True
)
```

```python
def get_relevant_feedback(self, prompt: str, unit: str = None, limit: int = 5) -> list
```

**Tablo Yapısı:**
```sql
CREATE TABLE ai_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_prompt TEXT NOT NULL,
    original_unit TEXT,
    correction_type TEXT,
    correction_description TEXT,
    ai_components TEXT,  -- JSON
    correct_components TEXT,  -- JSON
    keywords TEXT,  -- JSON array
    share_enabled INTEGER DEFAULT 1,
    use_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_date TEXT,
    last_used_date TEXT
)
```

---

## 🔄 Kullanım Akışı

### Senaryo 1: AI Düzeltmesi Kaydetme

```
1. Kullanıcı: "Beton trapez" analiz iste
   ↓
2. AI: Analiz yap → Beton + Demir + Kalıp (YANLIŞ demir ekledi)
   ↓
3. Kullanıcı: Tablodan demiri siler
   ↓
4. Kullanıcı: "📝 AI Düzeltmesi Kaydet" butonuna basar
   ↓
5. Feedback Dialog açılır:
   - AI Önerisi: 3 bileşen (Beton, Demir, Kalıp)
   - Düzeltilmiş: 2 bileşen (Beton, Kalıp)
   - Çıkarılan: Betonarme Demiri
   ↓
6. Kullanıcı düzeltme tipini seçer:
   → "⚠️ Yanlış Malzeme Eklendi"
   ↓
7. Açıklama yazar:
   "Beton trapez donatısız beton olduğu için demir olmamalı. Sadece beton ve kalıp yeterli."
   ↓
8. "💾 Kaydet ve Paylaş" butonuna basar
   ↓
9. Sistem:
   - Veritabanına feedback kaydeder
   - Anahtar kelimeleri çıkarır: ["beton", "trapez", "donatısız"]
   - use_count = 0 olarak başlar
   ↓
10. Başarı mesajı:
    "✅ Düzeltmeniz kaydedildi!
    Bu feedback gelecekteki AI analizlerini iyileştirecek.
    Teşekkür ederiz! 🙏"
```

---

### Senaryo 2: Gelecekte Aynı Poz İçin Analiz

```
1. Kullanıcı (3 gün sonra): "C20/25 beton trapez" analiz iste
   ↓
2. Sistem:
   a) Anahtar kelimeler çıkar: ["beton", "trapez", "c20/25"]
   b) get_relevant_feedback() çağırır
   c) Veritabanından benzer feedback bulur (Senaryo 1'deki kayıt)
   ↓
3. Feedback Context oluşturulur:

   📚 GEÇMİŞ KULLANICI DÜZELTMELERİ (Bu hatalardan kaçının!):

   1. HATA - Beton trapez
      Sorun: ⚠️ Yanlış Malzeme Eklendi
      Açıklama: Beton trapez donatısız beton olduğu için demir olmamalı
      ❌ Kaldırılan (yanlış eklenmiş): Betonarme Demiri

   ⚠️ Yukarıdaki hataları TEKRAR ETMEYIN! Bu düzeltmelerden öğrenin.
   ↓
4. AI'ye gönderilen prompt:

   [Normal analiz promptu]

   + [PDF/CSV Context]

   + [Feedback Context]  ← YENİ!
   ↓
5. AI:
   - Feedback context'i okur
   - "Beton trapez için demir ekleme" uyarısını görür
   - Sadece Beton + Kalıp önerir ✅ DOĞRU!
   ↓
6. Kullanıcı sonucu görür: Beton + Kalıp (demir yok) ✅
   ↓
7. Sistem feedback use_count'ı artırır
```

---

## 📊 Feedback Context Formatı

### AI'ye Gönderilen Context Örneği

```
📚 GEÇMİŞ KULLANICI DÜZELTMELERİ (Bu hatalardan kaçının!):

1. HATA - Beton trapez
   Sorun: ⚠️ Yanlış Malzeme Eklendi
   Açıklama: Beton trapez donatısız beton olduğu için demir olmamalı. Sadece beton ve kalıp yeterli.
   ❌ Kaldırılan (yanlış eklenmiş): Betonarme Demiri
   ✅ Eklenen (unutulmuş): -

2. HATA - Betonarme kolon
   Sorun: ❌ Eksik Malzeme/İşçilik
   Açıklama: Kalıp malzemesi unutulmuş
   ❌ Kaldırılan (yanlış eklenmiş): -
   ✅ Eklenen (unutulmuş): Ahşap Kalıp

3. HATA - Duvar örgüsü
   Sorun: 📊 Miktar Yanlış
   Açıklama: Harç miktarı çok düşük hesaplanmış

⚠️ Yukarıdaki hataları TEKRAR ETMEYIN! Bu düzeltmelerden öğrenin.
```

---

## 🧪 Test Senaryoları

### Test 1: Beton Trapez (Demir Hatası)

**Öncesi (Feedback Yok):**
```json
AI Çıktısı: ["Beton C20/25", "Betonarme Demiri", "Ahşap Kalıp"]
               ❌ YANLIŞ
```

**Feedback Kaydedildi:**
```
Düzeltme: "Betonarme Demiri" kaldırıldı
Açıklama: "Donatısız beton için demir olmaz"
```

**Sonrası (Feedback Kullanıldı):**
```json
AI Çıktısı: ["Beton C20/25", "Ahşap Kalıp"]
               ✅ DOĞRU (feedback'ten öğrendi)
```

---

### Test 2: Betonarme Kolon (Kalıp Unutma)

**Öncesi:**
```json
AI Çıktısı: ["Beton C25/30", "Nervürlü Betonarme Çeliği"]
               ❌ Kalıp eksik
```

**Feedback Kaydedildi:**
```
Düzeltme: "Ahşap Kalıp" eklendi
Açıklama: "Betonarme için kalıp zorunlu"
```

**Sonrası:**
```json
AI Çıktısı: ["Beton C25/30", "Nervürlü Betonarme Çeliği", "Ahşap Kalıp"]
               ✅ DOĞRU
```

---

## 📈 Feedback İstatistikleri

### Veritabanı Sorguları

**Toplam feedback sayısı:**
```sql
SELECT COUNT(*) FROM ai_feedback WHERE is_active = 1;
```

**En çok kullanılan feedback'ler:**
```sql
SELECT original_prompt, use_count
FROM ai_feedback
WHERE is_active = 1
ORDER BY use_count DESC
LIMIT 10;
```

**Düzeltme tipi dağılımı:**
```sql
SELECT correction_type, COUNT(*) as count
FROM ai_feedback
WHERE is_active = 1
GROUP BY correction_type;
```

---

## 🔧 Teknik Detaylar

### Feedback Benzerlik Algoritması

**`database.py:get_relevant_feedback()` metodu:**

1. **Keyword Extraction:**
   ```python
   prompt_keywords = ["beton", "trapez", "c20", "c25"]
   ```

2. **Benzerlik Puanı:**
   ```python
   score = (common_keywords / total_keywords) * 100
   ```

3. **Sıralama:**
   - Önce benzerlik puanına göre
   - Sonra use_count (kullanım sayısı)
   - Son olarak tarih

4. **Limit:**
   - En fazla 3 feedback döndürülür
   - Token limiti aşılmasın diye

---

### Feedback Kaydetme Akışı

```python
# 1. Dialog'dan veri al
feedback_data = {
    'original_prompt': "Beton trapez",
    'original_unit': "m³",
    'correction_type': "wrong_item",
    'correction_description': "Donatısız beton için demir olmaz",
    'ai_components': [...],
    'correct_components': [...],
    'share_enabled': True
}

# 2. Anahtar kelimeleri çıkar
keywords = ["beton", "trapez", "donatısız"]

# 3. Veritabanına kaydet
db.save_ai_feedback(
    original_prompt=feedback_data['original_prompt'],
    ...
)

# 4. use_count = 0, is_active = 1 olarak başlar
```

---

## 🎨 UI Görünümü

### Feedback Butonu
```
┌────────────────────────────────────────────────────────────┐
│ 💾 Analizi Veritabanına Kaydet                             │
│ 💾 + 💰 Kaydet ve Projeye Ekle                             │
│ 📄 PDF Olarak Kaydet                                       │
│ 📝 AI Düzeltmesi Kaydet  ← YENİ!                          │
└────────────────────────────────────────────────────────────┘
```

**Tooltip:**
```
AI sonucunu düzelttiyseniz, düzeltmenizi kaydedin.
Bu sayede AI gelecekte daha iyi sonuçlar üretir.
```

### Feedback Dialog

```
┌─────────────────────────────────────────────────────────────┐
│ 🎯 AI Sonucunu Değerlendirin ve Sistemi İyileştirin         │
├─────────────────────────────────────────────────────────────┤
│ 💡 Neden Önemli?                                            │
│ Düzeltmeleriniz sisteme kaydedilir ve gelecekte benzer     │
│ sorgular için AI daha doğru sonuçlar üretir.               │
├─────────────────────────────────────────────────────────────┤
│ 📋 Poz Bilgisi                                              │
│ Poz Tanımı: Beton trapez                                    │
│ Birim: m³                                                    │
├─────────────────────────────────────────────────────────────┤
│ 🔍 Düzeltme Tipi                                            │
│ [⚠️ Yanlış Malzeme/İşçilik Eklendi         ▼]              │
├─────────────────────────────────────────────────────────────┤
│ 📝 Düzeltme Açıklaması                                      │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Beton trapez donatısız beton olduğu için demir     │   │
│ │ olmamalı. Sadece beton ve kalıp yeterli.           │   │
│ └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│ 📊 Değişiklik Özeti                                         │
│ AI Önerisi: 3 bileşen                                       │
│ Düzeltilmiş: 2 bileşen                                      │
│                                                              │
│ ➖ Çıkarılan (1):                                           │
│   • Betonarme Demiri                                        │
├─────────────────────────────────────────────────────────────┤
│ 🌐 Paylaşım Ayarları                                        │
│ ☑ Bu düzeltmeyi sistemle paylaş (Anonim)                   │
│ ℹ️  Düzeltmeniz anonim olarak kaydedilir                   │
├─────────────────────────────────────────────────────────────┤
│           [💾 Kaydet ve Paylaş]  [⏭️ Atla]                 │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Ayarlar ve Yapılandırma

### Feedback Limiti

**analysis_builder.py:1720**
```python
feedbacks = self.db.get_relevant_feedback(description, unit=unit, limit=3)
```

**Değiştirilebilir:**
- `limit=3` → Daha fazla feedback için artırın (ör: 5)
- Daha fazla feedback = Daha fazla context = Daha yüksek token kullanımı

### Feedback Aktifliği

**database.py - is_active flag:**
```sql
WHERE is_active = 1
```

- Kullanıcı feedback'i silmek isterse `is_active = 0` yapılır
- Tamamen silinmez, arşivlenir

---

## 🔍 Debugging ve Log

### Console Output

**Feedback kaydedilirken:**
```
[FEEDBACK] Feedback context alınıyor: Beton trapez
[FEEDBACK] 2 ilgili feedback bulundu
[FEEDBACK] Context oluşturuldu (450 karakter)
```

**Feedback kullanılırken:**
```
[FEEDBACK] Feedback context eklendi (3 feedback)
[AI] Analiz başlatılıyor...
```

**Hata durumunda:**
```
[FEEDBACK] Feedback context alınırken hata: <hata detayı>
```

---

## 🚀 Gelecek İyileştirmeler

### 1. Otomatik Feedback Önerisi
```python
if user_changed_more_than_2_components():
    auto_show_feedback_dialog()
```

### 2. Feedback Voting
Kullanıcılar başkalarının feedback'lerini oylar:
```sql
ALTER TABLE ai_feedback ADD COLUMN upvotes INTEGER DEFAULT 0;
ALTER TABLE ai_feedback ADD COLUMN downvotes INTEGER DEFAULT 0;
```

### 3. Feedback Kategorileri
```python
FEEDBACK_CATEGORIES = {
    'beton_betonarme': 'Beton/Betonarme Ayrımı',
    'miktar_hesaplama': 'Miktar Hesaplama Hataları',
    'eksik_malzeme': 'Eksik Malzeme/İşçilik',
    'yanlis_poz': 'Yanlış Poz Kodu'
}
```

### 4. Machine Learning
Feedback'lerden pattern öğrenme:
```python
from sklearn.ensemble import RandomForestClassifier

model = train_from_feedbacks(all_feedbacks)
predicted_components = model.predict(description)
```

### 5. Feedback Dashboard
Web arayüzünde:
- Toplam feedback sayısı
- En çok düzeltilen hatalar
- AI iyileşme trendi (grafik)
- Kullanıcı katkı sıralaması

---

## 📚 İlgili Dosyalar

```
/home/aras/Masaüstü/UYGULAMALARIM/approximate_cost/
├── ui/
│   ├── feedback_dialog.py          ← YENİ (Dialog UI)
│   └── main_window.py               (Değişiklik yok)
├── analysis_builder.py              ← DEĞİŞTİ (Entegrasyon)
├── database.py                      (Mevcut metodlar kullanıldı)
├── FEEDBACK_SISTEMI_ENTEGRASYONU.md ← YENİ (Bu döküman)
├── BETON_BETONARME_DUZELTMESI.md   (İlgili)
└── IYILESTIRMELER_OZET.md          (Genel)
```

---

## 🎯 Başarı Kriterleri

- ✅ Kullanıcı AI sonucunu düzeltebilir
- ✅ Düzeltme dialog ile kaydedilebilir
- ✅ Feedback veritabanına kaydedilir
- ✅ Gelecek analizlerde feedback kullanılır
- ✅ AI sürekli öğrenir ve iyileşir
- ✅ Kullanıcı bilgileri anonim kalır
- ✅ Sistem token limitini aşmaz (max 3 feedback)

---

## 🐛 Bilinen Sorunlar

### Sorun 1: Feedback Butonu Aktif Olmuyor

**Sebep:**
- AI analizi henüz yapılmadı
- `original_ai_components` boş

**Çözüm:**
- Önce AI ile analiz yaptırın
- Sonra düzeltme yapın
- Buton otomatik aktif olur

---

### Sorun 2: "Değişiklik Yok" Uyarısı

**Sebep:**
- Tabloda değişiklik yapılmamış
- AI sonucu aynen kalmış

**Çözüm:**
- Önce tabloda malzeme ekle/çıkar/değiştir
- Sonra feedback kaydet

---

### Sorun 3: Feedback Kullanılmıyor

**Sebep:**
- Anahtar kelime eşleşmesi yok
- Benzerlik puanı düşük

**Çözüm:**
```python
# database.py:_extract_keywords_from_prompt() metodunu iyileştir
# Daha fazla keyword ekle
# Stemming/lemmatization kullan
```

---

## 📞 Destek

**Feedback sistemi ile ilgili sorularınız için:**

1. Bu dökümanı okuyun
2. Console log'larını kontrol edin
3. `database.py:get_relevant_feedback()` metodunu debug edin
4. `analysis_builder.py:get_feedback_context()` metodunu debug edin

---

**Son Güncelleme:** 2026-01-29
**Versiyon:** 1.0.0
**Durum:** ✅ Üretime Hazır

🎉 **Artık sistem her düzeltmeden öğreniyor ve sürekli gelişiyor!**
