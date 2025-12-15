from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLineEdit, QGroupBox, QTextEdit,
                             QMessageBox, QInputDialog, QProgressBar, QFormLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from database import DatabaseManager
import json
import requests
import re

class AIAnalysisThread(QThread):
    finished = pyqtSignal(list, str, str) # components, explanation, error
    
    def __init__(self, description, unit, api_key, model, base_url, context_data=""):
        super().__init__()
        self.description = description
        self.unit = unit
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.context_data = context_data
        
    def run(self):
        """
        Call OpenRouter API to generate analysis
        """
        try:
            if not self.api_key:
                raise Exception("API Anahtarı eksik! Ayarlar'dan ekleyiniz.")

            # PROMPT ENGINEERING FOR TURKISH COMPLIANCE
            prompt = f"""
            Sen uzman bir Türk İnşaat Metraj ve Hakediş Mühendisisin.
            
            Görev: Aşağıdaki poz tanımı için "Çevre ve Şehircilik Bakanlığı" birim fiyat analiz formatına uygun detaylı bir analiz oluştur.
            
            Poz Tanımı: {self.description}
            Poz Birimi: {self.unit}
            
            EK BAĞLAM (MEVCUT KAYNAKLARDAN BULUNAN İLGİLİ POZLAR):
            {self.context_data}
            
            Kurallar:
            1. Analiz şu bileşenleri içermelidir:
               - Malzeme (Örn: Çimento, Kum, Tuğla, vb.)
               - İşçilik (Örn: Usta, Düz işçi)
               - Makine (varsa)
            4. Miktarlar gerçekçi inşaat normlarına (analiz kitaplarına) dayanmalıdır.
            5. Birim fiyatlar 2024-2025 yılı ortalama piyasa rayiçleri (TL) olmalıdır.
            6. Çıktı SADECE geçerli bir JSON formatında olmalı.
            7. Lütfen JSON içindeki metin alanlarında çift tırnak (") kullanmaktan kaçının veya escape edin (\").
            
            JSON Formatı Şablonu:
            {{
              "explanation": "Bu analizi oluştururken ... mantığını kullandım. Şu pozları referans aldım: ...",
              "components": [
                  {{ "type": "Malzeme", "code": "10.xxx", "name": "Malzeme Adı", "unit": "kg/m/adet", "quantity": 0.0, "unit_price": 0.0 }},
                  {{ "type": "İşçilik", "code": "01.xxx", "name": "İşçilik Adı", "unit": "sa", "quantity": 0.0, "unit_price": 0.0 }}
              ]
            }}
            
            Lütfen "explanation" kısmında neden bu malzemeleri ve miktarları seçtiğini, hangi yöntemle hesapladığını detaylıca anlat.
            """

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://yaklasikmaliyetpro.com", # Required by OpenRouter
                "X-Title": "Yaklasik Maliyet Pro"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a helpful construction estimation assistant. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2, # Low temperature for more deterministic/factual output
                "max_tokens": 2000
            }
            
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"API Hatası: {response.text}")
                
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Clean Markdown if exists
            content = self.clean_json_string(content)
            
            data = json.loads(content)
            
            # Handle both old (list) and new (dict) formats for robustness
            if isinstance(data, list):
                components = data
                explanation = "Açıklama mevcut değil."
            else:
                components = data.get('components', [])
                explanation = data.get('explanation', "Açıklama yapılmadı.")
            
            # Calculate totals for verify
            for comp in components:
                comp['total_price'] = float(comp['quantity']) * float(comp['unit_price'])
                
            self.finished.emit(components, explanation, "")
            
        except Exception as e:
            self.finished.emit([], "", str(e))

    def clean_json_string(self, s):
        """Remove markdown code blocks from string and try to extract JSON"""
        s = s.strip()
        
        # Markdown clean
        if s.startswith("```json"):
            s = s[7:]
        if s.startswith("```"):
            s = s[3:]
        if s.endswith("```"):
            s = s[:-3]
            
        # Regex extraction as fallback if full string isn't valid JSON
        try:
            # En dıştaki { } bloğunu bulmayı dene
            match = re.search(r'\{.*\}', s.strip(), re.DOTALL)
            if match:
                return match.group(0)
        except:
            pass
            
        return s.strip()

