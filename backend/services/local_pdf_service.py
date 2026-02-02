
import fitz
import json
from pathlib import Path
import re

class LocalPDFService:
    """
    Yerel 'ANALIZ' klasöründeki PDF dosyalarından poz teknik tariflerini çeker.
    """
    def __init__(self, analiz_dir="/home/aras/Masaüstü/UYGULAMALARIM/approximate_cost/ANALIZ"):
        self.analiz_dir = Path(analiz_dir)
        # Cache dosyası backend/PDF/local_pdf_index.json
        self.index_file = Path(__file__).parent.parent / "PDF" / "local_pdf_index.json"
        
        self.index = {}
        self._load_index()

    def _load_index(self):
        """Kaydedilmiş indeksi yükle ve eski dosya referanslarını temizle"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    raw_index = json.load(f)

                # Sadece küçük harfli analiz_*.pdf dosyalarını tut
                cleaned = False
                for poz_no, entry in list(raw_index.items()):
                    file_path = entry.get('file', '')
                    file_name = Path(file_path).name
                    # Büyük harfli Analiz-*.pdf dosyalarını filtrele
                    if file_name.startswith('Analiz-'):
                        del raw_index[poz_no]
                        cleaned = True

                self.index = raw_index

                if cleaned:
                    self._save_index()
                    print("[LOCAL PDF] Eski indeks referansları temizlendi")

            except Exception as e:
                print(f"[LOCAL PDF] Index load error: {e}")
        
    def _save_index(self):
        """İndeksi kaydet"""
        try:
            self.index_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[LOCAL PDF] Index save error: {e}")

    def get_description(self, poz_no: str, return_structured=False) -> str:
        """
        Poz numarasının tarifini PDF'lerden bulur.
        Eğer indekste yoksa, PDF'leri tarar ve indeksler.
        """
        poz_no = poz_no.strip()
        
        # 1. İndekste var mı?
        if poz_no in self.index:
            entry = self.index[poz_no]
            if entry is None: # Daha önce arandı ve bulunamadı (Cache miss)
                return "" if not return_structured else {}
            return self._extract_text_from_pdf(entry['file'], entry['page'], poz_no, return_structured)
            
        print(f"[LOCAL PDF] {poz_no} aranıyor (Tüm dosyalar taranacak)...")
        
        # 2. Yoksa tüm dosyaları tara (Lazy Scanning)
        found_entry = self._scan_pdfs_for_poz(poz_no)
        
        # Her durumda (bulunsa da bulunmasa da) indekse ekle
        self.index[poz_no] = found_entry
        self._save_index()
        
        if found_entry:
            return self._extract_text_from_pdf(found_entry['file'], found_entry['page'], poz_no, return_structured)
            
        return "" if not return_structured else {}

    def _scan_pdfs_for_poz(self, poz_no: str):
        """PDF dosyalarında pozu arar (sadece küçük harfli analiz_*.pdf dosyaları)"""
        if not self.analiz_dir.exists():
            print(f"[LOCAL PDF] Klasör bulunamadı: {self.analiz_dir}")
            return None

        # Sadece küçük harfle başlayan analiz_*.pdf dosyalarını tara
        pdf_files = [f for f in self.analiz_dir.glob("analiz_*.pdf") if f.name[0].islower()]
        print(f"[LOCAL PDF] Taranacak dosyalar: {[f.name for f in pdf_files]}")

        for pdf_file in pdf_files:
            try:
                doc = fitz.open(pdf_file)
                for page_num in range(len(doc)):
                    text = doc[page_num].get_text()
                    
                    # HIZ VE DOĞRULUK İÇİN:
                    # "Poz No" etiketini ve aranan numarayı bul.
                    # Eğer "Poz No" ile "15.150.1005" arasında çok az karakter varsa (örn < 50), bu DOĞRU sayfadır.
                    # Aksi takdirde, metnin bir yerinde referans olarak geçiyordur.
                    
                    # İlk 1000 karakterde (Header) ara
                    header_text = text[:1000]
                    
                    # Regex: Poz No (opsiyonel noktalama) (bosluklar) ARANAN_POZ
                    # DOTALL yok, başlık genelde tek satır veya yan yana olur.
                    # fitz bazen "\n" ekler.
                    
                    pattern = rf'Poz\s*No.*?{re.escape(poz_no)}'
                    match = re.search(pattern, header_text, re.IGNORECASE | re.DOTALL)
                    
                    if match:
                        # Eşleşme uzunluğu kontrolü (Arada çok fazla metin olmamalı)
                        # "Poz No ............. 15.150.1005" -> OK
                        # "Poz No: 15.140... (sayfa sonu)... Referans: 15.150.1005" -> İPTAL
                        if len(match.group(0)) < 100:  # Arada max 100 karakter olsun (Tablo çizgileri vs dahil)
                            doc.close()
                            return {
                                'file': str(pdf_file),
                                'page': page_num
                            }
                        
                doc.close()
            except Exception as e:
                print(f"[LOCAL PDF] Error scanning {pdf_file.name}: {e}")
                
        return None

    def _extract_text_from_pdf(self, file_path, page_num, poz_no, return_structured=False):
        """Belirtilen sayfanın metnini çeker ve Yapısal Analiz veya Tarifi kısmını ayıklatır"""
        try:
            # Dosya varlık kontrolü
            if not Path(file_path).exists():
                print(f"[LOCAL PDF] Dosya bulunamadı: {file_path}")
                # İndeksten sil
                if poz_no in self.index:
                    del self.index[poz_no]
                    self._save_index()
                return "" if not return_structured else {}

            doc = fitz.open(file_path)
            page = doc[page_num]
            text = page.get_text()
            doc.close()

            # 1. YAPISAL ANALİZ ÇIKARMA (Eğer tablolu bir sayfa ise)
            if "Genel Fiyat Analizi" in text or "Tanımı" in text:
                analysis_data = self._parse_analysis_text(text, poz_no)
                if return_structured:
                    return analysis_data
                
                # Eğer sadece string isteniyorsa, yapısal veriyi güzel bir formata sokup döndürelim
                # (Eski frontend'leri bozmamak için)
                if not return_structured:
                    return self._format_analysis_as_string(analysis_data)

            # 2. NORMAL TARİF ÇIKARMA (Eski mantık)
            price_marker = re.search(r'(1\s*m[³3]\s*Fiyatı|Birim\s*Fiyatı|genel\s*giderler)', text, re.IGNORECASE)
            description = ""
            
            if price_marker:
                start_index = price_marker.end()
                remaining_text = text[start_index:]
                end_match = re.search(r'(Ölçü:|Not:|Poz\s*No)', remaining_text, re.IGNORECASE)
                description = remaining_text[:end_match.start()] if end_match else remaining_text
            else:
                match = re.search(r'(Tarifi|Yapım Şartları|Kapsamı)[:\s]+(.*?)(?=(Analizi|Not|Ölçü|Birim Fiyatı)|$)', text, re.IGNORECASE | re.DOTALL)
                description = match.group(2) if match else text
            
            return description.strip()[:4000]
            
        except Exception as e:
            print(f"[LOCAL PDF] Extract error: {e}")
            return "" if not return_structured else {}

    def _parse_analysis_text(self, text, poz_no):
        """ÇŞB PDF metnini yapısal analize dönüştürür"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        data = {
            "poz_no": poz_no,
            "name": "",
            "unit": "",
            "components": [],
            "totals": {},
            "full_text": text
        }
        
        # Temel Bilgiler
        try:
            # Analiz Adı: "Analizin Adı" satırından sonra gelen metin
            if "Analizin Adı" in lines:
                idx = lines.index("Analizin Adı")
                # Analiz adı genelde "Analizin Adı"dan sonra, "Tanımı"dan öncedir
                name_parts = []
                for i in range(idx + 1, len(lines)):
                    if lines[i] in ["Tanımı", "Ölçü Birimi", "Miktarı"]: break
                    name_parts.append(lines[i])
                data["name"] = " ".join(name_parts)

            # Ölçü Birimi
            unit_matches = re.findall(r'Ölçü Birimi\s*\n\s*([^\n]+)', text)
            if unit_matches:
                data["unit"] = unit_matches[-1].strip()
        except: pass

        # Bileşenler (Malzeme, İşçilik vb.)
        current_type = "Bileşen"
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if line.endswith(":") and line[:-1] in ["Malzeme", "İşçilik", "Makine", "Nakliye"]:
                current_type = line[:-1]
                i += 1
                continue
            
            # Satır bir poz numarası gibi mi başlıyor? (örn: 10.130.1505)
            if re.match(r'^\d{2}\.\d{3}\.\d{4}', line):
                try:
                    # Poz formatındaki satırı bulduk, sonraki lines'ları oku
                    comp = {
                        "type": current_type,
                        "code": line,
                        "name": lines[i+1],
                        "unit": lines[i+2],
                        "quantity": lines[i+3],
                        "price": lines[i+4],
                        "total": lines[i+5]
                    }
                    data["components"].append(comp)
                    i += 6
                    continue
                except: pass
            
            # Totaller
            if "Malzeme + İşçilik Tutarı" in line:
                try: data["totals"]["subtotal"] = lines[i+1]
                except: pass
            elif "kârı ve genel giderler" in line:
                try: data["totals"]["profit"] = lines[i+1]
                except: pass
            elif "Fiyatı" in line and (i+1 < len(lines)) and re.match(r'^[\d\.,]+$', lines[i+1]):
                try: 
                    data["totals"]["grand_total"] = lines[i+1]
                    data["totals"]["label"] = line
                except: pass
                
            i += 1
            
        return data

    def _format_analysis_as_string(self, data):
        """Yapısal veriden okunabilir String oluşturur (Eski gösterimler için)"""
        if not data.get("components"): return data.get("full_text", "")[:4000]
        
        sb = []
        sb.append(f"ANALİZ: {data['name']}\n")
        sb.append("-" * 40)
        sb.append(f"{'POZ NO':<12} {'TANIMI':<30} {'BİRİM':<6} {'MİKTAR':<8} {'TUTAR':<10}")
        for c in data["components"]:
            sb.append(f"{c['code']:<12} {c['name'][:30]:<30} {c['unit']:<6} {c['quantity']:<8} {c['total']:<10}")
        
        sb.append("-" * 40)
        if data["totals"].get("subtotal"): sb.append(f"Toplam: {data['totals']['subtotal']}")
        if data["totals"].get("grand_total"): sb.append(f"GENEL TOPLAM ({data.get('unit')}): {data['totals']['grand_total']}")
        
        return "\n".join(sb)

# Singleton
_local_pdf_service = None

def get_local_pdf_service(force_new=False):
    global _local_pdf_service
    if _local_pdf_service is None or force_new:
        _local_pdf_service = LocalPDFService()
    return _local_pdf_service

def reset_local_pdf_service():
    """Singleton'ı sıfırla (cache temizlendikten sonra çağrılmalı)"""
    global _local_pdf_service
    _local_pdf_service = None
    print("[LOCAL PDF] Service reset edildi")
