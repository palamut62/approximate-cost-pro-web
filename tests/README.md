# Otomatik Test Sistemi (Golden Dataset)

Bu klasör, AI analiz sisteminin kalitesini sürekli denetlemek için otomatik test altyapısını içerir.

## 📁 Dosyalar

- **`golden_dataset.json`**: Doğruluğunu bildiğimiz test senaryoları
- **`test_runner.py`**: Test motor (API çağrıları, doğrulama, raporlama)
- **`create_golden_dataset.py`**: Interactive dataset oluşturma aracı

## 🚀 Kullanım

### 1. Testleri Çalıştır

```bash
# Tüm testleri çalıştır
python run_tests.py

# Sadece basit testleri çalıştır
python run_tests.py --category basit

# HTML rapor oluştur
python run_tests.py --report html --output test_report.html

# Farklı API URL'si kullan
python run_tests.py --api http://production-server:8000
```

### 2. Yeni Senaryo Ekle

```bash
# Interactive oluşturucu
python tests/create_golden_dataset.py

# Manuel olarak JSON'a ekle
# tests/golden_dataset.json dosyasını düzenle
```

## 📊 Test Formatı

Her test senaryosu şunları içerir:

- **ID**: Benzersiz tanımlayıcı (örn: `simple_wall_001`)
- **Kategori**: `basit`, `orta` veya `kompleks`
- **Tanım**: AI'ya gönderilecek metin
- **Beklenen Bileşenler**: Olması gereken malzeme/işçilik/nakliye
- **Validasyon Kuralları**: Harç/işçilik/nakliye zorunluluğu, fiyat aralığı

## 🎯 Başarı Kriterleri

Bir test şu durumlarda başarılı sayılır:

✅ Tüm beklenen bileşenler mevcut  
✅ Miktarlar belirtilen aralıkta  
✅ Validasyon kuralları geçiyor  
✅ Toplam fiyat beklenen aralıkta  

## 📈 Önerilen Kullanım

1. **Her kod değişikliğinden sonra testleri çalıştırın**
2. Başarı oranı düşerse, hangi testlerin başarısız olduğunu kontrol edin
3. Gerekirse kodu veya golden dataset'i düzeltin
4. Yeni özellikler eklediğinizde yeni test senaryoları da ekleyin

## 🧪 Mevcut Test Senaryoları

1. `simple_wall_001` - 10 m² tuğla duvar
2. `simple_concrete_001` - 5 m³ beton döküm
3. `medium_reinforced_001` - 20 m² betonarme döşeme
4. `simple_tile_001` - 30 m² seramik kaplama
5. `simple_excavation_001` - 50 m³ kazı

**Hedef:** 50+ senaryo ile %95+ başarı oranı
