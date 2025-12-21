
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QLineEdit, QGroupBox, QFormLayout,
                             QDoubleSpinBox, QMessageBox, QComboBox, QInputDialog, QDialog,
                             QDialogButtonBox, QPlainTextEdit, QMenu, QSplitter, QTextEdit,
                             QApplication, QFileDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from database import DatabaseManager
from pdf_exporter import PDFExporter
import json
import requests
import re


class ErrorDialog(QDialog):
    """Kopyalanabilir hata mesajı gösteren dialog"""
    def __init__(self, parent=None, title="Hata", message=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(500, 300)
        self.setup_ui(message)

    def setup_ui(self, message):
        layout = QVBoxLayout(self)

        # Hata ikonu ve başlık
        header = QLabel("❌ Bir hata oluştu:")
        header.setStyleSheet("font-weight: bold; font-size: 12pt; color: #D32F2F;")
        layout.addWidget(header)

        # Kopyalanabilir hata mesajı
        self.error_text = QPlainTextEdit()
        self.error_text.setPlainText(message)
        self.error_text.setReadOnly(True)
        self.error_text.setFont(QFont("Consolas", 9))
        self.error_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #FFEBEE;
                border: 1px solid #EF9A9A;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.error_text)

        # Butonlar
        btn_layout = QHBoxLayout()

        copy_btn = QPushButton("📋 Kopyala")
        copy_btn.clicked.connect(self.copy_error)
        copy_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px 16px;")
        btn_layout.addWidget(copy_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("padding: 8px 16px;")
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def copy_error(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.error_text.toPlainText())
        QMessageBox.information(self, "Kopyalandı", "Hata mesajı panoya kopyalandı.")


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

class AIAnalyzeComponentsThread(QThread):
    """Adım 1: İmalatın bileşenlerini (malzeme, işçilik, makine) analiz eden thread"""
    finished = pyqtSignal(dict, str)  # components_data, error
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
        prompt = self._get_analysis_prompt()
        self._execute_with_prompt(prompt)

    def _get_analysis_prompt(self):
        return f"""Verilen imalat için gerekli bileşenleri (malzeme, işçilik, makine) belirle.

İmalat: "{self.text}"

JSON formatında yanıt ver:
{{
  "imalat_adi": "İmalat adı",
  "imalat_aciklama": "Kısa açıklama",
  "bilesenler": [
    {{"kategori": "MALZEME", "ad": "Beton C25", "birim": "m3", "aciklama": "Hazır beton"}},
    {{"kategori": "MALZEME", "ad": "Demir", "birim": "ton", "aciklama": "Donatı"}},
    {{"kategori": "MALZEME", "ad": "Kalıp", "birim": "m2", "aciklama": "Ahşap kalıp"}},
    {{"kategori": "ISCILIK", "ad": "Kalıpçı", "birim": "saat", "aciklama": "İşçilik"}},
    {{"kategori": "MAKINE", "ad": "Ekskavatör", "birim": "saat", "aciklama": "Kazı makinesi"}},
    {{"kategori": "DIGER", "ad": "Kazı", "birim": "m3", "aciklama": "Temel kazısı"}}
  ]
}}

Kategoriler: MALZEME, ISCILIK, MAKINE, DIGER
Birimler: m3, m2, m, ton, kg, saat, adet, gün"""

    def _execute_with_prompt(self, prompt):
        """Prompt ile AI çağrısını yap"""
        gemini_error = None
        openrouter_error = None

        if self.provider == "Google Gemini":
            if self.gemini_key:
                try:
                    self.status_update.emit("🔍 Gemini ile imalat analiz ediliyor...")
                    self._call_gemini(prompt)
                    return
                except Exception as e:
                    gemini_error = str(e)
                    self.status_update.emit("⚠️ Gemini hatası, OpenRouter deneniyor...")
            else:
                gemini_error = "Gemini API anahtarı tanımlı değil"

            if self.api_key:
                try:
                    self.status_update.emit("🔍 OpenRouter ile imalat analiz ediliyor...")
                    self._call_openrouter(prompt)
                    return
                except Exception as e:
                    openrouter_error = str(e)
            else:
                openrouter_error = "OpenRouter API anahtarı tanımlı değil"

            self.finished.emit({}, f"Tüm kaynaklar başarısız.\nGemini: {gemini_error}\nOpenRouter: {openrouter_error}")
        else:
            if self.api_key:
                try:
                    self.status_update.emit("🔍 OpenRouter ile imalat analiz ediliyor...")
                    self._call_openrouter(prompt)
                    return
                except Exception as e:
                    openrouter_error = str(e)
                    self.status_update.emit("⚠️ OpenRouter hatası, Gemini deneniyor...")
            else:
                openrouter_error = "OpenRouter API anahtarı tanımlı değil"

            if self.gemini_key:
                try:
                    self.status_update.emit("🔍 Gemini ile imalat analiz ediliyor...")
                    self._call_gemini(prompt)
                    return
                except Exception as e:
                    gemini_error = str(e)
            else:
                gemini_error = "Gemini API anahtarı tanımlı değil"

            self.finished.emit({}, f"Tüm kaynaklar başarısız.\nOpenRouter: {openrouter_error}\nGemini: {gemini_error}")

    def _call_openrouter(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://yaklasikmaliyetpro.com",
            "X-Title": "Yaklasik Maliyet Pro"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful construction engineer. Output valid JSON object only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 3000,
            "transforms": ["middle-out"]
        }
        response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=90)
        if response.status_code != 200:
            raise Exception(f"API Hatası ({response.status_code}): {response.text[:500]}")
        result = response.json()
        if 'choices' not in result or not result['choices']:
            raise Exception(f"Geçersiz API yanıtı: {str(result)[:300]}")
        raw_content = result['choices'][0]['message']['content']
        if not raw_content or not raw_content.strip():
            raise Exception("API boş yanıt döndürdü. Lütfen tekrar deneyin.")
        self._process_response(raw_content)

    def _call_gemini(self, prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
        final_prompt = "Sen bir inşaat mühendisisin. Sadece geçerli JSON döndür.\n" + prompt
        data = {
            "contents": [{"parts": [{"text": final_prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 3000,
                "responseMimeType": "application/json"
            }
        }
        response = requests.post(url, json=data, timeout=90)
        if response.status_code != 200:
            raise Exception(f"Gemini API Hatası ({response.status_code}): {response.text}")
        result = response.json()
        if 'candidates' in result and result['candidates']:
            raw_content = result['candidates'][0]['content']['parts'][0]['text']
            self._process_response(raw_content)
        else:
            raise Exception("Gemini boş yanıt döndürdü.")

    def _process_response(self, raw_content):
        content = raw_content.strip()
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            content = content[start:end+1]
        else:
            content = content.replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(content)
            self.finished.emit(data, "")
        except json.JSONDecodeError as e:
            # JSON onarımını dene
            try:
                corrected = self._repair_truncated_json(content)
                data = json.loads(corrected)
                self.finished.emit(data, "")
            except:
                self.finished.emit({}, f"JSON Ayrıştırma Hatası: {str(e)}\n\nGelen Veri: {raw_content[:300]}...")

    def _repair_truncated_json(self, content):
        """Kesilmiş JSON'u onarmaya çalış"""
        corrected = re.sub(r',\s*}', '}', content)
        corrected = re.sub(r',\s*]', ']', corrected)
        corrected = re.sub(r'"\s*\n\s*"', '",\n"', corrected)
        corrected = re.sub(r'"\s+"', '", "', corrected)
        corrected = re.sub(r'}\s*{', '}, {', corrected)
        corrected = re.sub(r']\s*\[', '], [', corrected)

        # Açık kalan string'i kapat
        quote_count = corrected.count('"')
        if quote_count % 2 != 0:
            corrected = corrected.rstrip()
            if not corrected.endswith('"'):
                corrected += '"'

        open_braces = corrected.count('{') - corrected.count('}')
        open_brackets = corrected.count('[') - corrected.count(']')
        corrected = corrected.rstrip()
        if corrected.endswith(','):
            corrected = corrected[:-1]
        corrected += ']' * max(0, open_brackets)
        corrected += '}' * max(0, open_braces)
        return corrected


class ComponentPreviewDialog(QDialog):
    """Adım 1.5: AI'ın belirlediği bileşenleri göster ve kullanıcı onayı al"""
    def __init__(self, parent=None, components_data=None):
        super().__init__(parent)
        self.components_data = components_data or {}
        self.selected_components = []
        self.setWindowTitle("🔍 İmalat Bileşenleri - Onay")
        self.setMinimumSize(700, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Başlık
        imalat_adi = self.components_data.get('imalat_adi', 'İmalat')
        imalat_aciklama = self.components_data.get('imalat_aciklama', '')

        header = QLabel(f"<h2>🏗️ {imalat_adi}</h2>")
        header.setStyleSheet("color: #1565C0;")
        layout.addWidget(header)

        if imalat_aciklama:
            desc_label = QLabel(f"<i>{imalat_aciklama}</i>")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        layout.addWidget(QLabel("<b>Bu imalat için belirlenen bileşenler:</b>"))
        layout.addWidget(QLabel("<small>Metraj hesaplanmasını istediğiniz bileşenleri seçin veya düzenleyin.</small>"))

        # Bileşen tablosu
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['✓', 'Kategori', 'Bileşen Adı', 'Birim', 'Açıklama'])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        # Bileşenleri tabloya ekle
        bilesenler = self.components_data.get('bilesenler', [])
        self.table.setRowCount(len(bilesenler))

        for row, bilesen in enumerate(bilesenler):
            # Checkbox
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox.setCheckState(Qt.Checked)  # Varsayılan olarak seçili
            self.table.setItem(row, 0, checkbox)

            # Kategori
            kategori = bilesen.get('kategori', 'DIGER')
            kategori_item = QTableWidgetItem(kategori)
            if kategori == 'MALZEME':
                kategori_item.setBackground(QColor('#E3F2FD'))
            elif kategori in ('ISCILIK', 'İŞÇİLİK'):
                kategori_item.setBackground(QColor('#E8F5E9'))
            elif kategori in ('MAKINE', 'MAKİNE'):
                kategori_item.setBackground(QColor('#FFF3E0'))
            else:
                kategori_item.setBackground(QColor('#F3E5F5'))
            self.table.setItem(row, 1, kategori_item)

            # Ad
            self.table.setItem(row, 2, QTableWidgetItem(bilesen.get('ad', '')))

            # Birim
            self.table.setItem(row, 3, QTableWidgetItem(bilesen.get('birim', '')))

            # Açıklama
            self.table.setItem(row, 4, QTableWidgetItem(bilesen.get('aciklama', '')))

        layout.addWidget(self.table)

        # Butonlar: Tümünü Seç / Seçimi Kaldır
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("✅ Tümünü Seç")
        select_all_btn.clicked.connect(self.select_all)
        select_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("⬜ Seçimi Kaldır")
        deselect_all_btn.clicked.connect(self.deselect_all)
        select_layout.addWidget(deselect_all_btn)

        select_layout.addStretch()
        layout.addLayout(select_layout)

        # Onay Butonları
        btn_layout = QHBoxLayout()

        cancel_btn = QPushButton("❌ İptal")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()

        ok_btn = QPushButton("✅ Seçilenlerin Metrajını Hesapla")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                font-size: 11pt;
            }
            QPushButton:hover { background-color: #43A047; }
        """)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def select_all(self):
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(Qt.Checked)

    def deselect_all(self):
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(Qt.Unchecked)

    def get_selected_components(self):
        """Seçili bileşenleri döndür"""
        selected = []
        bilesenler = self.components_data.get('bilesenler', [])

        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                # Tablodaki güncel değerleri al (kullanıcı düzenlemiş olabilir)
                selected.append({
                    'kategori': self.table.item(row, 1).text(),
                    'ad': self.table.item(row, 2).text(),
                    'birim': self.table.item(row, 3).text(),
                    'aciklama': self.table.item(row, 4).text()
                })

        return selected


class AIComponentTakeoffThread(QThread):
    """Adım 2: Seçilen bileşenler için metraj hesaplayan thread"""
    finished = pyqtSignal(dict, str, str)  # items, explanation, error
    status_update = pyqtSignal(str)

    def __init__(self, user_request, imalat_adi, components, api_key, model, base_url, gemini_key=None, gemini_model=None, provider="OpenRouter"):
        super().__init__()
        self.user_request = user_request
        self.imalat_adi = imalat_adi
        self.components = components
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.gemini_key = gemini_key
        self.gemini_model = gemini_model
        self.provider = provider

    def run(self):
        prompt = self._get_takeoff_prompt()
        self._execute_with_prompt(prompt)

    def _get_takeoff_prompt(self):
        # Bileşenleri kategorize et
        components_text = ""
        for comp in self.components:
            components_text += f"- {comp['kategori']}: {comp['ad']} ({comp['birim']}) - {comp['aciklama']}\n"

        return f"""
        Sen uzman bir inşaat metraj mühendisisin.
        Görev: Verilen imalat ve bileşenler için DETAYLI METRAJ HESAPLA.

        **Kullanıcı Talebi:** "{self.user_request}"

        **İmalat Adı:** {self.imalat_adi}

        **Hesaplanacak Bileşenler:**
        {components_text}

        **ÖNEMLİ KURALLAR:**
        1. Her bileşen için ayrı bir metraj satırı oluştur
        2. Boyutları kullanıcı talebinden çıkar veya makul varsayımlar yap
        3. Hesaplama formüllerini "notes" alanında açıkla
        4. Birimler doğru olmalı (m3, m2, ton, saat, adet vb.)

        **HESAPLAMA KURALLARI:**
        - Beton: Hacim = Boy × En × Yükseklik (m3)
        - Kalıp: Alan = Kalıplanacak yüzey alanı (m2)
        - Demir: Yaklaşık %7-10 arası beton hacminin (ton olarak hesapla, 100 kg/m3 yaklaşık)
        - İşçilik: İmalat miktarına göre saat/gün olarak
        - Kazı: Temel boyutları + çalışma payı (0.3-0.5m)
        - Dolgu: Kazı hacmi - Beton hacmi

        **ÇIKTI FORMATI (JSON):**
        {{
          "explanation": "Detaylı hesaplama açıklaması. Örn: Temel boyutları 10m × 5m × 0.5m kabul edilmiştir. Beton hacmi: 10×5×0.5=25m3...",
          "groups": [
              {{
                "group_name": "{self.imalat_adi}",
                "unit": "",
                "items": [
                  {{"description": "Bileşen adı", "similar_count": 1, "length": 10.0, "width": 5.0, "height": 0.5, "quantity": 25.0, "unit": "m3", "notes": "Boy×En×Yük = 10×5×0.5"}}
                ]
              }}
          ]
        }}

        **DİKKAT:**
        - Her bileşen için bir item oluştur
        - Hesaplamaları "notes" alanında göster
        - "explanation" alanı ZORUNLU ve detaylı olmalı
        - Kullanıcı talebindeki boyutları kullan, yoksa makul varsayım yap
        """

    def _execute_with_prompt(self, prompt):
        """Prompt ile AI çağrısını yap"""
        gemini_error = None
        openrouter_error = None

        if self.provider == "Google Gemini":
            if self.gemini_key:
                try:
                    self.status_update.emit("📊 Gemini ile metraj hesaplanıyor...")
                    self._call_gemini(prompt)
                    return
                except Exception as e:
                    gemini_error = str(e)
                    self.status_update.emit("⚠️ Gemini hatası, OpenRouter deneniyor...")
            else:
                gemini_error = "Gemini API anahtarı tanımlı değil"

            if self.api_key:
                try:
                    self.status_update.emit("📊 OpenRouter ile metraj hesaplanıyor...")
                    self._call_openrouter(prompt)
                    return
                except Exception as e:
                    openrouter_error = str(e)
            else:
                openrouter_error = "OpenRouter API anahtarı tanımlı değil"

            self.finished.emit({}, "", f"Tüm kaynaklar başarısız.\nGemini: {gemini_error}\nOpenRouter: {openrouter_error}")
        else:
            if self.api_key:
                try:
                    self.status_update.emit("📊 OpenRouter ile metraj hesaplanıyor...")
                    self._call_openrouter(prompt)
                    return
                except Exception as e:
                    openrouter_error = str(e)
                    self.status_update.emit("⚠️ OpenRouter hatası, Gemini deneniyor...")
            else:
                openrouter_error = "OpenRouter API anahtarı tanımlı değil"

            if self.gemini_key:
                try:
                    self.status_update.emit("📊 Gemini ile metraj hesaplanıyor...")
                    self._call_gemini(prompt)
                    return
                except Exception as e:
                    gemini_error = str(e)
            else:
                gemini_error = "Gemini API anahtarı tanımlı değil"

            self.finished.emit({}, "", f"Tüm kaynaklar başarısız.\nOpenRouter: {openrouter_error}\nGemini: {gemini_error}")

    def _call_openrouter(self, prompt):
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
            "max_tokens": 4000,
            "transforms": ["middle-out"]
        }
        response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=120)
        if response.status_code != 200:
            raise Exception(f"API Hatası ({response.status_code}): {response.text[:500]}")
        result = response.json()
        if 'choices' not in result or not result['choices']:
            raise Exception(f"Geçersiz API yanıtı: {str(result)[:300]}")
        raw_content = result['choices'][0]['message']['content']
        self._process_response(raw_content)

    def _call_gemini(self, prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
        final_prompt = "You are a helpful construction quantity surveyor. Output valid JSON object only.\n" + prompt
        data = {
            "contents": [{"parts": [{"text": final_prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 4000,
                "responseMimeType": "application/json"
            }
        }
        response = requests.post(url, json=data, timeout=120)
        if response.status_code != 200:
            raise Exception(f"Gemini API Hatası ({response.status_code}): {response.text}")
        result = response.json()
        if 'candidates' in result and result['candidates']:
            raw_content = result['candidates'][0]['content']['parts'][0]['text']
            self._process_response(raw_content)
        else:
            raise Exception("Gemini boş yanıt döndürdü.")

    def _process_response(self, raw_content):
        content = raw_content.strip()
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            content = content[start:end+1]
        else:
            content = content.replace("```json", "").replace("```", "").strip()

        try:
            items = json.loads(content)
            explanation = ""
            if isinstance(items, dict):
                explanation = items.get("explanation", "")
            self.finished.emit(items, explanation, "")
        except json.JSONDecodeError as e:
            try:
                corrected = self._repair_truncated_json(content)
                items = json.loads(corrected)
                explanation = items.get("explanation", "") if isinstance(items, dict) else ""
                self.finished.emit(items, explanation, "")
            except:
                self.finished.emit({}, "", f"JSON Ayrıştırma Hatası: {str(e)}\n\nGelen Veri: {raw_content[:300]}...")

    def _repair_truncated_json(self, content):
        """Kesilmiş JSON'u onarmaya çalış"""
        corrected = re.sub(r',\s*}', '}', content)
        corrected = re.sub(r',\s*]', ']', corrected)
        corrected = re.sub(r'"\s*\n\s*"', '",\n"', corrected)
        corrected = re.sub(r'"\s+"', '", "', corrected)
        corrected = re.sub(r'}\s*{', '}, {', corrected)
        corrected = re.sub(r']\s*\[', '], [', corrected)

        open_braces = corrected.count('{') - corrected.count('}')
        open_brackets = corrected.count('[') - corrected.count(']')
        corrected = corrected.rstrip()
        if corrected.endswith(','):
            corrected = corrected[:-1]
        corrected += ']' * max(0, open_brackets)
        corrected += '}' * max(0, open_braces)
        return corrected


class AITakeoffThread(QThread):
    finished = pyqtSignal(dict, str, str) # items (hierarchical), explanation, error
    status_update = pyqtSignal(str)

    def __init__(self, text, api_key, model, base_url, gemini_key=None, gemini_model=None, provider="OpenRouter", custom_prompt=None):
        super().__init__()
        self.text = text
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.gemini_key = gemini_key
        self.gemini_model = gemini_model
        self.provider = provider
        self.custom_prompt = custom_prompt

    def run(self):
        # Özel prompt varsa kullan
        if self.custom_prompt:
            try:
                prompt = self.custom_prompt.format(text=self.text)
            except KeyError as e:
                print(f"Metraj prompt format hatası: {e}, varsayılan kullanılıyor")
                prompt = self._get_default_prompt()
        else:
            prompt = self._get_default_prompt()

        self._execute_with_prompt(prompt)

    def _get_default_prompt(self):
        return f"""
        Sen uzman bir inşaat metraj mühendisisin.
        Görev: Verilen metinden TEK BİR İMALAT GRUBU oluştur ve bu gruba ait TÜM MALZEME METRAJLARINI (Beton, Kalıp, Demir, Kazı, Dolgu vb.) hesapla.

        Metin: "{self.text}"

        **ÖNEMLİ KURALLAR:**
        1. SADECE TEK BİR GRUP oluştur (örn: "Betonarme U Kanal", "İstinat Duvarı" vb.)
        2. Bu grubun altında TÜM malzeme metrajlarını ayrı satırlar olarak listele
        3. Her malzeme için: Beton, Kalıp, Demir, Kazı, Dolgu, vb. ayrı satır olacak

        **HESAPLAMA KURALLARI:**

        **Betonarme U Kanal (iç_genişlik: b, iç_yükseklik: h, duvar_kalınlık: t, taban_kalınlık: t0, uzunluk: L):**
        - Taban Betonu (m3): L × (b + 2×t) × t0
        - Yan Duvar Betonu (m3): L × t × h × 2
        - Toplam Beton (m3): Taban + Yan Duvarlar
        - İç Kalıp (m2): L × (b + 2×h) (taban + 2 yan iç yüzey)
        - Dış Kalıp (m2): L × 2 × h (2 yan dış yüzey)
        - Demir (ton): Toplam Beton × 0.10 (100 kg/m3)
        - Kazı (m3): L × (b + 2×t + 0.5) × (h + t0 + 0.3) (çalışma payı dahil)
        - Geri Dolgu (m3): Kazı - Beton hacmi

        **Betonarme İstinat Duvarı:**
        - Gövde Betonu (m3): L × H × t
        - Taban Betonu (m3): L × B × t0
        - Kalıp (m2): 2 × L × H (ön + arka yüzey)
        - Demir (ton): Toplam Beton × 0.10

        **Taş Duvar:**
        - Duvar Hacmi (m3): L × H × t
        - Harpuşta (m3): L × genişlik × kalınlık

        **ÇIKTI FORMATI (JSON):**
        {{
          "explanation": "Hesaplama detayları ve varsayımlar. Örn: U Kanal için L=1m, iç genişlik=3m, iç yükseklik=2m, duvar kalınlığı=0.3m, taban kalınlığı=0.5m kabul edilmiştir. Taban betonu: 1×(3+0.6)×0.5=1.8m3...",
          "groups": [
              {{
                "group_name": "İmalat Adı (örn: Betonarme U Kanal)",
                "unit": "",
                "items": [
                  {{"description": "Taban Betonu", "similar_count": 1, "length": 1.0, "width": 3.6, "height": 0.5, "quantity": 1.8, "unit": "m3", "notes": "L×(b+2t)×t0 = 1×3.6×0.5"}},
                  {{"description": "Yan Duvar Betonu", "similar_count": 2, "length": 1.0, "width": 0.3, "height": 2.0, "quantity": 1.2, "unit": "m3", "notes": "L×t×h×2 = 1×0.3×2×2"}},
                  {{"description": "İç Kalıp", "similar_count": 1, "length": 1.0, "width": 7.0, "height": 1.0, "quantity": 7.0, "unit": "m2", "notes": "L×(b+2h) = 1×(3+4)"}},
                  {{"description": "Dış Kalıp", "similar_count": 2, "length": 1.0, "width": 2.0, "height": 1.0, "quantity": 4.0, "unit": "m2", "notes": "L×h×2 = 1×2×2"}},
                  {{"description": "Betonarme Demiri", "similar_count": 1, "length": 1.0, "width": 1.0, "height": 1.0, "quantity": 0.30, "unit": "ton", "notes": "Toplam beton × 0.10"}},
                  {{"description": "Kazı", "similar_count": 1, "length": 1.0, "width": 4.1, "height": 2.8, "quantity": 11.48, "unit": "m3", "notes": "Çalışma payı dahil"}},
                  {{"description": "Geri Dolgu", "similar_count": 1, "length": 1.0, "width": 1.0, "height": 1.0, "quantity": 8.48, "unit": "m3", "notes": "Kazı - Beton"}}
                ]
              }}
          ]
        }}

        **DİKKAT:**
        - SADECE 1 GRUP olacak, birden fazla grup OLUŞTURMA
        - Her malzeme türü (beton, kalıp, demir, kazı, dolgu) ayrı bir satır/item olacak
        - Hesaplamaları "notes" alanında göster
        - "explanation" alanı ZORUNLU ve detaylı olmalı
        """

    def _execute_with_prompt(self, prompt):
        """Prompt ile AI çağrısını yap"""
        gemini_error = None
        openrouter_error = None

        if self.provider == "Google Gemini":
            # Birincil: Gemini
            if self.gemini_key:
                try:
                    self.status_update.emit("🤖 Gemini ile hesaplanıyor...")
                    self.call_gemini(prompt)
                    return  # Başarılı, çık
                except Exception as e:
                    gemini_error = str(e)
                    if "503" in gemini_error:
                        self.status_update.emit("⚠️ Gemini servisi yoğun, OpenRouter deneniyor...")
                    else:
                        self.status_update.emit("⚠️ Gemini hatası, OpenRouter deneniyor...")
            else:
                gemini_error = "Gemini API anahtarı tanımlı değil"
                self.status_update.emit("⚠️ Gemini anahtarı yok, OpenRouter kullanılıyor...")

            # Yedek: OpenRouter
            if self.api_key:
                try:
                    self.status_update.emit("🤖 OpenRouter ile hesaplanıyor...")
                    self.call_openrouter(prompt)
                    return  # Başarılı, çık
                except Exception as e:
                    openrouter_error = str(e)
            else:
                openrouter_error = "OpenRouter API anahtarı tanımlı değil"

            # Her ikisi de başarısız
            self.finished.emit({}, "", f"Tüm kaynaklar başarısız.\nGemini: {gemini_error}\nOpenRouter: {openrouter_error}")

        else:
            # Birincil: OpenRouter
            if self.api_key:
                try:
                    self.status_update.emit("🤖 OpenRouter ile hesaplanıyor...")
                    self.call_openrouter(prompt)
                    return  # Başarılı, çık
                except Exception as e:
                    openrouter_error = str(e)
                    self.status_update.emit("⚠️ OpenRouter hatası, Gemini deneniyor...")
            else:
                openrouter_error = "OpenRouter API anahtarı tanımlı değil"
                self.status_update.emit("⚠️ OpenRouter anahtarı yok, Gemini kullanılıyor...")

            # Yedek: Gemini
            if self.gemini_key:
                try:
                    self.status_update.emit("🤖 Gemini ile hesaplanıyor...")
                    self.call_gemini(prompt)
                    return  # Başarılı, çık
                except Exception as e:
                    gemini_error = str(e)
            else:
                gemini_error = "Gemini API anahtarı tanımlı değil"

            # Her ikisi de başarısız
            self.finished.emit({}, "", f"Tüm kaynaklar başarısız.\nOpenRouter: {openrouter_error}\nGemini: {gemini_error}")

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
            "max_tokens": 4000
        }

        response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=60)

        if response.status_code != 200:
            raise Exception(f"API Hatası ({response.status_code}): {response.text[:500]}")

        # Boş yanıt kontrolü
        if not response.text or not response.text.strip():
            raise Exception("API boş yanıt döndürdü")

        try:
            result = response.json()
        except Exception as e:
            raise Exception(f"JSON parse hatası: {str(e)}")

        if 'choices' not in result or not result['choices']:
            raise Exception(f"Geçersiz API yanıtı: {str(result)[:300]}")

        raw_content = result['choices'][0]['message']['content']
        if not raw_content:
            raise Exception("API içerik boş döndürdü")

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
                "maxOutputTokens": 4000,
                "responseMimeType": "application/json"
            }
        }

        response = requests.post(url, json=data, timeout=60)
        
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
            # Önce standart onarımı dene
            try:
                corrected = self._repair_truncated_json(content)
                items = json.loads(corrected)

                explanation = ""
                if isinstance(items, dict):
                    explanation = items.get("explanation", "")

                self.finished.emit(items, explanation, "")
            except:
                # Standart onarım başarısız - sadece groups dizisini çıkarmayı dene
                try:
                    minimal_json = self._extract_groups_only(content)
                    if minimal_json:
                        items = json.loads(minimal_json)
                        explanation = "(AI açıklaması ayrıştırılamadı)"
                        self.finished.emit(items, explanation, "")
                    else:
                        raise Exception("Groups çıkarılamadı")
                except:
                    error_msg = f"JSON Ayrıştırma Hatası: {str(json_err)}\n\nGelen Veri: {raw_content[:200]}..."
                    self.finished.emit({}, "", error_msg)

        except Exception as e:
            self.finished.emit({}, "", f"İşlem Hatası: {str(e)}")

    def _repair_truncated_json(self, content):
        """Kesilmiş JSON'u onarmaya çalış"""
        import re
        
        # Trailing comma temizliği
        corrected = re.sub(r',\s*}', '}', content)
        corrected = re.sub(r',\s*]', ']', corrected)

        # Eksik virgül ekleme: "value" "key" -> "value", "key"
        corrected = re.sub(r'"\s*\n\s*"', '",\n"', corrected)
        corrected = re.sub(r'"\s+"', '", "', corrected)

        # Eksik virgül: } { veya ] [ arasında
        corrected = re.sub(r'}\s*{', '}, {', corrected)
        corrected = re.sub(r']\s*\[', '], [', corrected)

        # Eksik virgül: } "key" veya ] "value" arasında
        corrected = re.sub(r'}\s*"', '}, "', corrected)
        corrected = re.sub(r']\s*"', '], "', corrected)

        # Eksik virgül: number/true/false/null sonrası " karakteri
        corrected = re.sub(r'(\d)\s*\n\s*"', r'\1,\n"', corrected)
        corrected = re.sub(r'(true|false|null)\s*\n\s*"', r'\1,\n"', corrected)

        # Kesilmiş string'i kapat
        quote_count = corrected.count('"')
        if quote_count % 2 != 0:
            # Tek sayıda tırnak var, string kesilmiş
            # En son açılmamış tırnağı bul ve kapat
            corrected = corrected.rstrip()
            if not corrected.endswith('"'):
                corrected += '"'

        # Eksik kapanış parantezlerini say ve ekle
        open_braces = corrected.count('{') - corrected.count('}')
        open_brackets = corrected.count('[') - corrected.count(']')

        # Önce trailing virgül varsa kaldır
        corrected = corrected.rstrip()
        if corrected.endswith(','):
            corrected = corrected[:-1]

        # Eksik kapanışları ekle
        corrected += ']' * max(0, open_brackets)
        corrected += '}' * max(0, open_braces)

        return corrected
    
    def _extract_groups_only(self, content):
        """Sadece groups dizisini çıkarmaya çalış - explanation başarısız olduğunda"""
        import re
        
        print(f"[DEBUG] _extract_groups_only çalışıyor, içerik uzunluğu: {len(content)}")
        
        # "groups" dizisini bul - daha esnek regex
        # groups: [ ... ] veya "groups": [ ... ] formatlarını yakala
        groups_match = re.search(r'"groups"\s*:\s*\[', content, re.DOTALL)
        if groups_match:
            start_idx = groups_match.end() - 1  # [ karakterinden başla
            # Eşleşen köşeli parantezi bul
            bracket_count = 0
            end_idx = start_idx
            for i, char in enumerate(content[start_idx:]):
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = start_idx + i + 1
                        break
            
            if end_idx > start_idx:
                groups_str = content[start_idx:end_idx]
                print(f"[DEBUG] Groups dizisi bulundu: {groups_str[:100]}...")
                try:
                    # Sadece groups'u parse et
                    groups_array = json.loads(groups_str)
                    minimal_json = json.dumps({"groups": groups_array, "explanation": ""})
                    return minimal_json
                except Exception as e:
                    print(f"[DEBUG] Groups parse hatası: {e}")
                    # Son çare: onarım uygula
                    try:
                        repaired_groups = self._repair_truncated_json(groups_str)
                        groups_array = json.loads(repaired_groups)
                        if isinstance(groups_array, list):
                            minimal_json = json.dumps({"groups": groups_array, "explanation": ""})
                            return minimal_json
                    except:
                        pass
        else:
            print("[DEBUG] 'groups' anahtarı bulunamadı")
        
        return None

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
        self.csv_manager = None  # CSV manager için referans
        self.setup_ui()
        self.refresh_groups()
        self._init_csv_manager()
        self.ai_thread = None

    def _init_csv_manager(self):
        """Ana pencereden CSV manager'a erişmeye çalış"""
        try:
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'csv_manager'):
                main_window = main_window.parent()
            
            if main_window and hasattr(main_window, 'csv_manager'):
                self.csv_manager = main_window.csv_manager
        except:
            pass

    def _find_poz_for_item(self, item):
        """Metraj item'ı için uygun poz bul"""
        if not self.csv_manager or not hasattr(self.csv_manager, 'poz_data'):
            return None
        
        item_unit = item.get('unit', '').lower()
        item_desc = item.get('description', '').lower()
        
        # Önce birime göre ara
        best_match = None
        best_score = 0
        
        for poz_no, poz_info in self.csv_manager.poz_data.items():
            poz_unit = poz_info.get('unit', '').lower()
            poz_desc = poz_info.get('description', '').lower()
            
            score = 0
            
            # Birim eşleşmesi (en önemli)
            if item_unit and poz_unit:
                if item_unit == poz_unit:
                    score += 10
                elif item_unit in poz_unit or poz_unit in item_unit:
                    score += 5
            
            # Açıklama eşleşmesi
            if item_desc and poz_desc:
                # Anahtar kelimelere göre eşleşme
                item_keywords = set(item_desc.split())
                poz_keywords = set(poz_desc.split())
                common_keywords = item_keywords.intersection(poz_keywords)
                if common_keywords:
                    score += len(common_keywords) * 2
            
            if score > best_score:
                best_score = score
                best_match = poz_info
        
        return best_match

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
        self.group_table.setColumnCount(4)
        self.group_table.setHorizontalHeaderLabels(['ID', 'İmalat Adı', 'Birim', 'PDF'])
        self.group_table.hideColumn(0)
        self.group_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.group_table.setColumnWidth(2, 60)
        self.group_table.setColumnWidth(3, 50)
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

        group_btns.addStretch()

        # Tümünü PDF olarak dışa aktar
        pdf_all_btn = QPushButton("📑 Tümü PDF")
        pdf_all_btn.setToolTip("Tüm imalatlar için birleşik PDF metraj cetveli oluştur")
        pdf_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                padding: 5px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1565C0; }
        """)
        pdf_all_btn.clicked.connect(self.export_all_groups_pdf)
        group_btns.addWidget(pdf_all_btn)

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

            # PDF butonu ekle - hücre içinde ortalanmış
            pdf_btn = QPushButton("📄")
            pdf_btn.setToolTip(f"{grp['name']} için PDF oluştur")
            pdf_btn.setFixedSize(30, 25)
            pdf_btn.setStyleSheet("font-size: 12px; padding: 2px;")
            group_id = grp['id']
            pdf_btn.clicked.connect(lambda checked, gid=group_id: self.export_single_group_pdf(gid))

            # Butonu ortalamak için bir widget container kullan
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.addWidget(pdf_btn)
            btn_layout.setAlignment(Qt.AlignCenter)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            self.group_table.setCellWidget(row, 3, btn_container)

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

    def export_group_pdf(self):
        """Seçili imalat grubu için PDF metraj cetveli oluşturur"""
        if not self.current_group_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir imalat grubu seçin.")
            return
        self.export_single_group_pdf(self.current_group_id)

    def export_single_group_pdf(self, group_id):
        """Belirli bir imalat grubu için PDF metraj cetveli oluşturur"""
        # Grup bilgilerini al
        groups = self.db.get_quantity_groups()
        group_info = None
        for grp in groups:
            if grp['id'] == group_id:
                group_info = grp
                break

        if not group_info:
            QMessageBox.warning(self, "Hata", "Grup bilgisi bulunamadı.")
            return

        # Metraj detaylarını al
        items = self.db.get_takeoffs_by_group(group_id)

        # Her item için poz bilgisi bul ve ekle
        for item in items:
            poz_info = self._find_poz_for_item(item)
            if poz_info:
                item['poz_name'] = poz_info.get('poz_no', '')
            else:
                item['poz_name'] = item.get('location', item.get('poz', ''))

        # İmalat grubu verisi hazırla
        imalat_group = {
            'name': group_info['name'],
            'unit': group_info['unit'],
            'items': items,
            'ai_explanation': group_info.get('ai_explanation', '')
        }

        # Proje bilgilerini al
        project_info = self._get_project_info()

        # Dosya kaydetme dialogu
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in group_info['name'])
        default_filename = f"Metraj_Cetveli_{safe_name}.pdf"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "PDF Metraj Cetveli Kaydet",
            default_filename,
            "PDF Dosyaları (*.pdf)"
        )

        if not filepath:
            return

        # PDF oluştur
        try:
            exporter = PDFExporter()
            success = exporter.export_imalat_metraj_cetveli(
                filepath,
                project_info,
                imalat_group,
                signatories=self._get_signatories()
            )

            if success:
                QMessageBox.information(self, "Başarılı", f"PDF metraj cetveli oluşturuldu:\n{filepath}")
            else:
                QMessageBox.warning(self, "Hata", "PDF oluşturulamadı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"PDF oluşturma hatası:\n{str(e)}")

    def export_all_groups_pdf(self):
        """Tüm imalat grupları için birleşik PDF metraj cetveli oluşturur"""
        groups = self.db.get_quantity_groups()

        if not groups:
            QMessageBox.warning(self, "Uyarı", "Henüz imalat grubu bulunmuyor.")
            return

        # Tüm grupların verilerini hazırla
        imalat_groups = []
        for grp in groups:
            items = self.db.get_takeoffs_by_group(grp['id'])
            
            # Her item için poz bilgisi bul ve ekle
            for item in items:
                poz_info = self._find_poz_for_item(item)
                if poz_info:
                    item['poz_name'] = poz_info.get('poz_no', '')
                else:
                    item['poz_name'] = item.get('location', item.get('poz', ''))
            
            imalat_groups.append({
                'name': grp['name'],
                'unit': grp['unit'],
                'items': items,
                'ai_explanation': grp.get('ai_explanation', '')
            })

        # Proje bilgilerini al
        project_info = self._get_project_info()

        # Dosya kaydetme dialogu
        default_filename = f"Tum_Imalat_Metrajlari.pdf"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Tüm İmalatlar PDF Kaydet",
            default_filename,
            "PDF Dosyaları (*.pdf)"
        )

        if not filepath:
            return

        # PDF oluştur
        try:
            exporter = PDFExporter()
            success = exporter.export_tum_imalat_metrajlari(
                filepath,
                project_info,
                imalat_groups,
                signatories=self._get_signatories()
            )

            if success:
                QMessageBox.information(self, "Başarılı", f"Tüm imalat metrajları PDF'e aktarıldı:\n{filepath}")
            else:
                QMessageBox.warning(self, "Hata", "PDF oluşturulamadı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"PDF oluşturma hatası:\n{str(e)}")

    def _get_project_info(self):
        """Aktif proje bilgilerini veritabanından döndürür - Yaklaşık maliyet formatıyla uyumlu"""
        from datetime import datetime
        project_info = {
            'name': 'Yaklaşık Maliyet Projesi',
            'employer': '-',
            'contractor': '-',
            'location': '-',
            'date': datetime.now().strftime("%d.%m.%Y"),
            'institution': 'KAMU KURUMU',
        }

        # Ana pencereden cost_tab'a erişip aktif proje ID'sini al
        try:
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'cost_tab'):
                main_window = main_window.parent()

            if main_window and hasattr(main_window, 'cost_tab'):
                cost_tab = main_window.cost_tab
                if hasattr(cost_tab, 'current_project_id') and cost_tab.current_project_id:
                    # Veritabanından proje bilgilerini çek
                    project = self.db.get_project(cost_tab.current_project_id)
                    if project:
                        project_info['name'] = project.get('name', project_info['name'])
                        project_info['employer'] = project.get('employer', project.get('institution', project_info['employer'])) or '-'
                        project_info['contractor'] = project.get('contractor', project_info['contractor']) or '-'
                        project_info['location'] = project.get('location', project_info['location']) or '-'
                        project_info['institution'] = project.get('institution', project_info['institution']) or 'KAMU KURUMU'
                        
                        # Tarih formatını dönüştür (yyyy-MM-dd -> dd.MM.yyyy)
                        project_date = project.get('project_date', '')
                        if project_date:
                            try:
                                from datetime import datetime as dt
                                date_obj = dt.strptime(project_date, "%Y-%m-%d")
                                project_info['date'] = date_obj.strftime("%d.%m.%Y")
                            except:
                                pass
        except Exception as e:
            print(f"Proje bilgisi alınırken hata: {e}")

        # İşin adını ayarlardan al ve projeye ekle (Override)
        work_name = self.db.get_setting("work_name")
        if work_name:
            project_info['name'] = work_name

        return project_info

    def _get_signatories(self):
        """Veritabanından imzalayan bilgilerini al - Yaklaşık maliyet formatıyla uyumlu"""
        try:
            # Veritabanından imzalayan bilgilerini al
            signatories_list = self.db.get_signatories()

            if signatories_list:
                signatories = {
                    'hazirlayan': {},
                    'kontrol1': {},
                    'kontrol2': {},
                    'kontrol3': {},
                    'onaylayan': {}
                }

                for sig in signatories_list:
                    role = sig.get('role', '').lower()
                    sig_data = {
                        'full_name': sig.get('full_name', ''),
                        'title': sig.get('title', ''),
                        'date_text': ''
                    }

                    if 'hazirlayan' in role or 'hazırlayan' in role:
                        signatories['hazirlayan'] = sig_data
                    elif 'kontrol' in role and '1' in role:
                        signatories['kontrol1'] = sig_data
                    elif 'kontrol' in role and '2' in role:
                        signatories['kontrol2'] = sig_data
                    elif 'kontrol' in role and '3' in role:
                        signatories['kontrol3'] = sig_data
                    elif 'kontrol' in role:
                        # İlk boş kontrol alanına ekle
                        if not signatories['kontrol1']:
                            signatories['kontrol1'] = sig_data
                        elif not signatories['kontrol2']:
                            signatories['kontrol2'] = sig_data
                        elif not signatories['kontrol3']:
                            signatories['kontrol3'] = sig_data
                    elif 'onay' in role:
                        signatories['onaylayan'] = sig_data

                return signatories
        except:
            pass

        # Varsayılan boş imzalayan dict
        return None

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

    def format_ai_text(self, text, is_explanation=False):
        """AI metnini gelişmiş HTML formatına dönüştür"""
        if not text:
            if is_explanation:
                return "<i style='color: #999;'>Hesaplama detayları kaydedilmemiş.</i>"
            return "<i style='color: #999;'>Kayıt bulunamadı.</i>"

        if not is_explanation:
            # Basit formatlama (prompt için)
            return text.replace('\n', '<br>')

        # Gelişmiş formatlama (açıklama için)
        lines = text.split('\n')
        formatted_lines = []
        in_list = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if in_list:
                    formatted_lines.append('</ul>')
                    in_list = False
                formatted_lines.append('<br>')
                continue

            # Madde işareti ile başlayan satırlar (-, *, •)
            if stripped.startswith(('-', '*', '•')) and len(stripped) > 1:
                if not in_list:
                    formatted_lines.append('<ul style="margin: 5px 0; padding-left: 20px;">')
                    in_list = True
                item_text = stripped[1:].strip()
                item_text = self._format_line_content(item_text)
                formatted_lines.append(f'<li style="margin: 3px 0;">{item_text}</li>')
            # Numaralı liste (1., 2., vb.)
            elif re.match(r'^\d+[\.\)]\s*', stripped):
                if not in_list:
                    formatted_lines.append('<ol style="margin: 5px 0; padding-left: 20px;">')
                    in_list = True
                item_text = re.sub(r'^\d+[\.\)]\s*', '', stripped)
                item_text = self._format_line_content(item_text)
                formatted_lines.append(f'<li style="margin: 3px 0;">{item_text}</li>')
            # Başlık satırları (: ile biten)
            elif stripped.endswith(':') and len(stripped) < 60:
                if in_list:
                    formatted_lines.append('</ul>' if '</li>' in formatted_lines[-1] else '</ol>')
                    in_list = False
                formatted_lines.append(f'<p style="margin: 10px 0 5px 0;"><b style="color: #1565C0; font-size: 10.5pt;">{stripped}</b></p>')
            else:
                if in_list:
                    formatted_lines.append('</ul>' if '<ul' in ''.join(formatted_lines[-5:]) else '</ol>')
                    in_list = False
                formatted_line = self._format_line_content(stripped)
                formatted_lines.append(f'<p style="margin: 4px 0;">{formatted_line}</p>')

        if in_list:
            formatted_lines.append('</ul>')

        return ''.join(formatted_lines)

    def _format_line_content(self, text):
        """Satır içeriğini formatla - sayılar, birimler, formüller"""
        # Formülleri vurgula: L×B×H = 5×3×2 = 30 m³
        text = re.sub(
            r'([A-Za-zğüşıöçĞÜŞİÖÇ\d\.]+)\s*[×x\*]\s*([A-Za-zğüşıöçĞÜŞİÖÇ\d\.]+)(\s*[×x\*]\s*[A-Za-zğüşıöçĞÜŞİÖÇ\d\.]+)*',
            lambda m: f'<code style="background: #E3F2FD; padding: 2px 4px; border-radius: 3px; color: #1565C0;">{m.group(0).replace("*", "×").replace("x", "×")}</code>',
            text
        )

        # Eşitlik sonuçlarını vurgula: = 30
        text = re.sub(
            r'=\s*(\d+\.?\d*)',
            r'= <b style="color: #2E7D32;">\1</b>',
            text
        )

        # Sayı + birim kombinasyonlarını vurgula
        text = re.sub(
            r'(\d+\.?\d*)\s*(m[²³]|m2|m3|kg|ton|adet|sa|TL|cm|mm|lt|litre)',
            r'<span style="color: #D84315; font-weight: 500;">\1 \2</span>',
            text,
            flags=re.IGNORECASE
        )

        # Yüzde değerlerini vurgula
        text = re.sub(
            r'%\s*(\d+\.?\d*)',
            r'<span style="color: #7B1FA2; font-weight: 500;">%\1</span>',
            text
        )

        # Parantez içi açıklamaları italik yap
        text = re.sub(
            r'\(([^)]+)\)',
            r'<i style="color: #666;">(\1)</i>',
            text
        )

        return text

    def show_request_details(self):
        row = self.group_table.currentRow()
        if row < 0: return

        group_id = int(self.group_table.item(row, 0).text())
        group_name = self.group_table.item(row, 1).text()

        # Get extra details from DB (user_prompt, methodology, score)
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_prompt, methodology, score FROM quantity_groups WHERE id=?", (group_id,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            return

        user_prompt = result[0]
        methodology = result[1]
        group_score = result[2]

        # Varsayılan mesajlar
        default_prompt = "Kullanıcı isteği kaydedilmemiş (Eski sürüm verisi)."
        default_methodology = "Hesaplama detayları kaydedilmemiş (Eski sürüm verisi)."

        dialog = QDialog(self)
        dialog.setWindowTitle(f"🤖 AI Detayları - {group_name}")
        dialog.setMinimumSize(700, 550)

        layout = QVBoxLayout(dialog)

        # Splitter for prompt and methodology
        splitter = QSplitter(Qt.Vertical)

        # Top Panel: User Prompt
        prompt_widget = QWidget()
        prompt_layout = QVBoxLayout(prompt_widget)
        prompt_layout.setContentsMargins(0, 0, 0, 5)
        prompt_layout.addWidget(QLabel("<b style='font-size: 11pt;'>👤 Kullanıcı İsteği:</b>"))

        prompt_text = QTextEdit()
        prompt_text.setReadOnly(True)
        formatted_prompt = self.format_ai_text(user_prompt or default_prompt, is_explanation=False)
        prompt_text.setHtml(f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; line-height: 1.5; color: #333;">
                {formatted_prompt}
            </div>
        """)
        prompt_text.setStyleSheet("""
            QTextEdit {
                background-color: #FFF8E1;
                border: 1px solid #FFE082;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        prompt_layout.addWidget(prompt_text)
        splitter.addWidget(prompt_widget)

        # Bottom Panel: Methodology
        methodology_widget = QWidget()
        methodology_layout = QVBoxLayout(methodology_widget)
        methodology_layout.setContentsMargins(0, 5, 0, 0)
        methodology_layout.addWidget(QLabel("<b style='font-size: 11pt;'>🤖 AI Hesaplama Mantığı & Varsayımlar:</b>"))

        methodology_text = QTextEdit()
        methodology_text.setReadOnly(True)
        formatted_methodology = self.format_ai_text(methodology or default_methodology, is_explanation=True)
        methodology_text.setHtml(f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; line-height: 1.6; color: #333;">
                {formatted_methodology}
            </div>
        """)
        methodology_text.setStyleSheet("""
            QTextEdit {
                background-color: #E8F5E9;
                border: 1px solid #A5D6A7;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        methodology_layout.addWidget(methodology_text)
        splitter.addWidget(methodology_widget)

        layout.addWidget(splitter)

        # --- Scoring Section ---
        score_layout = QHBoxLayout()
        score_layout.addWidget(QLabel("<b>⭐ AI Cevap Puanı:</b>"))

        score_combo = QComboBox()
        score_combo.addItems([
            "Seçiniz...",
            "⭐ 1 - Kötü (Kullanılamaz)",
            "⭐⭐ 2 - Zayıf (Çok düzeltme gerekli)",
            "⭐⭐⭐ 3 - Orta (Düzeltmelerle kullanılabilir)",
            "⭐⭐⭐⭐ 4 - İyi (Az düzeltme gerekli)",
            "⭐⭐⭐⭐⭐ 5 - Mükemmel (Doğrudan kullanılabilir)"
        ])

        # Load current score
        if group_score is not None:
            try:
                score_val = int(group_score)
                if 1 <= score_val <= 5:
                    score_combo.setCurrentIndex(score_val)
            except:
                pass

        score_layout.addWidget(score_combo)

        save_score_btn = QPushButton("💾 Puanı Kaydet")
        save_score_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFC107;
                color: black;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #FFB300; }
        """)
        score_layout.addWidget(save_score_btn)

        layout.addLayout(score_layout)

        def save_score():
            idx = score_combo.currentIndex()
            if idx == 0:
                QMessageBox.warning(dialog, "Uyarı", "Lütfen bir puan seçin.")
                return

            score_val = idx
            self.db.update_quantity_group_score(group_id, score_val)
            QMessageBox.information(dialog, "Başarılı", "Puan kaydedildi.")

        save_score_btn.clicked.connect(save_score)

        # Close button
        btn_box = QDialogButtonBox(QDialogButtonBox.Close)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)

        dialog.exec_()

    def start_ai_takeoff(self):
        """2 Adımlı AI Metraj: Önce bileşenleri belirle, sonra metraj hesapla"""
        dialog = AIPromptDialog(
            self,
            "Yapay Zeka Metraj Asistanı",
            "İmalatı tarif edin (Örn: '10m x 5m x 0.5m betonarme temel', '100 metre U kanal' vb.):"
        )

        if dialog.exec_() != QDialog.Accepted:
            return

        text = dialog.get_text()
        if not text.strip():
            return

        self.last_ai_prompt_text = text

        # API ayarlarını al
        api_key = self.db.get_setting("openrouter_api_key")
        gemini_key = self.db.get_setting("gemini_api_key")

        if not api_key and not gemini_key:
            QMessageBox.warning(self, "Uyarı", "API Anahtarı eksik! OpenRouter veya Gemini API anahtarı gerekli.")
            return

        model = self.db.get_setting("openrouter_model") or "google/gemini-2.0-flash-exp:free"
        base_url = self.db.get_setting("openrouter_base_url") or "https://openrouter.ai/api/v1"
        gemini_model = self.db.get_setting("gemini_model") or "gemini-1.5-flash"
        provider = self.db.get_setting("ai_provider") or "OpenRouter"

        self.ai_btn.setEnabled(False)
        self.ai_btn.setText("🔍 Adım 1: İmalat analiz ediliyor...")

        # ADIM 1: İmalat bileşenlerini analiz et
        self.analyze_thread = AIAnalyzeComponentsThread(
            text, api_key, model, base_url, gemini_key, gemini_model, provider
        )
        self.analyze_thread.finished.connect(self.on_analysis_finished)
        self.analyze_thread.status_update.connect(lambda s: self.ai_btn.setText(s))
        self.analyze_thread.start()

    def on_analysis_finished(self, components_data, error):
        """Adım 1 tamamlandı - Bileşenleri göster ve onay al"""
        if error:
            self.ai_btn.setEnabled(True)
            self.ai_btn.setText("🤖 Yapay Zeka ile İmalat Ekle")
            dialog = ErrorDialog(self, "AI Analiz Hatası", error)
            dialog.exec_()
            return

        if not components_data or 'bilesenler' not in components_data:
            self.ai_btn.setEnabled(True)
            self.ai_btn.setText("🤖 Yapay Zeka ile İmalat Ekle")
            QMessageBox.warning(self, "Uyarı", "İmalat bileşenleri belirlenemedi!")
            return

        # Bileşen önizleme dialogunu göster
        self.ai_btn.setText("✅ Bileşenler belirlendi - Onay bekleniyor...")

        preview_dialog = ComponentPreviewDialog(self, components_data)
        if preview_dialog.exec_() != QDialog.Accepted:
            self.ai_btn.setEnabled(True)
            self.ai_btn.setText("🤖 Yapay Zeka ile İmalat Ekle")
            return

        # Seçilen bileşenleri al
        selected_components = preview_dialog.get_selected_components()
        if not selected_components:
            self.ai_btn.setEnabled(True)
            self.ai_btn.setText("🤖 Yapay Zeka ile İmalat Ekle")
            QMessageBox.warning(self, "Uyarı", "Hiç bileşen seçilmedi!")
            return

        # İmalat adını sakla
        self.current_imalat_adi = components_data.get('imalat_adi', 'İmalat')

        # ADIM 2: Seçilen bileşenler için metraj hesapla
        self.ai_btn.setText("📊 Adım 2: Metraj hesaplanıyor...")

        api_key = self.db.get_setting("openrouter_api_key")
        model = self.db.get_setting("openrouter_model") or "google/gemini-2.0-flash-exp:free"
        base_url = self.db.get_setting("openrouter_base_url") or "https://openrouter.ai/api/v1"
        gemini_key = self.db.get_setting("gemini_api_key")
        gemini_model = self.db.get_setting("gemini_model") or "gemini-1.5-flash"
        provider = self.db.get_setting("ai_provider") or "OpenRouter"

        self.takeoff_thread = AIComponentTakeoffThread(
            self.last_ai_prompt_text,
            self.current_imalat_adi,
            selected_components,
            api_key, model, base_url, gemini_key, gemini_model, provider
        )
        self.takeoff_thread.finished.connect(self.on_takeoff_finished)
        self.takeoff_thread.status_update.connect(lambda s: self.ai_btn.setText(s))
        self.takeoff_thread.start()

    def on_takeoff_finished(self, data, explanation, error):
        """Adım 2 tamamlandı - Metrajları kaydet"""
        self.ai_btn.setEnabled(True)
        self.ai_btn.setText("🤖 Yapay Zeka ile İmalat Ekle")

        if error:
            dialog = ErrorDialog(self, "AI Metraj Hatası", error)
            dialog.exec_()
            return

        if not data or 'groups' not in data:
            QMessageBox.warning(self, "Uyarı", "Metraj verisi çözümlenemedi!")
            return

        count = 0

        # Her grup için kaydet
        for grp in data['groups']:
            group_name = grp.get('group_name', self.current_imalat_adi)
            unit = grp.get('unit', '')

            # Grup oluştur (prompt ve açıklama ile)
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
        QMessageBox.information(
            self,
            "Tamamlandı",
            f"✅ {count} metraj kalemi eklendi.\n\n"
            f"📋 İmalat: {self.current_imalat_adi}\n\n"
            f"Hesaplama detaylarını görmek için gruba sağ tıklayınız."
        )

    # Eski metod (geriye uyumluluk için - opsiyonel olarak kullanılabilir)
    def start_ai_takeoff_legacy(self):
        """Eski tek adımlı AI metraj (geriye uyumluluk)"""
        dialog = AIPromptDialog(
            self,
            "Yapay Zeka Metraj Asistanı (Klasik)",
            "İmalatları tarif edin:"
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
        gemini_key = self.db.get_setting("gemini_api_key")
        gemini_model = self.db.get_setting("gemini_model") or "gemini-1.5-flash"
        provider = self.db.get_setting("ai_provider") or "OpenRouter"

        self.ai_btn.setEnabled(False)
        self.ai_btn.setText("🤖 Hesaplanıyor...")

        custom_prompt = self.db.get_setting("custom_metraj_prompt") or None

        self.ai_thread = AITakeoffThread(text, api_key, model, base_url, gemini_key, gemini_model, provider, custom_prompt)
        self.ai_thread.finished.connect(self.on_ai_finished_legacy)
        self.ai_thread.status_update.connect(lambda s: self.ai_btn.setText(s))
        self.ai_thread.start()

    def on_ai_finished_legacy(self, data, explanation, error):
        """Eski tek adımlı sonuç işleyici"""
        self.ai_btn.setEnabled(True)
        self.ai_btn.setText("🤖 Yapay Zeka ile İmalat Ekle")

        if error:
            dialog = ErrorDialog(self, "AI İşlem Hatası", error)
            dialog.exec_()
            return

        if not data or 'groups' not in data:
            QMessageBox.warning(self, "Uyarı", "Veri çözümlenemedi!")
            return

        count = 0

        for grp in data['groups']:
            group_name = grp.get('group_name', 'Yeni Grup')
            unit = grp.get('unit', '')
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
