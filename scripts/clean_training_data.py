import json
import os

def clean_training_record(record):
    """Eğitim kaydını temizle ve doğru kategorize et"""
    output = record.get('output', {})
    
    cleaned = {
        "iscilik": [],
        "makine": [],
        "malzeme": [],
        "nakliye": []
    }
    
    # Tüm kategorileri birleştir ve yeniden sınıflandır
    all_items = []
    for category in ['iscilik', 'makine', 'malzeme', 'nakliye']:
        # Kategori varsa ve liste ise ekle
        items = output.get(category, [])
        if isinstance(items, list):
            all_items.extend(items)
    
    for item in all_items:
        kod = item.get('kod', '')
        ad = item.get('ad', '').lower()
        
        # Kod bazlı sınıflandırma
        if kod.startswith('10.100'):  # İşçilik kodları
            cleaned['iscilik'].append(item)
        elif kod.startswith('19.') or 'ekskavatör' in ad or 'kompresör' in ad or 'vinç' in ad:
            cleaned['makine'].append(item)
        elif kod.startswith('15.100') or 'nakliye' in ad:
            cleaned['nakliye'].append(item)
        else:
            cleaned['malzeme'].append(item)
    
    record['output'] = cleaned
    return record

def main():
    input_file = 'egitim_verisi_FINAL_READY.jsonl'
    output_file = 'egitim_verisi_CLEANED.jsonl'
    
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        return

    print(f"🧹 Cleaning {input_file}...")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            records = [json.loads(line) for line in f]
        
        cleaned_records = [clean_training_record(r) for r in records]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for record in cleaned_records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                
        print(f"✅ Cleaned {len(cleaned_records)} records.")
        print(f"💾 Saved to {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
