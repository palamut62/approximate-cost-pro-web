
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLineEdit, QGroupBox, QFormLayout,
                             QDoubleSpinBox, QMessageBox, QComboBox, QInputDialog, QDialog,
                             QDialogButtonBox, QPlainTextEdit, QMenu, QSplitter, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from database import DatabaseManager
import json
import requests
import re

class AIPromptDialog(QDialog):
    def __init__(self, parent=None, title="AI Asistan", label="Talep:"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(500, 300)
        self.setup_ui(label)
        
    def setup_ui(self, label_text):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(label_text))
        
        self.input_text = QPlainTextEdit()
        self.input_text.setPlaceholderText("Buraya detaylıca yazın...")
        self.input_text.setLineWrapMode(QPlainTextEdit.WidgetWidth) # Force wrap
        layout.addWidget(self.input_text)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
    def get_text(self):
        return self.input_text.toPlainText()

class AITakeoffThread(QThread):
    finished = pyqtSignal(dict, str, str) # items (hierarchical), explanation, error
    status_update = pyqtSignal(str)

    def __init__(self, text, api_key, model, base_url, gemini_key=None, gemini_model=None, provider="OpenRouter"):
        super().__init__()
        self.text = text
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.gemini_key = gemini_key
        self.gemini_model = gemini_model
        self.provider = provider

    def run(self):
        prompt = f"""
        Sen uzman bir inşaat metraj mühendisisin.
        Görev: Verilen metinden imalat gruplarını ve bu gruplara ait DETAYLI malzeme metrajlarını (Beton, Kalıp, Demir vb.) çıkar.

        Metin: "{self.text}"

        Kurallar ve Hesaplama Mantığı:
        
        **GENEL YAPI ELEMANLARI:**
        1. **Beton (m3):** Hacim.
        2. **Kalıp (m2):** Temas yüzey alanı.
        3. **Demir (ton):** Ort. 80-100 kg/m3.
        
        **ÖZEL ALTYAPI VE KANAL İMALATLARI (Kullanıcı tarifine göre uygula):**
        
        **1) Betonarme U Kanal:**
         - **Taban Betonu:** L x b(iç) x t1(taban_kalınlık).
         - **Yan Duvar Betonu:** L x h(iç) x t2(duvar_kalınlık) x 2.
         - **Kalıp (İç+Dış):** 4 x L x h. (Dış yüzeyin de kalıplandığını varsay).
        
        **2) Betonarme İstinat Duvarı:**
         - **Gövde Betonu:** L x H x t(gövde).
         - **Taban Betonu:** L x B(taban_genişlik) x t0(taban_kalınlık).
         - **Kalıp (Gövde Ön+Arka):** 2 x L x H.
        
        **3) Trapez Kanal (Toprak/Beton):**
         - **Kazı (m3):** A_kesit = (b + B)/2 * h. V = A * L. (B = b + 2*h*m).
         - **Kaplama Betonu (m3):** A_kaplama * kalınlık.
           (A_kaplama = L*b + 2*L * sqrt(h^2 + (h*m)^2)).
        
        **4) Taş Duvar:**
         - **Hacim (m3):** L x H x Ortalama_Kalınlık.
         - **Harpuşta (m3):** L x w x t.
        
        **5) Korkuluk:**
         - **Korkuluk (m):** Hat uzunluğu.
         - **Dikme (Adet):** (L / aralık) + 1.

        İstenen Çıktı Formatı (JSON Object):
        {{
          "explanation": "Buraya hesaplama mantığını ve kabul edilen varsayımları detaylıca yaz. Örn: 'İstinat duvarı için L=50m H=3m kabul edilmiştir...'",
          "groups": [
              {{
                "group_name": "Grup Adı (Örn: İstinat Duvarı)",
                "unit": "", 
                "items": [
                  {{
                    "description": "Örn: İstinat Gövde Betonu",
                    "similar_count": 1,
                    "length": 50.0,
                    "width": 0.50,
                    "height": 3.00,
                    "quantity": 75.0,
                    "unit": "m3",
                    "notes": "50x3x0.5"
                  }}
                ]
              }}
          ]
        }}
        
        Tek bir JSON nesnesi döndür. "explanation" alanı ZORUNLUDUR.
        """

        if self.provider == "Google Gemini":
            # Primary: Gemini
            if self.gemini_key:
                try:
                    self.status_update.emit("🤖 Gemini ile hesaplanıyor...")
                    self.call_gemini(prompt)
                    return
                except Exception as e:
                    error_msg = str(e)
                    print(f"Gemini Error: {error_msg}")
                    
                    if "503" in error_msg:
                        self.status_update.emit("⚠️ Gemini servisi yoğun, OpenRouter deneniyor...")
                    else:
                        self.status_update.emit(f"⚠️ Gemini hatası ({error_msg[:30]}...), OpenRouter deneniyor...")
                    pass
            else:
                 self.status_update.emit("⚠️ Gemini anahtarı yok, OpenRouter kullanılıyor...")
                 
            # Fallback/Default Logic (OpenRouter)
            try:
                self.call_openrouter(prompt)
            except Exception as e:
                self.finished.emit({}, "", f"Tüm denemeler başarısız.\n{str(e)}")
        
        else:
            # Primary: OpenRouter (Default)
            try:
                self.status_update.emit("🤖 OpenRouter ile hesaplanıyor...")
                if not self.api_key:
                    raise Exception("OpenRouter API Anahtarı eksik!")
                self.call_openrouter(prompt)
                return

            except Exception as e:
                print(f"OpenRouter Error: {e}")
                
                # Failover to Gemini
                if self.gemini_key:
                    try:
                        self.status_update.emit("⚠️ OpenRouter hatası, Gemini deneniyor...")
                        self.call_gemini(prompt)
                        return
                    except Exception as gemini_e:
                        self.finished.emit({}, "", f"Tüm denemeler başarısız.\nOpenRouter: {str(e)}\nGemini: {str(gemini_e)}")
                else:
                    self.finished.emit({}, "", f"İşlem Hatası (OpenRouter): {str(e)}\nYedek Gemini anahtarı tanımlı değil.")

    def call_openrouter(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://yaklasikmaliyetpro.com",
            "X-Title": "Yaklasik Maliyet Pro"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful construction quantity surveyor. Output valid JSON object only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "transforms": ["middle-out"],
            "max_tokens": 2000
        }
        
        response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=45)
        
        if response.status_code != 200:
            raise Exception(f"API Hatası ({response.status_code}): {response.text}")
            
        raw_content = response.json()['choices'][0]['message']['content']
        self.process_response(raw_content)

    def call_gemini(self, prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
        
        # Adjust prompt for Gemini (it likes clean prompts)
        final_prompt = "You are a helpful construction quantity surveyor. Output valid JSON object only.\n" + prompt
        
        data = {
            "contents": [{
                "parts": [{"text": final_prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2000,
                "responseMimeType": "application/json"
            }
        }
        
        response = requests.post(url, json=data, timeout=45)
        
        if response.status_code != 200:
            raise Exception(f"Gemini API Hatası ({response.status_code}): {response.text}")
            
        result = response.json()
        if 'candidates' in result and result['candidates']:
            raw_content = result['candidates'][0]['content']['parts'][0]['text']
            self.process_response(raw_content)
        else:
            raise Exception("Gemini boş yanıt döndürdü.")

    def process_response(self, raw_content):
        content = raw_content.strip()
        
        # Attempt to find JSON object structure
        start = content.find('{')
        end = content.rfind('}')
        
        if start != -1 and end != -1:
            content = content[start:end+1]
        else:
            content = content.replace("```json", "").replace("```", "").strip()

        try:
            items = json.loads(content)
            
            # Robust extraction of explanation if available
            explanation = ""
            if isinstance(items, dict):
                explanation = items.get("explanation", "")
                
            self.finished.emit(items, explanation, "")
        except json.JSONDecodeError as json_err:
            try:
                # Common fix cleanup
                corrected = re.sub(r',\s*}', '}', content)
                corrected = re.sub(r',\s*]', ']', corrected)
                items = json.loads(corrected)
                
                explanation = ""
                if isinstance(items, dict):
                    explanation = items.get("explanation", "")
                    
                self.finished.emit(items, explanation, "")
            except:
                error_msg = f"JSON Ayrıştırma Hatası: {str(json_err)}\n\nGelen Veri: {raw_content[:200]}..."
                self.finished.emit({}, "", error_msg)
        
        except Exception as e:
            self.finished.emit({}, "", f"İşlem Hatası: {str(e)}")

class TakeoffEditDialog(QDialog):
    def __init__(self, parent=None, takeoff_data=None):
        super().__init__(parent)
        self.takeoff_data = takeoff_data
        self.setWindowTitle("Metraj Düzenle" if takeoff_data else "Yeni Metraj")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.desc_input = QLineEdit()
        if self.takeoff_data: self.desc_input.setText(self.takeoff_data['description'])
        form.addRow("Tanım:", self.desc_input)
        
        # Dimensions
        dim_layout = QHBoxLayout()
        self.similar_input = QDoubleSpinBox()
        self.similar_input.setRange(1, 10000)
        self.similar_input.setPrefix("Benzer: ")
        self.similar_input.setValue(self.takeoff_data['similar_count'] if self.takeoff_data else 1)
        dim_layout.addWidget(self.similar_input)
        self.length_input = QDoubleSpinBox()
        self.length_input.setRange(0, 10000)
        self.length_input.setPrefix("Boy: ")
        self.length_input.setValue(self.takeoff_data['length'] if self.takeoff_data else 0)
        dim_layout.addWidget(self.length_input)
        self.width_input = QDoubleSpinBox()
        self.width_input.setRange(0, 10000)
        self.width_input.setPrefix("En: ")
        self.width_input.setValue(self.takeoff_data['width'] if self.takeoff_data else 0)
        dim_layout.addWidget(self.width_input)
        self.height_input = QDoubleSpinBox()
        self.height_input.setRange(0, 10000)
        self.height_input.setPrefix("Yük: ")
        self.height_input.setValue(self.takeoff_data['height'] if self.takeoff_data else 0)
        dim_layout.addWidget(self.height_input)
        form.addRow("Boyutlar:", dim_layout)
        
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["m3", "m2", "m", "adet"])
        if self.takeoff_data: self.unit_combo.setCurrentText(self.takeoff_data['unit'])
        form.addRow("Birim:", self.unit_combo)
        
        self.notes_input = QLineEdit()
        if self.takeoff_data: self.notes_input.setText(self.takeoff_data['notes'])
        form.addRow("Notlar:", self.notes_input)
        
        layout.addLayout(form)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
    def get_data(self):
        # Calculate quantity
        sim = self.similar_input.value()
        l = self.length_input.value()
        w = self.width_input.value()
        h = self.height_input.value()
        
        val = sim
        if l > 0: val *= l
        if w > 0: val *= w
        if h > 0: val *= h
        if l == 0 and w == 0 and h == 0: val = 0 # Fallback logic
        
        return {
            'description': self.desc_input.text(),
            'similar_count': sim,
            'length': l,
            'width': w,
            'height': h,
            'quantity': val,
            'unit': self.unit_combo.currentText(),
            'notes': self.notes_input.text()
        }

class QuantityTakeoffManager(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.current_group_id = None
        self.setup_ui()
        self.refresh_groups()
        self.ai_thread = None

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Top: AI Button ---
        ai_layout = QHBoxLayout()
        self.ai_btn = QPushButton("🤖 Yapay Zeka ile İmalat Ekle")
        self.ai_btn.setStyleSheet("""
            QPushButton {
                background-color: #673AB7; 
                color: white; 
                font-weight: bold; 
                padding: 10px;
                font-size: 11pt;
            }
            QPushButton:hover { background-color: #5E35B1; }
        """)
        self.ai_btn.clicked.connect(self.start_ai_takeoff)
        ai_layout.addWidget(self.ai_btn)
        layout.addLayout(ai_layout)
        
        # --- Splitter (Left: Groups, Right: Details) ---
        splitter = QSplitter(Qt.Horizontal)
        
        # --- Left Panel: Groups ---
        left_widget = QGroupBox("İmalat Grupları")
        left_layout = QVBoxLayout()
        
        self.group_table = QTableWidget()
        self.group_table.setColumnCount(3)
        self.group_table.setHorizontalHeaderLabels(['ID', 'İmalat Adı', 'Birim'])
        self.group_table.hideColumn(0)
        self.group_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.group_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.group_table.itemSelectionChanged.connect(self.on_group_selected)
        
        # Context Menu
        self.group_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.group_table.customContextMenuRequested.connect(self.show_group_context_menu)
        
        left_layout.addWidget(self.group_table)
        
        group_btns = QHBoxLayout()
        del_group_btn = QPushButton("- Sil")
        del_group_btn.clicked.connect(self.delete_group)
        group_btns.addWidget(del_group_btn)
        left_layout.addLayout(group_btns)
        
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        # --- Right Panel: Details ---
        right_widget = QGroupBox("Metraj Detayları")
        right_layout = QVBoxLayout()
        
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(8)
        self.detail_table.setHorizontalHeaderLabels([
            'ID', 'Tanım', 'Benzer', 'Boy', 'En', 'Yük', 'Miktar', 'Birim'
        ])
        self.detail_table.hideColumn(0)
        self.detail_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.detail_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.detail_table.itemDoubleClicked.connect(self.load_for_edit)
        right_layout.addWidget(self.detail_table)
        
        detail_btns = QHBoxLayout()
        add_manual_btn = QPushButton("+ Ekle")
        add_manual_btn.clicked.connect(lambda: self.load_for_edit(None))
        detail_btns.addWidget(add_manual_btn)
        
        del_detail_btn = QPushButton("- Sil")
        del_detail_btn.clicked.connect(self.delete_detail)
        detail_btns.addWidget(del_detail_btn)
        
        right_layout.addLayout(detail_btns)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        # Set splitter sizes (30% - 70%)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)

    def refresh_groups(self):
        self.group_table.setRowCount(0)
        groups = self.db.get_quantity_groups()
        for row, grp in enumerate(groups):
            self.group_table.insertRow(row)
            self.group_table.setItem(row, 0, QTableWidgetItem(str(grp['id'])))
            self.group_table.setItem(row, 1, QTableWidgetItem(grp['name']))
            self.group_table.setItem(row, 2, QTableWidgetItem(grp['unit']))
            
        # Select first if exists
        #if self.group_table.rowCount() > 0:
        #    self.group_table.selectRow(0)

    def on_group_selected(self):
        selected_items = self.group_table.selectedItems()
        if not selected_items:
            self.current_group_id = None
            self.detail_table.setRowCount(0)
            return
            
        # ID is in column 0
        self.current_group_id = int(self.group_table.item(selected_items[0].row(), 0).text())
        self.refresh_details()

    def refresh_details(self):
        if not self.current_group_id:
            return
            
        self.detail_table.setRowCount(0)
        takeoffs = self.db.get_takeoffs_by_group(self.current_group_id)
        
        for row, item in enumerate(takeoffs):
            self.detail_table.insertRow(row)
            self.detail_table.setItem(row, 0, QTableWidgetItem(str(item['id'])))
            self.detail_table.setItem(row, 1, QTableWidgetItem(item['description']))
            self.detail_table.setItem(row, 2, QTableWidgetItem(str(item['similar_count'])))
            self.detail_table.setItem(row, 3, QTableWidgetItem(str(item['length'])))
            self.detail_table.setItem(row, 4, QTableWidgetItem(str(item['width'])))
            self.detail_table.setItem(row, 5, QTableWidgetItem(str(item['height'])))
            self.detail_table.setItem(row, 6, QTableWidgetItem(str(item['quantity'])))
            self.detail_table.setItem(row, 7, QTableWidgetItem(item['unit']))

    def save_takeoff_from_dialog(self, takeoff_id, data):
        if not self.current_group_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce soldan bir İmalat Grubu seçin.")
            return

        if takeoff_id:
            self.db.update_quantity_takeoff(
                takeoff_id, data['description'], data['similar_count'], 
                data['length'], data['width'], data['height'], 
                data['quantity'], data['unit'], data['notes']
            )
        else:
            self.db.add_quantity_takeoff(
                data['description'], data['similar_count'], 
                data['length'], data['width'], data['height'], 
                data['quantity'], data['unit'], data['notes'],
                group_id=self.current_group_id
            )
        self.refresh_details()

    def delete_group(self):
        if not self.current_group_id: return
        reply = QMessageBox.question(self, "Sil", "Grubu ve altındaki TÜM metrajları silmek istiyor musunuz?", QMessageBox.Yes|QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.delete_quantity_group(self.current_group_id)
            self.refresh_groups()
            self.detail_table.setRowCount(0)
            self.current_group_id = None

    def delete_detail(self):
        row = self.detail_table.currentRow()
        if row < 0: return
        item_id = int(self.detail_table.item(row, 0).text())
        if QMessageBox.question(self, "Sil", "Satırı sil?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            self.db.delete_quantity_takeoff(item_id)
            self.refresh_details()

    def load_for_edit(self, item):
        if not self.current_group_id:
             QMessageBox.warning(self, "Uyarı", "Lütfen önce soldan bir İmalat Grubu seçin veya oluşturun.")
             return
             
        takeoff_data = None
        takeoff_id = None
        
        if item is not None:
            # Edit mode
            row = item.row()
            id_item = self.detail_table.item(row, 0)
            if not id_item: return
            takeoff_id = int(id_item.text())
            
            takeoff_data = {
                'description': self.detail_table.item(row, 1).text(),
                'similar_count': float(self.detail_table.item(row, 2).text()),
                'length': float(self.detail_table.item(row, 3).text()),
                'width': float(self.detail_table.item(row, 4).text()),
                'height': float(self.detail_table.item(row, 5).text()),
                'quantity': float(self.detail_table.item(row, 6).text()),
                'unit': self.detail_table.item(row, 7).text(),
                'notes': "" 
            }
            
        dialog = TakeoffEditDialog(self, takeoff_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            self.save_takeoff_from_dialog(takeoff_id, data)

    def show_group_context_menu(self, position):
        menu = QMenu()
        show_details_action = menu.addAction("📜 İsteği ve Hesabı Göster")
        delete_action = menu.addAction("🗑️ Grubu Sil")
        
        action = menu.exec_(self.group_table.viewport().mapToGlobal(position))
        
        if action == delete_action:
            self.delete_group()
        elif action == show_details_action:
            self.show_request_details()

    def show_request_details(self):
        row = self.group_table.currentRow()
        if row < 0: return
        
        group_id = int(self.group_table.item(row, 0).text())
        
        # Get extra details from DB (user_prompt, methodology)
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_prompt, methodology FROM quantity_groups WHERE id=?", (group_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return
            
        user_prompt = result[0] if result[0] else "Kayıt bulunamadı."
        methodology = result[1] if result[1] else "Hesaplama detayları kaydedilmemiş (Eski sürüm verisi)."
        
        dialog = QDialog(self)
        dialog.setWindowTitle("İstek ve Hesaplama Detayları")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("<b>👤 Kullanıcı İsteği:</b>"))
        prompt_text = QTextEdit()
        prompt_text.setReadOnly(True)
        prompt_text.setText(user_prompt)
        layout.addWidget(prompt_text)
        
        layout.addWidget(QLabel("<b>🤖 AI Hesaplama Mantığı & Varsayımlar:</b>"))
        method_text = QTextEdit()
        method_text.setReadOnly(True)
        method_text.setText(methodology)
        layout.addWidget(method_text)
        
        btn = QPushButton("Kapat")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)
        
        dialog.exec_()

    def start_ai_takeoff(self):
        dialog = AIPromptDialog(
            self, 
            "Yapay Zeka Metraj Asistanı", 
            "İmalatları tarif edin (Örn: 'Zemin katta 10 tane 30x50 kolon var (H=3m). Ayrıyeten 5 adet kiriş var...'):"
        )
        
        if dialog.exec_() != QDialog.Accepted:
            return
            
        text = dialog.get_text()
        if not text.strip():
            return
            
        self.last_ai_prompt_text = text
            
        api_key = self.db.get_setting("openrouter_api_key")
        if not api_key:
             QMessageBox.warning(self, "Uyarı", "OpenRouter API Anahtarı eksik!")
             return
             
        model = self.db.get_setting("openrouter_model") or "google/gemini-2.0-flash-exp:free"
        base_url = self.db.get_setting("openrouter_base_url") or "https://openrouter.ai/api/v1"
        
        # Gemini Settings (Failover)
        gemini_key = self.db.get_setting("gemini_api_key")
        gemini_model = self.db.get_setting("gemini_model") or "gemini-1.5-flash"
        
        provider = self.db.get_setting("ai_provider") or "OpenRouter"
        
        self.ai_btn.setEnabled(False)
        self.ai_btn.setText("🤖 Hesaplanıyor...")
        
        self.ai_thread = AITakeoffThread(text, api_key, model, base_url, gemini_key, gemini_model, provider)
        self.ai_thread.finished.connect(self.on_ai_finished)
        self.ai_thread.status_update.connect(lambda s: self.ai_btn.setText(s))
        self.ai_thread.start()
        
    def on_ai_finished(self, data, explanation, error):
        self.ai_btn.setEnabled(True)
        self.ai_btn.setText("🤖 Yapay Zeka ile İmalat Ekle")
        
        if error:
            QMessageBox.critical(self, "Hata", error)
            return
            
        if not data or 'groups' not in data:
            QMessageBox.warning(self, "Uyarı", "Veri çözümlenemedi!")
            return
            
        count = 0
        
        # Save each group with prompt and explanation
        for grp in data['groups']:
            group_name = grp.get('group_name', 'Yeni Grup')
            unit = grp.get('unit', '')
            
            # Create Group with Prompt AND Methodology
            group_id = self.db.add_quantity_group(group_name, unit, self.last_ai_prompt_text, explanation)
            
            for item in grp.get('items', []):
                self.db.add_quantity_takeoff(
                    item.get('description', ''),
                    item.get('similar_count', 1),
                    item.get('length', 0),
                    item.get('width', 0),
                    item.get('height', 0),
                    item.get('quantity', 0),
                    item.get('unit', ''),
                    item.get('notes', ''),
                    group_id=group_id
                )
            count += len(grp.get('items', []))
            
        self.refresh_groups()
        QMessageBox.information(self, "Tamamlandı", f"{count} imalat eklendi.\nHesaplama detaylarını görmek için gruba sağ tıklayınız.")
