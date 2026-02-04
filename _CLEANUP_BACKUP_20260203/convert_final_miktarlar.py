#!/usr/bin/env python3
"""
analiz_final_miktarlar.json dosyasını JSONL eğitim verisine dönüştürür.
Bu veri çok temiz ve miktarlar dahil!

Kullanım:
    python3 convert_final_miktarlar.py
"""

import json
from pathlib import Path
from typing import Dict, Any


def parse_quantity(qty_str: str) -> float:
    """Miktar stringini float'a çevir (Türkçe format: 0,022)"""
    if not qty_str:
        return 0.0
    try:
        return float(str(qty_str).strip().replace(',', '.'))
    except (ValueError, TypeError):
        return 0.0


def determine_component_type(code: str, name: str) -> str:
    """Bileşen tipini belirle"""
    name_lower = name.lower()

    # İşçilik kodları (10.100.xxxx)
    if code.startswith('10.100.'):
        return "iscilik"

    # Makine kodları (19.xxx, 03.xxx)
    if code.startswith('19.') or code.startswith('03.'):
        return "makine"

    # Nakliye kontrolü (kelime bazlı)
    if 'nakliye' in name_lower or 'taşıma' in name_lower or code.startswith('15.100.'):
        return "nakliye"

    # Diğerleri malzeme
    return "malzeme"


def convert_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Tek bir kaydı JSONL formatına dönüştür"""

    poz_no = entry.get('ana_poz_no', '')
    poz_adi = entry.get('ana_poz_adi', '')
    bilesenler = entry.get('bilesenler', [])

    if not poz_adi:
        return None

    # Bileşenleri kategorilere ayır
    malzemeler = []
    iscilikler = []
    nakliyeler = []
    makineler = []

    for bilesen in bilesenler:
        kod = bilesen.get('kod', '').strip()
        tanim = bilesen.get('tanim', '').strip()
        miktar = parse_quantity(bilesen.get('miktar', '0'))
        birim = bilesen.get('birim', '').strip().lower()

        # Birim düzeltme
        if birim in ['sa', 'saat']:
            birim = 'sa'
        elif birim in ['m³', 'm3', 'metreküp']:
            birim = 'm³'
        elif birim in ['m²', 'm2', 'metrekare']:
            birim = 'm²'

        if not kod:
            continue

        item = {
            "kod": kod,
            "ad": tanim,
            "birim": birim,
            "miktar": miktar
        }

        tip = determine_component_type(kod, tanim)

        if tip == "iscilik":
            iscilikler.append(item)
        elif tip == "makine":
            makineler.append(item)
        elif tip == "nakliye":
            nakliyeler.append(item)
        else:
            malzemeler.append(item)

    # En az bir bileşen olmalı
    if not (malzemeler or iscilikler or nakliyeler or makineler):
        return None

    return {
        "input": poz_adi,
        "output": {
            "malzeme": malzemeler,
            "iscilik": iscilikler,
            "nakliye": nakliyeler,
            "makine": makineler
        },
        "metadata": {
            "ana_poz_no": poz_no,
            "source": "analiz_final_miktarlar.json"
        }
    }


def main():
    print("=" * 80)
    print("ANALİZ FİNAL MİKTARLAR → JSONL DÖNÜŞTÜRÜCÜ")
    print("=" * 80)

    input_file = Path("analiz_final_miktarlar.json")
    output_file = Path("egitim_verisi_FROM_FINAL.jsonl")

    if not input_file.exists():
        print(f"\n❌ {input_file} bulunamadı!")
        return

    print(f"\n📁 Okuyuyor: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"📊 Toplam kayıt: {len(data)}")

    results = []

    for entry in data:
        converted = convert_entry(entry)
        if converted:
            results.append(converted)

    # Sonuçları yaz
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"\n✅ {len(results)} analiz dönüştürüldü!")
    print(f"📄 Çıktı: {output_file}")

    # İstatistikler
    total_malzeme = sum(len(r['output']['malzeme']) for r in results)
    total_iscilik = sum(len(r['output']['iscilik']) for r in results)
    total_nakliye = sum(len(r['output']['nakliye']) for r in results)
    total_makine = sum(len(r['output']['makine']) for r in results)

    # Miktar içeren bileşen sayısı
    has_miktar = 0
    for r in results:
        for tip in ['malzeme', 'iscilik', 'nakliye', 'makine']:
            for b in r['output'][tip]:
                if b.get('miktar', 0) > 0:
                    has_miktar += 1

    print(f"\n📊 İSTATİSTİKLER:")
    print(f"   Toplam analiz: {len(results)}")
    print(f"   Malzeme bileşeni: {total_malzeme}")
    print(f"   İşçilik bileşeni: {total_iscilik}")
    print(f"   Nakliye bileşeni: {total_nakliye}")
    print(f"   Makine bileşeni: {total_makine}")
    print(f"   Miktar içeren: {has_miktar} bileşen ✅")

    # Örnek göster
    print(f"\n📝 ÖRNEK ÇIKTI (İlk 3 analiz):")
    print("-" * 80)
    for item in results[:3]:
        print(json.dumps(item, ensure_ascii=False, indent=2))
        print("-" * 80)

    print(f"\n📌 SONRAKİ ADIMLAR:")
    print(f"1. {output_file} dosyasını kontrol edin")
    print(f"2. Mevcut eğitim verisine ekleyin:")
    print(f"   cat {output_file} >> egitim_verisi_FINAL_READY.jsonl")
    print(f"3. Backend'i yeniden başlatın")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
