#!/usr/bin/env python3
"""
PDF analiz dosyalarını JSONL eğitim verisine dönüştürür.

Kullanım:
    python3 convert_pdf_to_jsonl.py

Gereksinimler:
    pip install PyPDF2
"""

import json
import re
from pathlib import Path

def parse_pdf_text_to_jsonl(text: str, filename: str) -> dict:
    """
    PDF metnini parse edip JSONL formatına dönüştürür.

    Bu fonksiyonu kendi PDF formatınıza göre özelleştirin!
    """

    # İmalat tanımını bul
    tanim_patterns = [
        r'İMALAT TANIMI:?\s*(.+?)(?:\n|$)',
        r'TANIM:?\s*(.+?)(?:\n|$)',
        r'POZ\s+TANIMI:?\s*(.+?)(?:\n|$)',
    ]

    tanim = ""
    for pattern in tanim_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            tanim = match.group(1).strip()
            break

    if not tanim:
        print(f"⚠️  {filename}: İmalat tanımı bulunamadı!")
        tanim = filename.replace('.pdf', '').replace('_', ' ')

    # Malzemeleri bul (10.xxx kodları)
    malzemeler = []
    malzeme_pattern = r'((?:10\.|04\.)\d+\.\d+)\s+(.+?)\s+(\d+[.,]\d+)\s+(ton|m³|m²|kg|adet|sa)'
    for match in re.finditer(malzeme_pattern, text):
        kod = match.group(1)
        ad = match.group(2).strip()
        miktar = float(match.group(3).replace(',', '.'))
        birim = match.group(4)

        malzemeler.append({
            "kod": kod,
            "ad": ad,
            "birim": birim,
            "miktar": miktar
        })

    # İşçilikleri bul (10.100.xxx kodları)
    iscilikler = []
    iscilik_pattern = r'(10\.100\.\d+)\s+(.+?)\s+(\d+[.,]\d+)\s+(sa|saat)'
    for match in re.finditer(iscilik_pattern, text):
        kod = match.group(1)
        ad = match.group(2).strip()
        miktar = float(match.group(3).replace(',', '.'))
        birim = "sa"

        iscilikler.append({
            "kod": kod,
            "ad": ad,
            "birim": birim,
            "miktar": miktar
        })

    # Nakliyeleri bul (15.xxx kodları)
    nakliyeler = []
    nakliye_pattern = r'(15\.\d+\.\d+)\s+(.+?)\s+(\d+[.,]\d+)\s+(ton|m³|kg)'
    for match in re.finditer(nakliye_pattern, text):
        kod = match.group(1)
        ad = match.group(2).strip()
        miktar = float(match.group(3).replace(',', '.'))
        birim = match.group(4)

        nakliyeler.append({
            "kod": kod,
            "ad": ad,
            "birim": birim,
            "miktar": miktar
        })

    # Makineleri bul (03.xxx kodları)
    makineler = []
    makine_pattern = r'(03\.\d+)\s+(.+?)\s+(\d+[.,]\d+)\s+(sa|saat)'
    for match in re.finditer(makine_pattern, text):
        kod = match.group(1)
        ad = match.group(2).strip()
        miktar = float(match.group(3).replace(',', '.'))
        birim = "sa"

        makineler.append({
            "kod": kod,
            "ad": ad,
            "birim": birim,
            "miktar": miktar
        })

    return {
        "input": tanim,
        "output": {
            "malzeme": malzemeler,
            "iscilik": iscilikler,
            "nakliye": nakliyeler,
            "makine": makineler
        }
    }


def convert_single_pdf(pdf_path: Path) -> dict:
    """Tek bir PDF'yi JSONL formatına dönüştür"""
    try:
        import PyPDF2

        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()

        if not text.strip():
            print(f"❌ {pdf_path.name}: PDF boş veya okunamadı!")
            return None

        return parse_pdf_text_to_jsonl(text, pdf_path.name)

    except Exception as e:
        print(f"❌ {pdf_path.name}: {e}")
        return None


def main():
    print("=" * 80)
    print("PDF → JSONL DÖNÜŞTÜRÜCÜ")
    print("=" * 80)

    # Klasör kontrolü
    pdf_dir = Path("ANALIZ")
    if not pdf_dir.exists():
        print(f"\n⚠️  '{pdf_dir}' klasörü bulunamadı!")
        print("Lütfen PDF'leri 'ANALIZ/' klasörüne koyun.\n")

        # Örnek klasör oluştur
        pdf_dir.mkdir(exist_ok=True)
        print(f"✅ '{pdf_dir}' klasörü oluşturuldu.")
        print("PDF'leri bu klasöre ekleyip tekrar çalıştırın.\n")
        return

    # PDF'leri bul
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"\n⚠️  '{pdf_dir}' klasöründe PDF bulunamadı!")
        print("PDF dosyalarını bu klasöre ekleyin.\n")
        return

    print(f"\n📁 {len(pdf_files)} PDF bulundu\n")

    # Output dosyası
    output_file = "egitim_verisi_NEW.jsonl"
    success_count = 0

    with open(output_file, "w", encoding="utf-8") as f:
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"[{i}/{len(pdf_files)}] İşleniyor: {pdf_file.name}...", end=" ")

            data = convert_single_pdf(pdf_file)

            if data and data['input']:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
                success_count += 1

                # Özet bilgi
                total_items = (len(data['output'].get('malzeme', [])) +
                              len(data['output'].get('iscilik', [])) +
                              len(data['output'].get('nakliye', [])) +
                              len(data['output'].get('makine', [])))

                print(f"✅ ({total_items} bileşen)")
            else:
                print("❌")

    print("\n" + "=" * 80)
    print("TAMAMLANDI!")
    print("=" * 80)
    print(f"✅ Başarılı: {success_count}/{len(pdf_files)}")
    print(f"📄 Çıktı dosyası: {output_file}")

    if success_count > 0:
        print(f"\n📌 SONRAKİ ADIMLAR:")
        print(f"1. {output_file} dosyasını kontrol edin")
        print(f"2. Manuel düzeltmeler yapın (gerekirse)")
        print(f"3. egitim_verisi_FINAL_READY.jsonl dosyasına ekleyin:")
        print(f"   cat {output_file} >> egitim_verisi_FINAL_READY.jsonl")
        print(f"4. Backend'i yeniden başlatın")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # PyPDF2 kontrolü
    try:
        import PyPDF2
    except ImportError:
        print("\n❌ PyPDF2 kütüphanesi bulunamadı!")
        print("Kurulum için:")
        print("  pip install PyPDF2\n")
        exit(1)

    main()
