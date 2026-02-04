#!/usr/bin/env python3
"""
analiz_verileri.json dosyasını JSONL eğitim verisine dönüştürür.
Miktarları da dahil eder!

Kullanım:
    python3 convert_analiz_json_to_jsonl.py
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


def parse_poz_code(code: str) -> str:
    """Poz kodunu temizle ve doğrula"""
    code = code.strip()
    # Geçerli poz kodu formatı: XX.XXX.XXXX veya XX.XXX
    if re.match(r'^\d{2}\.\d{3}(\.\d+)?$', code):
        return code
    return ""


def parse_quantity(qty_str: str) -> float:
    """Miktar stringini float'a çevir"""
    try:
        qty_str = qty_str.strip().replace(',', '.')
        return float(qty_str)
    except (ValueError, TypeError):
        return 0.0


def determine_component_type(code: str, name: str) -> str:
    """Bileşen tipini belirle (malzeme, işçilik, nakliye, makine)"""
    name_lower = name.lower()

    # İşçilik kodları (10.100.xxxx)
    if code.startswith('10.100.'):
        return "iscilik"

    # Makine kodları (19.xxx, 03.xxx)
    if code.startswith('19.') or code.startswith('03.'):
        return "makine"

    # Nakliye kodları (15.100.xxxx veya nakliye kelimesi)
    if code.startswith('15.100.') or 'nakliye' in name_lower or 'taşıma' in name_lower:
        return "nakliye"

    # Malzeme kodları (10.130.xxxx, 10.140.xxxx, 04.xxx, diğerleri)
    return "malzeme"


def process_analysis_group(ana_poz: Dict, bilesenler_row: Dict) -> Optional[Dict]:
    """
    Bir analiz grubunu işle ve JSONL formatına dönüştür.

    Args:
        ana_poz: Ana poz bilgisi (poz no, tanım)
        bilesenler_row: Bileşenler satırı (kodlar, isimler, miktarlar \n ile ayrılmış)
    """

    # Ana poz numarasını al
    poz_no = ana_poz.get('ana_poz_no', '').strip()
    if not parse_poz_code(poz_no):
        return None  # Geçerli poz numarası değil

    # Tanımı al
    tanim = ana_poz.get('tanim', '').strip()
    if not tanim:
        return None

    # Bileşenleri parse et
    bilesen_kodlari = bilesenler_row.get('ana_poz_no', '').split('\n')
    bilesen_isimleri = bilesenler_row.get('tanim', '').split('\n') if bilesenler_row.get('tanim') else []
    bilesen_miktarlari = bilesenler_row.get('birim', '').split('\n') if bilesenler_row.get('birim') else []

    # Bileşenleri grupla
    malzemeler = []
    iscilikler = []
    nakliyeler = []
    makineler = []

    for i, kod_raw in enumerate(bilesen_kodlari):
        kod = parse_poz_code(kod_raw)
        if not kod:
            continue

        # İsim ve miktar al
        isim = bilesen_isimleri[i].strip() if i < len(bilesen_isimleri) else ""
        miktar = parse_quantity(bilesen_miktarlari[i]) if i < len(bilesen_miktarlari) else 0.0

        # İsimden parantez içini temizle (açıklama kısmı)
        isim_temiz = re.sub(r'\s*\(.*?\)\s*', ' ', isim).strip()

        # Birim tahmini
        tip = determine_component_type(kod, isim)
        if tip == "iscilik":
            birim = "sa"
        elif tip == "makine":
            birim = "sa"
        elif tip == "nakliye":
            birim = "ton" if "ton" in isim.lower() else "m³"
        else:
            # Malzeme birimi tahmini
            if "m³" in isim or "metreküp" in isim.lower():
                birim = "m³"
            elif "m²" in isim or "metrekare" in isim.lower():
                birim = "m²"
            elif "ton" in isim.lower():
                birim = "ton"
            elif "kg" in isim.lower():
                birim = "kg"
            elif "adet" in isim.lower():
                birim = "adet"
            else:
                birim = "birim"

        bilesen = {
            "kod": kod,
            "ad": isim_temiz if isim_temiz else isim,
            "birim": birim,
            "miktar": miktar
        }

        if tip == "malzeme":
            malzemeler.append(bilesen)
        elif tip == "iscilik":
            iscilikler.append(bilesen)
        elif tip == "nakliye":
            nakliyeler.append(bilesen)
        elif tip == "makine":
            makineler.append(bilesen)

    # En az bir bileşen olmalı
    if not (malzemeler or iscilikler or nakliyeler or makineler):
        return None

    return {
        "input": tanim,
        "output": {
            "malzeme": malzemeler,
            "iscilik": iscilikler,
            "nakliye": nakliyeler,
            "makine": makineler
        },
        "metadata": {
            "ana_poz_no": poz_no,
            "source": "analiz_verileri.json"
        }
    }


