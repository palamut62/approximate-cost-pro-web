# Poz Birim Fiyat Çıkarıcı Uygulaması

Çevre Şehircilik ve diğer kurumlara ait birim fiyat PDF dosyalarından pozları ve birim fiyatlarını otomatik olarak çıkartarak CSV dosyasına kaydeden uygulama.

## Özellikler

- 📄 **Otomatik PDF Yükleme**: `PDF/` klasöründeki tüm PDF dosyalarını otomatik algıla
- 🏢 **Kurum Kategorileştirme**: PDF dosya adından otomatik olarak kurum adını belirle
- 📊 **Poz Çıkarma**: Koordinat tabanlı analiz ile tüm pozları ve birim fiyatlarını çıkart
- 📥 **Toplu İşlem**: Birden fazla PDF'i sırası ile işleyip tek CSV dosyasına yazma
- 🖥️ **Çift Arayüz**: PyQt5 GUI ve Komut Satırı (CLI) versiyonu
- 📋 **Türkçe Destek**: Türk sayı formatı (1.000,50) ve Türkçe başlıklar

## Kurulum

### Gereksinimler
```bash
pip install -r requirements.txt
```

### Bağımlılıklar
- PyMuPDF (fitz) - PDF işleme
- PyQt5 - Masaüstü arayüzü
- pandas - Veri işleme
- openpyxl - Excel desteği

## Kullanım

### 1. GUI Versiyonu (PyQt5)

```bash
python poz_extractor_app.py
```

**Özellikler:**
- Uygulama açıldığında PDF/ klasöründeki dosyalar otomatik yüklenir
- "Poz Çıkart" butonuyla işlemi başlat
- Sonuçları tabloda görüntüle
- "CSV'ye Kaydet" butonuyla CSV dosyası oluştur

### 2. Komut Satırı Versiyonu (CLI)

#### PDF Dizini İşle
```bash
python poz_extractor_cli.py PDF -o pozlar.csv
```

#### Tek PDF Dosyası İşle
```bash
python poz_extractor_cli.py "path/to/file.pdf" -o output.csv
```

#### JSON Formatında da Kaydet
```bash
python poz_extractor_cli.py PDF -o pozlar.csv -j pozlar.json
```

#### Örnek Sonuçları Göster
```bash
python poz_extractor_cli.py PDF -o pozlar.csv -s 10
```

## CSV Çıktı Formatı

| Sütun | Açıklama | Örnek |
|-------|----------|-------|
| Kurum | PDF dosya adından otomatik çıkartılır | Birim Fiyatlar |
| Poz No | Poz numarası | 10.100.1001 |
| Açıklama | Pozın açıklaması | Taşcı ustası |
| Birim | Ölçü birimi | Sa, m², kg vb. |
| Miktar | Miktar (varsa) | 100, 5,5 vb. |
| Birim Fiyatı (TL) | Birim fiyat | 250,00 |
| Sayfa | PDF sayfası | 8 |

## Örnek Çıktı

```csv
Kurum,Poz No,Açıklama,Birim,Miktar,Birim Fiyatı (TL),Sayfa
Birim Fiyatlar,10.100.1001,Taşcı ustası,Sa,,250,00,8
Birim Fiyatlar,10.100.1002,Karo kaplama ustası,Sa,,250,00,8
Birim Fiyatlar,10.100.1003,Fayans kaplama ustası,Sa,,250,00,8
```

## Desteklenen Poz Formatları

- `AA.BBB.CCCC` - Ön ek + alt grup + sıra (10.100.1001)
- `AA.BBB` - Ön ek + alt grup (10.100)
- `A.BBB.CCC` - Başlık + kategori + sıra (1.001.001)

## Desteklenen Birim Türleri

- Uzunluk: `m`, `cm`, `mm`
- Alan: `m²`
- Hacim: `m³`
- Ağırlık: `kg`, `ton`, `gr`
- Diğer: `adet`, `lt`, `da` (dekara), `Sa` (saat)

## Hata Ayıklama

### PDF dosyası bulunamıyor
- Dosyaların `PDF/` klasöründe olduğundan emin olun
- Dosya adında özel karakterler kullanmayın

### Pozlar çıkarılamıyor
- PDF yapısını kontrol etmek için çalıştırın: `python table_analyzer.py`
- PDF'nin tablo formatında olduğundan emin olun

### CSV Kodlama Hatası
- Dosya UTF-8 BOM ile kodlandı, Excel veya LibreOffice Calc'da açılabilir

## Sınırlamalar

- PDF dosyalarının tablo içermesi gerekir
- Koordinat bazlı analiz kullanılır, taranmış (scan) PDF'lerde çalışmayabilir
- Pozların belirli formatlar içermesi gerekir

## Geliştirilmesi Planlanan Özellikler

- [ ] OCR desteği (taranmış PDF'ler için)
- [ ] Excel çıktısı
- [ ] Batch işlem scheduler
- [ ] Web arayüzü
- [ ] Pozlara göre kategorilendirme
- [ ] Fiyat karşılaştırması ve analiz

## Teknik Detaylar

### Poz Çıkarma Algoritması

1. **Koordinat Tabanlı Analiz**
   - PDF'deki her karakterin X, Y koordinatını al
   - Y eksenine göre satırları grup
   - X eksenine göre sütunları sırala

2. **Pattern Matching**
   - Regex ile poz numarası ara: `\d{2}\.\d{3}\.\d{4}`
   - Birim türlerini tanı: `m²`, `kg`, `adet` vb.
   - Fiyatları ayıkla: Türk sayı formatı (1.000,50)

3. **Kurum Belirleme**
   - PDF dosya adını temizle (alt çizgi/tire kaldır)
   - Sayıları kaldır
   - İlk kelimeyi kurum adı olarak kullan

### Thread İşleme
- CLI ve GUI versiyonları ayrı thread'lerde çalışır
- Uzun işlemler UI'ı dondurmaz

## Lisans

Bu proje açık kaynaklıdır.

## İletişim

Sorular ve öneriler için lütfen iletişime geçin.