class AnalysisBuilder(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.parent_app = None # Reference to main app
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # --- Header Inputs ---
        input_group = QGroupBox("Yeni Poz Tanımı (Çevre ve Şehircilik Bakanlığı Formatı)")
        input_layout = QFormLayout()
        
        self.poz_no_input = QLineEdit()
        self.poz_no_input.setPlaceholderText("Örn: ÖZEL.001")
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Örn: 20 cm Gazbeton Duvar Örülmesi")
        self.unit_input = QLineEdit("m²")
        
        input_layout.addRow("Özel Poz No:", self.poz_no_input)
        input_layout.addRow("Tanım:", self.desc_input)
        input_layout.addRow("Birim:", self.unit_input)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # --- AI Button ---
        ai_layout = QHBoxLayout()
        
        info_lbl = QLabel("Mode: OpenRouter AI")
        info_lbl.setStyleSheet("color: gray;")
        ai_layout.addWidget(info_lbl)
        
        self.generate_btn = QPushButton("🤖 Yapay Zeka ile Analiz Oluştur")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #673AB7; 
                color: white; 
                font-weight: bold; 
                padding: 10px;
                font-size: 11pt;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #5E35B1; }
        """)
        self.generate_btn.clicked.connect(self.start_ai_generation)
        ai_layout.addWidget(self.generate_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0) # Indeterminate
        ai_layout.addWidget(self.progress_bar)
        
        layout.addLayout(ai_layout)
        
        # --- Components Table ---
        self.comp_table = QTableWidget()
        self.comp_table.setColumnCount(6)
        self.comp_table.setHorizontalHeaderLabels([
            'Tür', 'Rayiç No', 'Ad', 'Birim', 'Miktar', 'Birim Fiyat'
        ])
        self.comp_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.comp_table)
        
        # --- Actions ---
        btn_layout = QHBoxLayout()
        add_row_btn = QPushButton("+ Satır Ekle")
        add_row_btn.clicked.connect(self.add_empty_row)
        btn_layout.addWidget(add_row_btn)
        
        del_row_btn = QPushButton("- Satır Sil")
        del_row_btn.clicked.connect(self.remove_row)
        btn_layout.addWidget(del_row_btn)
        layout.addLayout(btn_layout)
        
        # --- Results ---
        res_group = QGroupBox("Hesaplama Sonuçları")
        res_layout = QVBoxLayout()
        
        self.base_total_label = QLabel("Analiz Toplamı (Malzeme+İşçilik): 0.00 TL")
        self.overhead_label = QLabel("Yüklenici Kârı + Genel Giderler (%25): 0.00 TL")
        self.final_total_label = QLabel("Birim Fiyat (Kârlı): 0.00 TL")
        self.final_total_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #2E7D32;")
        
        res_layout.addWidget(self.base_total_label)
        res_layout.addWidget(self.overhead_label)
        res_layout.addWidget(self.final_total_label)
        res_group.setLayout(res_layout)
        layout.addWidget(res_group)
        
        # --- Save ---
        save_btn = QPushButton("💾 Analizi Veritabanına Kaydet")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 12px; font-weight: bold;")
        save_btn.clicked.connect(self.save_analysis)
        save_btn.clicked.connect(self.save_analysis)
        layout.addWidget(save_btn)
        
        save_add_btn = QPushButton("💾 + 💰 Kaydet ve Projeye Ekle")
        save_add_btn.setStyleSheet("background-color: #f57f17; color: white; padding: 12px; font-weight: bold;")
        save_add_btn.clicked.connect(self.save_and_add_to_project)
        layout.addWidget(save_add_btn)
        
        self.setLayout(layout)
        
        # Connect item change to recalc
        self.comp_table.itemChanged.connect(self.on_item_changed)

    def start_ai_generation(self):
        # 1. Ask user for the request via Dialog
        text, ok = QInputDialog.getMultiLineText(
            self, 
            "Yapay Zeka Analiz Asistanı", 
            "Analiz talebinizi detaylıca yazın (Örn: 'C25 beton dökülmesi, nakliye ve kalıp dahil'):"
        )
        
        if not ok or not text.strip():
            return
            
        desc = text.strip()
        self.desc_input.setText(desc) # Update UI
        
        unit = self.unit_input.text()
            
        # Get Settings
        api_key = self.db.get_setting("openrouter_api_key") 
        if not api_key:
             QMessageBox.warning(self, "Uyarı", "OpenRouter API Anahtarı bulunamadı! Lütfen Ayarlar menüsünden ekleyin.")
             return
             
        model = self.db.get_setting("openrouter_model") or "google/gemini-2.0-flash-exp:free"
        base_url = self.db.get_setting("openrouter_base_url") or "https://openrouter.ai/api/v1"
        
        self.set_loading(True)
        
        # RAG Implementation: Extract keywords and search context
        context_text = self.extract_and_format_context(desc)
        
        self.thread = AIAnalysisThread(desc, unit, api_key, model, base_url, context_text)
        self.thread.finished.connect(self.on_ai_finished)
        self.thread.start()

    def extract_and_format_context(self, description):
        """Extract keywords from description and search in loaded PDFs"""
        if not self.parent_app or not hasattr(self.parent_app, 'search_engine'):
            return ""

        # Simple keyword extraction (remove stop words if needed, but here we just take words > 3 chars)
        keywords = [w.strip() for w in description.split() if len(w.strip()) > 3]
        
        found_items = []
        search_engine = self.parent_app.search_engine
        
        # Limit total context to avoid token issues
        max_items = 20
        
        for keyword in keywords:
            if len(found_items) >= max_items:
                break
                
            # Use existing simple search logic from search engine manually or implement custom loop
            # Here we iterate loaded PDFs
            for file_name, lines in search_engine.pdf_data.items():
                for line_data in lines:
                    text = line_data['text']
                    if keyword.lower() in text.lower():
                        # Try to parse if it looks like a poz line
                        # Format: Code | Desc | Unit | Price (Approx)
                        if '|' in text:
                            found_items.append(text.strip())
                            if len(found_items) >= max_items:
                                break
                if len(found_items) >= max_items:
                    break
        
        if not found_items:
            return "İlgili poz bulunamadı."
            
        return "\n".join(found_items)
        
    def set_loading(self, loading):
        self.generate_btn.setEnabled(not loading)
        self.progress_bar.setVisible(loading)
        
    def on_ai_finished(self, components, explanation, error):
        self.set_loading(False)
        if error:
            QMessageBox.critical(self, "Hata", f"AI Hatası: {error}")
            return
            
        # Populate table
        self.comp_table.blockSignals(True)
        self.comp_table.setRowCount(0)
        
        for row, comp in enumerate(components):
            self.comp_table.insertRow(row)
            self.comp_table.setItem(row, 0, QTableWidgetItem(comp.get('type', 'Malzeme')))
            self.comp_table.setItem(row, 1, QTableWidgetItem(comp.get('code', '')))
            self.comp_table.setItem(row, 2, QTableWidgetItem(comp.get('name', '')))
            self.comp_table.setItem(row, 3, QTableWidgetItem(comp.get('unit', '')))
            self.comp_table.setItem(row, 4, QTableWidgetItem(str(comp.get('quantity', 0))))
            self.comp_table.setItem(row, 5, QTableWidgetItem(str(comp.get('unit_price', 0))))
            
        self.comp_table.blockSignals(False)
        self.recalc_totals()
        
        # Show Rationale Report
        QMessageBox.information(
            self, 
            "Yapay Zeka Analiz Raporu", 
            f"✅ Analiz Oluşturuldu!\n\n🔍 **AI Açıklaması:**\n{explanation}\n\nLütfen tabloyu kontrol edip kaydedin."
        )

    def add_empty_row(self):
        row = self.comp_table.rowCount()
        self.comp_table.insertRow(row)
        self.comp_table.setItem(row, 0, QTableWidgetItem("Malzeme"))
        self.comp_table.setItem(row, 4, QTableWidgetItem("0"))
        self.comp_table.setItem(row, 5, QTableWidgetItem("0"))

    def remove_row(self):
        self.comp_table.removeRow(self.comp_table.currentRow())
        self.recalc_totals()

    def on_item_changed(self, item):
        self.recalc_totals()

    def recalc_totals(self):
        total = 0.0
        for i in range(self.comp_table.rowCount()):
            try:
                qty_item = self.comp_table.item(i, 4)
                price_item = self.comp_table.item(i, 5)
                
                if qty_item and price_item:
                    qty = float(qty_item.text())
                    price = float(price_item.text())
                    total += qty * price
            except:
                pass
                
        # Compliance: 25% Overhead & Profit
        overhead = total * 0.25
        final_total = total + overhead
        
        self.base_total_label.setText(f"Analiz Toplamı (Malzeme+İşçilik): {total:,.2f} TL")
        self.overhead_label.setText(f"Yüklenici Kârı + Genel Giderler (%25): {overhead:,.2f} TL")
        self.final_total_label.setText(f"Birim Fiyat (Kârlı): {final_total:,.2f} TL")

    def save_analysis(self):
        poz_no = self.poz_no_input.text()
        if not poz_no:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir Poz No girin.")
            return
            
        components = []
        for i in range(self.comp_table.rowCount()):
            try:
                comp = {
                    'type': self.comp_table.item(i, 0).text(),
                    'code': self.comp_table.item(i, 1).text(),
                    'name': self.comp_table.item(i, 2).text(),
                    'unit': self.comp_table.item(i, 3).text(),
                    'quantity': float(self.comp_table.item(i, 4).text()),
                    'unit_price': float(self.comp_table.item(i, 5).text())
                }
                comp['total_price'] = comp['quantity'] * comp['unit_price']
                components.append(comp)
            except:
                continue
                
        if self.db.save_analysis(poz_no, self.desc_input.text(), self.unit_input.text(), components, is_ai=True):
            QMessageBox.information(self, "Kayıt", "Analiz başarıyla kaydedildi!")
            return True
        else:
            QMessageBox.critical(self, "Hata", "Kayıt sırasında hata oluştu. Poz No benzersiz olmalıdır.")
            return False

    def save_and_add_to_project(self):
        """Save analysis and add to active project cost"""
        if self.save_analysis():
            # Get Price from label
            txt = self.final_total_label.text()
            price = 0.0
            try:
                # "Birim Fiyat (Kârlı): 1.234,56 TL"
                val_str = txt.split(':')[1].replace(' TL', '').strip()
                price = float(val_str.replace('.', '').replace(',', '.'))
            except:
                pass
                
            if self.parent_app and self.parent_app.cost_tab:
                success = self.parent_app.cost_tab.add_item_from_external(
                    self.poz_no_input.text(),
                    self.desc_input.text(),
                    self.unit_input.text(),
                    price
                )
                if success:
                    QMessageBox.information(self, "Başarılı", "Poz projeye eklendi!")