def is_valid_poz_no(value: str) -> bool:
    """Değerin geçerli bir poz numarası olup olmadığını kontrol et"""
    if not value:
        return False
    # Çok uzun değilse ve poz formatına uyuyorsa
    if len(value) > 20:
        return False
    return bool(parse_poz_code(value.split('\n')[0]))


def main():
    print("=" * 80)
    print("ANALİZ VERİLERİ → JSONL DÖNÜŞTÜRÜCÜ")
    print("=" * 80)

    input_file = Path("analiz_verileri.json")
    output_file = Path("egitim_verisi_FROM_ANALIZ.jsonl")

    if not input_file.exists():
        print(f"\n❌ {input_file} bulunamadı!")
        return

    print(f"\n📁 Okuyuyor: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"📊 Toplam kayıt: {len(data)}")

    # Grupları oluştur
    results = []
    i = 0

    while i < len(data):
        row = data[i]
        poz_no = row.get('ana_poz_no', '')

        # Geçerli bir poz numarası mı?
        if is_valid_poz_no(poz_no) and not '\n' in poz_no:
            # Bu bir ana poz satırı
            ana_poz = row

            # Sonraki satır bileşenler olabilir
            if i + 1 < len(data):
                next_row = data[i + 1]
                next_poz = next_row.get('ana_poz_no', '')

                # Bileşenler satırı: \n içerir veya uzun açıklama değil
                if '\n' in next_poz or (is_valid_poz_no(next_poz) and next_row.get('birim')):
                    bilesenler_row = next_row

                    # İşle
                    result = process_analysis_group(ana_poz, bilesenler_row)
                    if result:
                        results.append(result)

                    i += 2  # Ana poz + bileşenler

                    # Açıklama satırını atla (varsa)
                    if i < len(data):
                        maybe_desc = data[i].get('ana_poz_no', '')
                        if len(maybe_desc) > 50:  # Uzun metin = açıklama
                            i += 1
                    continue

        i += 1

    # Sonuçları yaz
    if results:
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

        print(f"\n📊 İSTATİSTİKLER:")
        print(f"   Toplam analiz: {len(results)}")
        print(f"   Malzeme bileşeni: {total_malzeme}")
        print(f"   İşçilik bileşeni: {total_iscilik}")
        print(f"   Nakliye bileşeni: {total_nakliye}")
        print(f"   Makine bileşeni: {total_makine}")

        # Örnek göster
        print(f"\n📝 ÖRNEK ÇIKTI (İlk 2 analiz):")
        print("-" * 80)
        for item in results[:2]:
            print(json.dumps(item, ensure_ascii=False, indent=2))
            print("-" * 80)

        print(f"\n📌 SONRAKİ ADIMLAR:")
        print(f"1. {output_file} dosyasını kontrol edin")
        print(f"2. Mevcut eğitim verisine ekleyin:")
        print(f"   cat {output_file} >> egitim_verisi_FINAL_READY.jsonl")
        print(f"3. Backend'i yeniden başlatın")
    else:
        print("\n❌ Hiç analiz dönüştürülemedi!")
        print("Veri formatını kontrol edin.")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
