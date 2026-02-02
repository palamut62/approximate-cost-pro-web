"""
Golden Dataset Creator - Interaktif Test Senaryosu Oluşturucu

Bu script, AI analiz sistemi için altın standart test senaryoları oluşturur.
Kullanıcıyla etkileşimli olarak doğru sonuçları belirler.
"""

import json
from pathlib import Path
from typing import List, Dict

class GoldenDatasetCreator:
    def __init__(self):
        self.scenarios = []
        self.dataset_path = Path(__file__).parent / "golden_dataset.json"
        
    def create_scenario(self):
        """Yeni bir test senaryosu oluştur"""
        print("\n" + "="*60)
        print("YENİ TEST SENARYOSU OLUŞTURMA")
        print("="*60)
        
        # Temel bilgiler
        scenario_id = input("\n📝 Senaryo ID (örn: simple_wall_001): ").strip()
        category = input("📂 Kategori (basit/orta/kompleks): ").strip()
        description = input("📋 Tanım (örn: 10 m² tuğla duvar örülmesi): ").strip()
        
        # Beklenen bileşenler
        print("\n🔧 BEKLENEN BİLEŞENLER:")
        print("(Bitirmek için boş bırakın)")
        
        expected_components = []
        component_num = 1
        
        while True:
            print(f"\n--- Bileşen #{component_num} ---")
            comp_type = input("Tip (Malzeme/İşçilik/Nakliye/Makine) [boş=bitir]: ").strip()
            if not comp_type:
                break
                
            comp_name = input("İsim (örn: Tuğla, Duvarcı): ").strip()
            comp_unit = input("Birim (adet/m³/m²/Sa): ").strip()
            
            # Miktar aralığı
            has_quantity = input("Miktar aralığı var mı? (e/h): ").strip().lower()
            if has_quantity == 'e':
                min_q = float(input("  Min miktar: "))
                max_q = float(input("  Max miktar: "))
                component = {
                    "type": comp_type,
                    "name": comp_name,
                    "unit": comp_unit,
                    "min_quantity": min_q,
                    "max_quantity": max_q
                }
            else:
                component = {
                    "type": comp_type,
                    "name": comp_name,
                    "unit": comp_unit,
                    "required": True
                }
            
            expected_components.append(component)
            component_num += 1
        
        # Validasyon kuralları
        print("\n✅ VALIDASYON KURALLARI:")
        must_have_mortar = input("Harç olmalı mı? (e/h): ").strip().lower() == 'e'
        must_have_labor = input("İşçilik olmalı mı? (e/h): ").strip().lower() == 'e'
        must_have_transport = input("Nakliye olmalı mı? (e/h): ").strip().lower() == 'e'
        
        print("\n💰 FİYAT ARALIĞI:")
        min_price = float(input("Minimum toplam fiyat (TL): "))
        max_price = float(input("Maximum toplam fiyat (TL): "))
        
        # Senaryo objesi
        scenario = {
            "id": scenario_id,
            "category": category,
            "description": description,
            "expected_components": expected_components,
            "validation_rules": {
                "must_have_mortar": must_have_mortar,
                "must_have_labor": must_have_labor,
                "must_have_transport": must_have_transport,
                "price_range": {
                    "min": min_price,
                    "max": max_price
                }
            }
        }
        
        self.scenarios.append(scenario)
        print(f"\n✅ Senaryo '{scenario_id}' eklendi!")
        
    def save_dataset(self):
        """Dataset'i JSON dosyasına kaydet"""
        dataset = {
            "version": "1.0",
            "created_at": "2025-02-02",
            "description": "AI Analiz Sistemi için Golden Test Dataset",
            "scenarios": self.scenarios
        }
        
        with open(self.dataset_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Dataset kaydedildi: {self.dataset_path}")
        print(f"📊 Toplam senaryo sayısı: {len(self.scenarios)}")
        
    def load_existing_dataset(self):
        """Mevcut dataset'i yükle"""
        if self.dataset_path.exists():
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.scenarios = data.get('scenarios', [])
            print(f"📂 Mevcut dataset yüklendi: {len(self.scenarios)} senaryo")
        else:
            print("ℹ️  Yeni dataset oluşturuluyor...")
    
    def run(self):
        """Ana program döngüsü"""
        print("\n" + "="*60)
        print("🧪 GOLDEN DATASET CREATOR")
        print("="*60)
        
        self.load_existing_dataset()
        
        while True:
            print("\n📋 MENÜ:")
            print("1. Yeni senaryo ekle")
            print("2. Mevcut senaryoları görüntüle")
            print("3. Kaydet ve çık")
            print("4. Çık (kaydetmeden)")
            
            choice = input("\nSeçim (1-4): ").strip()
            
            if choice == '1':
                self.create_scenario()
            elif choice == '2':
                print("\n📊 MEVCUT SENARYOLAR:")
                for i, scenario in enumerate(self.scenarios, 1):
                    print(f"{i}. {scenario['id']}: {scenario['description']}")
            elif choice == '3':
                self.save_dataset()
                print("\n👋 Çıkılıyor...")
                break
            elif choice == '4':
                print("\n👋 Çıkılıyor (kaydedilmedi)...")
                break
            else:
                print("❌ Geçersiz seçim!")

if __name__ == "__main__":
    creator = GoldenDatasetCreator()
    creator.run()
