from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QLineEdit, QGroupBox, QTextEdit,
                             QMessageBox, QInputDialog, QProgressBar, QFormLayout, QDialog,
                             QPlainTextEdit, QDialogButtonBox, QComboBox, QScrollArea, QFrame,
                             QApplication)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from database import DatabaseManager
import json
import requests
import re


import openai
import time

class ErrorDialog(QDialog):
    """Kopyalanabilir hata mesajı gösteren dialog"""
    def __init__(self, parent=None, title="Hata", message=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(550, 350)
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

        # Bilgi notu
        info = QLabel("💡 Hata 503 (overloaded) ise, birkaç dakika bekleyip tekrar deneyin.")
        info.setStyleSheet("color: #666; font-size: 9pt;")
        info.setWordWrap(True)
        layout.addWidget(info)

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
    def __init__(self, parent=None, title="AI Asistan", label="Talep:", show_group_selector=False, db=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(550, 400)
        self.show_group_selector = show_group_selector
        self.db = db
        self.selected_group_id = None
        self.selected_group_details = None
        self.setup_ui(label)

    def setup_ui(self, label_text):
        layout = QVBoxLayout(self)

        # İmalat Grubu Seçici (opsiyonel)
        if self.show_group_selector and self.db:
            group_box = QGroupBox("📦 İmalat Grubu (Opsiyonel)")
            group_layout = QVBoxLayout()

            group_info = QLabel("Bir imalat grubu seçerseniz, o grubun metraj detayları AI'ya gönderilecektir.")
            group_info.setStyleSheet("color: #666; font-size: 9pt;")
            group_info.setWordWrap(True)
            group_layout.addWidget(group_info)

            self.group_combo = QComboBox()
            self.group_combo.addItem("-- Grup Seçilmedi (Genel Analiz) --", None)

            # Grupları yükle
            groups = self.db.get_quantity_groups()
            for grp in groups:
                self.group_combo.addItem(f"📁 {grp['name']} ({grp.get('unit', '')})", grp['id'])

            self.group_combo.currentIndexChanged.connect(self.on_group_changed)
            group_layout.addWidget(self.group_combo)

            # Metraj önizlemesi
            self.metraj_preview = QTextEdit()
            self.metraj_preview.setReadOnly(True)
            self.metraj_preview.setMaximumHeight(100)
            self.metraj_preview.setPlaceholderText("Grup seçildiğinde metraj detayları burada görünecek...")
            self.metraj_preview.setStyleSheet("""
                QTextEdit {
                    background-color: #F5F5F5;
                    border: 1px solid #DDD;
                    border-radius: 4px;
                    font-size: 9pt;
                }
            """)
            group_layout.addWidget(self.metraj_preview)

            group_box.setLayout(group_layout)
            layout.addWidget(group_box)

        layout.addWidget(QLabel(label_text))

        self.input_text = QPlainTextEdit()
        self.input_text.setPlaceholderText("Buraya detaylıca yazın...")
        self.input_text.setLineWrapMode(QPlainTextEdit.WidgetWidth) # Force wrap
        layout.addWidget(self.input_text)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def on_group_changed(self, index):
        """İmalat grubu değiştiğinde metraj detaylarını göster"""
        self.selected_group_id = self.group_combo.currentData()

        if not self.selected_group_id or not self.db:
            self.metraj_preview.clear()
            self.selected_group_details = None
            return

        # Grubun metraj detaylarını al
        takeoffs = self.db.get_takeoffs_by_group(self.selected_group_id)

        if not takeoffs:
            self.metraj_preview.setText("Bu grupta henüz metraj kaydı yok.")
            self.selected_group_details = None
            return

        # Metraj özeti oluştur
        preview_lines = []
        for t in takeoffs:
            line = f"• {t['description']}: {t['quantity']:.2f} {t['unit']}"
            if t.get('notes'):
                line += f" ({t['notes']})"
            preview_lines.append(line)

        self.metraj_preview.setText("\n".join(preview_lines))
        self.selected_group_details = takeoffs

    def get_text(self):
        return self.input_text.toPlainText()

    def get_selected_group_id(self):
        """Seçilen grup ID'sini döndür"""
        return self.selected_group_id

    def get_group_metraj_context(self):
        """Seçilen grubun metraj detaylarını AI context formatında döndür - SINIRLI"""
        if not self.selected_group_details:
            return ""

        # Grup adını al
        group_name = ""
        if self.show_group_selector and hasattr(self, 'group_combo'):
            group_name = self.group_combo.currentText().replace("📁 ", "").split(" (")[0]

        context_lines = [f"\n📦 Grup: {group_name}"]

        # Sadece ilk 10 metraj
        for t in self.selected_group_details[:10]:
            line = f"• {t['description'][:40]}: {t['quantity']:.2f} {t['unit']}"
            context_lines.append(line)

        result = "\n".join(context_lines)
        
        # Max 2000 karakter
        if len(result) > 2000:
            result = result[:2000]
        
        return result

class AIAnalysisThread(QThread):
    finished = pyqtSignal(list, str, str) # components, explanation, error
    status_update = pyqtSignal(str)

    def __init__(self, description, unit, api_key, model, base_url, context_data="", gemini_key=None, gemini_model=None, provider="OpenRouter", nakliye_params=None, custom_prompt=None, openai_api_key=None, assistant_id=None):
        super().__init__()
        self.description = description
        self.unit = unit
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.context_data = context_data
        self.gemini_key = gemini_key
        self.gemini_model = gemini_model
        self.provider = provider
        self.custom_prompt = custom_prompt
        self.nakliye_params = nakliye_params or {}
        self.openai_api_key = openai_api_key
        self.assistant_id = assistant_id
        
    def run(self):
        # Context'i tamamen devre dışı bırak - token limit aşımını önlemek için
        # Çok büyük veriler API'yi patlatıyor
        self.context_data = ""  # Context tamamen kapatıldı
        
        print(f"[DEBUG] Context devre dışı bırakıldı (token tasarrufu)")
        
        # Custom prompt çok büyükse kullanma
        if self.custom_prompt and len(self.custom_prompt) > 10000:
            print(f"[DEBUG] Custom prompt çok büyük ({len(self.custom_prompt)} karakter), varsayılan kullanılacak")
            self.custom_prompt = None
        
        # Nakliye parametrelerini al
        nakliye_mesafe = self.nakliye_params.get('mesafe', 20000)  # metre
        nakliye_k = self.nakliye_params.get('k', 1.0)
        nakliye_a = self.nakliye_params.get('a', 1.0)
        yogunluk_kum = self.nakliye_params.get('yogunluk_kum', 1.60)
        yogunluk_moloz = self.nakliye_params.get('yogunluk_moloz', 1.80)
        yogunluk_beton = self.nakliye_params.get('yogunluk_beton', 2.40)
        yogunluk_cimento = self.nakliye_params.get('yogunluk_cimento', 1.50)
        yogunluk_demir = self.nakliye_params.get('yogunluk_demir', 7.85)
        nakliye_mode = self.nakliye_params.get('mode', 'ai')

        # KGM Formül bilgisi
        nakliye_km = nakliye_mesafe / 1000  # km'ye çevir

        # Özel prompt varsa kullan, yoksa varsayılanı kullan
        if self.custom_prompt:
            try:
                prompt = self.custom_prompt.format(
                    description=self.description,
                    unit=self.unit,
                    context_data=self.context_data,
                    nakliye_mesafe=nakliye_mesafe,
                    nakliye_km=nakliye_km,
                    nakliye_k=nakliye_k,
                    nakliye_a=nakliye_a,
                    yogunluk_kum=yogunluk_kum,
                    yogunluk_moloz=yogunluk_moloz,
                    yogunluk_beton=yogunluk_beton,
                    yogunluk_cimento=yogunluk_cimento,
                    yogunluk_demir=yogunluk_demir
                )
            except KeyError as e:
                print(f"Prompt format hatası: {e}, varsayılan kullanılıyor")
                prompt = self._get_default_prompt(nakliye_mesafe, nakliye_km, nakliye_k, nakliye_a,
                                                   yogunluk_kum, yogunluk_moloz, yogunluk_beton,
                                                   yogunluk_cimento, yogunluk_demir)
        else:
            prompt = self._get_default_prompt(nakliye_mesafe, nakliye_km, nakliye_k, nakliye_a,
                                               yogunluk_kum, yogunluk_moloz, yogunluk_beton,
                                               yogunluk_cimento, yogunluk_demir)

        gemini_error = None
        openrouter_error = None
        openai_error = None
        crewai_error = None

        if self.provider == "CrewAI Agent Team":
            if self.api_key: # Reusing OpenRouter Key or OpenAI Key
                try:
                    self.status_update.emit("🕵️ CrewAI Ekibi Çalışıyor: Araştırmacı, Analist, Denetçi...")
                    self.call_crewai(self.context_data, nakliye_mesafe, nakliye_k, nakliye_a, yogunluk_kum, yogunluk_moloz, yogunluk_beton, yogunluk_cimento, yogunluk_demir)
                    return
                except Exception as e:
                     crewai_error = str(e)
                     self.status_update.emit(f"⚠️ CrewAI Hatası: {e}")
                     self.finished.emit([], "", f"CrewAI Hatası: {e}")
                     return
            else:
                self.finished.emit([], "", "CrewAI için bir API Anahtarı (OpenRouter/OpenAI) gerekli!")
                return

        if self.provider == "OpenAI Assistant":
            if self.openai_api_key and self.assistant_id:
                try:
                    self.status_update.emit("🤖 OpenAI Asistanı ile hesaplanıyor...")
                    self.call_openai_assistant()
                    return
                except Exception as e:
                     openai_error = str(e)
                     self.status_update.emit(f"⚠️ OpenAI Asistan hatası: {e}")
                     self.finished.emit([], "", f"OpenAI Asistan Hatası: {e}")
                     return
            else:
                self.finished.emit([], "", "OpenAI API Anahtarı veya Asistan ID eksik!")
                return

        if self.provider == "Google Gemini":
            # Birincil: Gemini
            if self.gemini_key:
                try:
                    self.status_update.emit("🤖 Gemini ile hesaplanıyor...")
                    self.call_gemini(prompt)
                    return  # Başarılı, çık
                except Exception as e:
                    gemini_error = str(e)
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
            self.finished.emit([], "", f"Tüm kaynaklar başarısız.\nGemini: {gemini_error}\nOpenRouter: {openrouter_error}")

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
            self.finished.emit([], "", f"Tüm kaynaklar başarısız.\nOpenRouter: {openrouter_error}\nGemini: {gemini_error}")

    def _get_default_prompt(self, nakliye_mesafe, nakliye_km, nakliye_k, nakliye_a,
                            yogunluk_kum, yogunluk_moloz, yogunluk_beton,
                            yogunluk_cimento, yogunluk_demir):
        """Varsayılan analiz promptunu döndür"""
        return f"""
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
           - Makine (varsa - vinç, beton pompası, vb.)
           - Nakliye (ZORUNLU - malzeme nakliyesi mutlaka hesaplanmalı)

        2. KGM 2025 NAKLİYE HESABI (Karayolları Genel Müdürlüğü Formülleri):
           KULLANILACAK PARAMETRELER:
           - Ortalama Taşıma Mesafesi (M): {nakliye_mesafe} metre ({nakliye_km:.1f} km)
           - Taşıma Katsayısı (K): {nakliye_k}
           - A Katsayısı (Taşıma Şartları): {nakliye_a}

           MALZEME YOĞUNLUKLARI (Y - ton/m³):
           - Kum, Çakıl, Stabilize, Kırmataş: {yogunluk_kum} ton/m³
           - Anroşman, Moloz Taş: {yogunluk_moloz} ton/m³
           - Beton, Prefabrik: {yogunluk_beton} ton/m³
           - Çimento: {yogunluk_cimento} ton/m³
           - Betonarme Demiri: {yogunluk_demir} ton/m³

           NAKLİYE FORMÜLÜ (07.005/K - 10.000 m'ye kadar):
           F = 1,25 × 0,00017 × K × M × Y × A  (m³ için)
           F = 1,25 × 0,00017 × K × M × A      (ton için)

           NAKLİYE FORMÜLÜ (07.006/K - 10.000 m'den fazla):
           F = 1,25 × K × (0,0007 × M + 0,01) × Y × A  (m³ için)
           F = 1,25 × K × (0,0007 × M + 0,01) × A      (ton için)

           ÖNEMLİ:
           - Her ağır malzeme (beton, çimento, demir, kum, çakıl) için nakliye kalemi AYRI SATIR olarak ekle
           - Nakliye birim fiyatını yukarıdaki formüle göre hesapla
           - Nakliye miktarı = Malzeme miktarı × Yoğunluk (ton cinsinden)
           - Nakliye tipi: "type": "Nakliye" olarak belirt
           - Nakliye kodu: "07.005/K" veya "07.006/K" kullan

        3. Miktarlar gerçekçi inşaat normlarına (analiz kitaplarına) dayanmalıdır.
        4. Birim fiyatlar 2024-2025 yılı ortalama piyasa rayiçleri (TL) olmalıdır.
        5. Çıktı SADECE geçerli bir JSON formatında olmalı.
        6. Lütfen JSON içindeki metin alanlarında çift tırnak (") kullanmaktan kaçının veya escape edin (\").

        JSON Formatı Şablonu:
        {{
          "explanation": "Bu analizi oluştururken ... mantığını kullandım. Nakliye hesabını KGM 2025 formülüne göre şu şekilde yaptım: F = 1,25 × {nakliye_k} × 0,00017 × {nakliye_mesafe} × Y × {nakliye_a} = ... TL/ton",
          "components": [
              {{ "type": "Malzeme", "code": "10.xxx", "name": "Malzeme Adı", "unit": "kg/m³/adet", "quantity": 0.0, "unit_price": 0.0 }},
              {{ "type": "İşçilik", "code": "01.xxx", "name": "İşçilik Adı", "unit": "sa", "quantity": 0.0, "unit_price": 0.0 }},
              {{ "type": "Makine", "code": "03.xxx", "name": "Makine Adı", "unit": "sa", "quantity": 0.0, "unit_price": 0.0 }},
              {{ "type": "Nakliye", "code": "07.005/K", "name": "Çimento Nakliyesi ({nakliye_km:.0f}km)", "unit": "ton", "quantity": 0.0, "unit_price": 0.0 }},
              {{ "type": "Nakliye", "code": "07.005/K", "name": "Demir Nakliyesi ({nakliye_km:.0f}km)", "unit": "ton", "quantity": 0.0, "unit_price": 0.0 }}
          ]
        }}

        Lütfen "explanation" kısmında neden bu malzemeleri ve miktarları seçtiğini, nakliye hesabını hangi formülle yaptığını detaylıca anlat.
        """


    def call_crewai(self, context_data, nakliye_mesafe, nakliye_k, nakliye_a, Y_kum, Y_moloz, Y_beton, Y_cimento, Y_demir):
        try:
            from crew_backend import ConstructionCrewManager
        except ImportError:
             raise Exception("CrewAI modülü bulunamadı! Lütfen 'pip install crewai langchain_openai' yapın.")

        # Prepare parameters for Crew
        nakliye_params = {
            'mesafe': nakliye_mesafe,
            'k': nakliye_k,
            'a': nakliye_a,
            'yogunluk_kum': Y_kum,
            'yogunluk_moloz': Y_moloz,
            'yogunluk_beton': Y_beton,
            'yogunluk_cimento': Y_cimento,
            'yogunluk_demir': Y_demir
        }

        # Initialize Crew Manager
        # We reuse the API Key provided. If provider is OpenRouter, base_url is set. 
        # CrewAI supports OpenAI compatible APIs.
        manager = ConstructionCrewManager(
            api_key=self.api_key,
            model_name=self.model,
            base_url=self.base_url
        )

        # Run Analysis
        result = manager.run_analysis(
            description=self.description,
            unit=self.unit,
            context_data=context_data,
            nakliye_params=nakliye_params
        )

        # CrewAI usually returns a string (final output of the last agent)
        # We expect JSON string from the Auditor agent
        
        # Check if result is a generic object or string
        content = str(result)
        
        self.process_response(content)


    def call_openai_assistant(self):
        client = openai.OpenAI(api_key=self.openai_api_key)
        
        # 1. Yeni bir sohbet (Thread) başlat
        thread = client.beta.threads.create()
        
        # Kullanıcı promptu
        user_prompt = f"Poz Tanımı: {self.description}\nBirim: {self.unit}\n\nLütfen detaylı analiz yap."
        if self.context_data:
            user_prompt += f"\n\nEK BİLGİ:\n{self.context_data}"

        # 2. Mesajı gönder
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_prompt
        )

        # 3. Asistanı çalıştır (Run)
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id,
            # Instructions override is optional, the assistant already has them
            # instructions="Lütfen çıktıları JSON formatında ver." 
        )

        # 4. Cevabı bekle (Polling)
        while run.status != "completed":
            if run.status in ["failed", "cancelled", "expired"]:
                raise Exception(f"Asistan çalışması başarısız oldu: {run.status}")
                
            time.sleep(1) # 1 saniye bekle
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        # 5. Mesajları al
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        
        # En son cevabı al (ilk mesaj en sonuncusudur)
        ai_response = messages.data[0].content[0].text.value
        
        self.process_response(ai_response)

    def call_openrouter(self, prompt):
        # Prompt boyutunu kontrol et ve sınırla
        MAX_PROMPT_CHARS = 50000  # ~12500 token
        print(f"[DEBUG] Prompt boyutu: {len(prompt)} karakter")
        
        if len(prompt) > MAX_PROMPT_CHARS:
            print(f"[DEBUG] Prompt çok büyük, {MAX_PROMPT_CHARS} karaktere kısaltılıyor...")
            prompt = prompt[:MAX_PROMPT_CHARS] + "\n\n[PROMPT KISILDI - SADECE JSON CEVAP VER]"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://yaklasikmaliyetpro.com",
            "X-Title": "Yaklasik Maliyet Pro"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful construction estimation assistant. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
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

        content = result['choices'][0]['message']['content']
        if not content:
            raise Exception("API içerik boş döndürdü")

        self.process_response(content)

    def call_gemini(self, prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
        
        final_prompt = "You are a helpful construction estimation assistant. Output valid JSON only.\n" + prompt
        
        data = {
            "contents": [{"parts": [{"text": final_prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code != 200:
             raise Exception(f"Gemini Hatası: {response.text}")
             
        result = response.json()
        if 'candidates' in result and result['candidates']:
            content = result['candidates'][0]['content']['parts'][0]['text']
            self.process_response(content)
        else:
            raise Exception("Gemini boş yanıt döndürdü.")

    def process_response(self, content):
        content = self.clean_json_string(content)

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            # JSON parse hatası - onarma dene
            repaired = self._repair_json(content)
            try:
                data = json.loads(repaired)
            except:
                raise Exception(f"JSON parse hatası: {str(e)}")

        # Handle formats
        if isinstance(data, list):
            components = data
            explanation = "Açıklama mevcut değil."
        else:
            components = data.get('components', [])
            explanation = data.get('explanation', "Açıklama yapılmadı.")

        # Calculate totals
        for comp in components:
            try:
                comp['total_price'] = float(comp.get('quantity', 0)) * float(comp.get('unit_price', 0))
            except:
                comp['total_price'] = 0

        self.finished.emit(components, explanation, "")

    def _repair_json(self, content):
        """Bozuk JSON'u onarmaya çalış"""
        # Trailing comma temizliği
        content = re.sub(r',\s*}', '}', content)
        content = re.sub(r',\s*]', ']', content)

        # Eksik virgül ekleme: "value" "key" -> "value", "key"
        # Bu pattern iki string arasında eksik virgülü yakalar
        content = re.sub(r'"\s*\n\s*"', '",\n"', content)
        content = re.sub(r'"\s+"', '", "', content)

        # Eksik virgül: } { veya ] [ arasında
        content = re.sub(r'}\s*{', '}, {', content)
        content = re.sub(r']\s*\[', '], [', content)

        # Eksik virgül: } "key" veya ] "value" arasında
        content = re.sub(r'}\s*"', '}, "', content)
        content = re.sub(r']\s*"', '], "', content)

        # Eksik virgül: number/true/false/null sonrası " karakteri
        content = re.sub(r'(\d)\s*\n\s*"', r'\1,\n"', content)
        content = re.sub(r'(true|false|null)\s*\n\s*"', r'\1,\n"', content)

        # Kesilmiş string'i kapat
        quote_count = content.count('"')
        if quote_count % 2 != 0:
            content = content.rstrip()
            if not content.endswith('"'):
                content += '"'

        # Eksik kapanış parantezlerini say ve ekle
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')

        # Trailing virgül varsa kaldır
        content = content.rstrip()
        if content.endswith(','):
            content = content[:-1]

        # Eksik kapanışları ekle
        content += ']' * max(0, open_brackets)
        content += '}' * max(0, open_braces)

        return content

    def clean_json_string(self, s):
        """Remove markdown code blocks from string and try to extract JSON"""
        s = s.strip()
        if s.startswith("```json"): s = s[7:]
        if s.startswith("```"): s = s[3:]
        if s.endswith("```"): s = s[:-3]
        try:
            match = re.search(r'\{.*\}', s.strip(), re.DOTALL)
            if match: return match.group(0)
        except: pass
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
        
        self.info_lbl = QLabel("Mode: OpenRouter AI")
        self.info_lbl.setStyleSheet("color: gray;")
        ai_layout.addWidget(self.info_lbl)
        
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

        clear_all_btn = QPushButton("🗑️ Tümünü Temizle")
        clear_all_btn.setStyleSheet("background-color: #FF5252; color: white;")
        clear_all_btn.clicked.connect(self.clear_all_rows)
        btn_layout.addWidget(clear_all_btn)
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
        save_btns_layout = QHBoxLayout()

        save_btn = QPushButton("💾 Analizi Veritabanına Kaydet")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 12px; font-weight: bold;")
        save_btn.clicked.connect(self.save_analysis)
        save_btns_layout.addWidget(save_btn)

        save_add_btn = QPushButton("💾 + 💰 Kaydet ve Projeye Ekle")
        save_add_btn.setStyleSheet("background-color: #f57f17; color: white; padding: 12px; font-weight: bold;")
        save_add_btn.clicked.connect(self.save_and_add_to_project)
        save_btns_layout.addWidget(save_add_btn)

        export_pdf_btn = QPushButton("📄 PDF Olarak Kaydet")
        export_pdf_btn.setStyleSheet("background-color: #1976D2; color: white; padding: 12px; font-weight: bold;")
        export_pdf_btn.clicked.connect(self.export_analysis_to_pdf)
        save_btns_layout.addWidget(export_pdf_btn)

        layout.addLayout(save_btns_layout)
        
        self.setLayout(layout)
        
        # Connect item change to recalc
        self.comp_table.itemChanged.connect(self.on_item_changed)

    def start_ai_generation(self):
        dialog = AIPromptDialog(
            self,
            "Yapay Zeka Analiz Asistanı",
            "Analiz talebinizi detaylıca yazın (Örn: 'C25 beton dökülmesi, nakliye ve kalıp dahil'):",
            show_group_selector=True,
            db=self.db
        )

        if dialog.exec_() != QDialog.Accepted:
             return

        text = dialog.get_text()

        if not text.strip():
            return

        desc = text.strip()
        self.desc_input.setText(desc) # Update UI

        # İmalat grubu metraj context'ini al
        group_metraj_context = dialog.get_group_metraj_context()
        self._selected_group_id = dialog.get_selected_group_id()
        
        unit = self.unit_input.text()
            
        # Get Settings
        api_key = self.db.get_setting("openrouter_api_key") 
        if not api_key:
             QMessageBox.warning(self, "Uyarı", "OpenRouter API Anahtarı bulunamadı! Lütfen Ayarlar menüsünden ekleyin.")
             return
             
        model = self.db.get_setting("openrouter_model") or "openai/gpt-4o"
        base_url = self.db.get_setting("openrouter_base_url") or "https://openrouter.ai/api/v1"
        
        # Gemini Settings (Failover)
        gemini_key = self.db.get_setting("gemini_api_key")
        gemini_model = self.db.get_setting("gemini_model") or "gemini-1.5-flash"
        
        provider = self.db.get_setting("ai_provider") or "OpenRouter"
        
        # OpenAI Assistant Settings
        openai_api_key = self.db.get_setting("openai_api_key")
        assistant_id = self.db.get_setting("openai_assistant_id")
        
        # Update UI Provider Label
        self.info_lbl.setText(f"Mode: {provider}")

        if provider == "OpenAI Assistant" and (not openai_api_key or not assistant_id):
             QMessageBox.warning(self, "Uyarı", "OpenAI Assistant modu için API Key ve Assistant ID gereklidir! Ayarlardan ekleyin.")
             return

        # KGM 2025 Nakliye Parametrelerini Al
        nakliye_mode = self.db.get_setting("nakliye_mode") or "AI'ya Bırak (Varsayılan değerler kullanılır)"
        is_ai_mode = 'Manuel' not in nakliye_mode

        # K katsayısını belirle (Türkçe formattan parse et)
        saved_k = self.db.get_setting("nakliye_k") or "1,00"
        k_value = self.parse_turkish_number(saved_k) or 1.0

        # AI modunda K katsayısını CSV'den otomatik çek
        if is_ai_mode and self.parent_app and hasattr(self.parent_app, 'csv_manager'):
            auto_k = self.get_k_coefficient_from_csv()
            if auto_k:
                k_value = auto_k
                print(f"K katsayısı CSV'den otomatik çekildi: {k_value}")

        nakliye_params = {
            'mode': 'manual' if not is_ai_mode else 'ai',
            'mesafe': int(self.db.get_setting("nakliye_mesafe") or 20000),
            'k': k_value,
            'a': float(self.db.get_setting("nakliye_a") or 1.0),
            'yogunluk_kum': float(self.db.get_setting("yogunluk_kum") or 1.60),
            'yogunluk_moloz': float(self.db.get_setting("yogunluk_moloz") or 1.80),
            'yogunluk_beton': float(self.db.get_setting("yogunluk_beton") or 2.40),
            'yogunluk_cimento': float(self.db.get_setting("yogunluk_cimento") or 1.50),
            'yogunluk_demir': float(self.db.get_setting("yogunluk_demir") or 7.85),
        }

        self.set_loading(True)

        # RAG Implementation: Extract keywords and search context
        context_text = self.extract_and_format_context(desc)

        # İmalat grubu metraj context'ini ekle (seçildiyse)
        if group_metraj_context:
            context_text += "\n" + group_metraj_context

        # Kullanıcı promptunu sakla (kayıt için)
        self._last_ai_prompt = desc

        # Özel prompt varsa al
        custom_prompt = self.db.get_setting("custom_analysis_prompt") or None

        self.thread = AIAnalysisThread(desc, unit, api_key, model, base_url, context_text, gemini_key, gemini_model, provider, nakliye_params, custom_prompt, openai_api_key, assistant_id)
        self.thread.finished.connect(self.on_ai_finished)
        self.thread.status_update.connect(lambda s: self.generate_btn.setText(s))
        self.thread.start()

    def extract_and_format_context(self, description):
        """Extract keywords from description and search in loaded PDFs - SINIRLI"""
        if not self.parent_app or not hasattr(self.parent_app, 'search_engine'):
            return ""

        # Simple keyword extraction
        keywords = [w.strip() for w in description.split() if len(w.strip()) > 3]
        
        found_items = []
        search_engine = self.parent_app.search_engine
        
        # Limit total context - DAHA DA AZALTILDI
        max_items = 5  # 10'dan 5'e
        
        for keyword in keywords[:3]:  # Sadece ilk 3 anahtar kelime
            if len(found_items) >= max_items:
                break
                
            for file_name, lines in search_engine.pdf_data.items():
                for line_data in lines:
                    text = line_data['text']
                    if keyword.lower() in text.lower():
                        if '|' in text and len(text) < 200:
                            found_items.append(text.strip()[:150])
                            if len(found_items) >= max_items:
                                break
                if len(found_items) >= max_items:
                    break
        
        if not found_items:
            context_str = ""
        else:
            context_str = "PDF Bilgileri:\n" + "\n".join(found_items) + "\n"

        # Quantity Takeoff - ÇOK SINIRLI
        takeoffs = self.db.get_quantity_takeoffs()
        if takeoffs:
            context_str += "\nMetrajlar:\n"
            for t in takeoffs[:10]:  # Sadece ilk 10
                line = f"- {t['description'][:30]}: {t['quantity']} {t['unit']}\n"
                context_str += line

        # Toplam context - DAHA DA SINIRLI
        max_chars = 4000  # 8000'den 4000'e
        if len(context_str) > max_chars:
            context_str = context_str[:max_chars]

        return context_str

    def get_k_coefficient_from_csv(self):
        """CSV verilerinden K katsayısını otomatik çek"""
        try:
            if not self.parent_app or not hasattr(self.parent_app, 'csv_manager'):
                return None

            poz_data = self.parent_app.csv_manager.poz_data
            if not poz_data:
                return None

            # Öncelikli arama: Tam poz numarası eşleşmesi
            priority_pozlar = ['10.110.1003', '02.017']

            for target_poz in priority_pozlar:
                if target_poz in poz_data:
                    poz_info = poz_data[target_poz]
                    unit_price = poz_info.get('unit_price', '')
                    if unit_price:
                        value = self.parse_turkish_number(unit_price)
                        if value and value > 0:
                            return value

            # İkincil arama: Poz numarasında içeren
            for poz_no, poz_info in poz_data.items():
                if any(term in poz_no for term in priority_pozlar):
                    unit_price = poz_info.get('unit_price', '')
                    if unit_price:
                        value = self.parse_turkish_number(unit_price)
                        if value and value > 0:
                            return value

            # Üçüncül arama: Açıklamada "motorlu araç taşıma katsayısı" geçen
            for poz_no, poz_info in poz_data.items():
                desc = poz_info.get('description', '').lower()
                if 'motorlu araç' in desc and 'taşıma katsayısı' in desc:
                    unit_price = poz_info.get('unit_price', '')
                    if unit_price:
                        value = self.parse_turkish_number(unit_price)
                        if value and value > 0:
                            return value

            return None

        except Exception as e:
            print(f"K katsayısı çekme hatası: {e}")
            return None

    def parse_turkish_number(self, value_str):
        """Türkçe sayı formatını parse et (1.750,00 -> 1750.00)"""
        try:
            if not value_str or str(value_str).lower() == 'nan':
                return None

            # String'e çevir ve temizle
            clean = str(value_str).strip().replace(' ', '').replace('TL', '')

            # Türkçe format: binlik ayraç nokta, ondalık virgül
            # Örnek: 1.750,00 -> 1750.00
            if ',' in clean:
                # Noktaları kaldır (binlik ayraç), virgülü noktaya çevir
                clean = clean.replace('.', '').replace(',', '.')

            return float(clean)
        except (ValueError, TypeError):
            return None
        
    def set_loading(self, loading):
        self.generate_btn.setEnabled(not loading)
        self.progress_bar.setVisible(loading)
        
    def on_ai_finished(self, components, explanation, error):
        self.set_loading(False)
        if error:
            # Kopyalanabilir hata dialogu göster
            dialog = ErrorDialog(self, "AI İşlem Hatası", error)
            dialog.exec_()
            return

        # Son AI açıklamasını sakla
        self.last_ai_explanation = explanation
        self.last_ai_prompt = getattr(self, '_last_ai_prompt', '')

        # Debug: Açıklama kontrolü
        if not explanation or explanation.strip() == "":
            print(f"[DEBUG] AI açıklaması boş geldi!")

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

        # Puanlama dialogu göster
        self.show_ai_rating_dialog(explanation)

    def format_ai_explanation(self, text):
        """AI açıklamasını gelişmiş HTML formatına dönüştür"""
        if not text:
            return "<i style='color: #999;'>Açıklama mevcut değil.</i>"

        import re
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
        import re

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

    def show_ai_rating_dialog(self, explanation):
        """AI sonucu için puanlama dialogu göster"""
        dialog = QDialog(self)
        dialog.setWindowTitle("🤖 Yapay Zeka Analiz Sonucu")
        dialog.setMinimumSize(650, 550)

        layout = QVBoxLayout(dialog)

        # Başlık
        header = QLabel("✅ Analiz Başarıyla Oluşturuldu!")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; color: #4CAF50; margin-bottom: 10px;")
        layout.addWidget(header)

        # AI Açıklaması
        explanation_group = QGroupBox("🔍 AI Açıklaması ve Hesaplama Mantığı")
        explanation_layout = QVBoxLayout(explanation_group)

        explanation_text = QTextEdit()
        formatted_explanation = self.format_ai_explanation(explanation)
        explanation_text.setHtml(f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; line-height: 1.6;">
                {formatted_explanation}
            </div>
        """)
        explanation_text.setReadOnly(True)
        explanation_text.setMinimumHeight(200)
        explanation_text.setStyleSheet("""
            QTextEdit {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 12px;
            }
        """)
        explanation_layout.addWidget(explanation_text)
        layout.addWidget(explanation_group)

        # Puanlama Bölümü
        rating_group = QGroupBox("⭐ AI Cevabını Puanla")
        rating_layout = QVBoxLayout(rating_group)

        rating_info = QLabel("Bu puanlama, yapay zekanın gelecekteki analizlerini iyileştirmemize yardımcı olur.")
        rating_info.setStyleSheet("color: #666; font-size: 9pt;")
        rating_layout.addWidget(rating_info)

        score_layout = QHBoxLayout()
        score_layout.addWidget(QLabel("<b>Puan:</b>"))

        self.ai_score_combo = QComboBox()
        self.ai_score_combo.addItems([
            "Seçiniz...",
            "⭐ 1 - Kötü (Kullanılamaz)",
            "⭐⭐ 2 - Zayıf (Çok düzeltme gerekli)",
            "⭐⭐⭐ 3 - Orta (Düzeltmelerle kullanılabilir)",
            "⭐⭐⭐⭐ 4 - İyi (Az düzeltme gerekli)",
            "⭐⭐⭐⭐⭐ 5 - Mükemmel (Doğrudan kullanılabilir)"
        ])
        self.ai_score_combo.setMinimumWidth(300)
        score_layout.addWidget(self.ai_score_combo)
        score_layout.addStretch()

        rating_layout.addLayout(score_layout)
        layout.addWidget(rating_group)

        # Bilgi notu
        note = QLabel("💡 Tabloyu kontrol edip gerekli düzeltmeleri yapın, ardından 'Analizi Kaydet' butonuna tıklayın.")
        note.setStyleSheet("color: #1976D2; font-weight: bold; margin-top: 10px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("Tamam")
        close_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px 30px;")
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        dialog.exec_()

        # Puanı kaydet (geçici olarak, analiz kaydedildiğinde DB'ye yazılacak)
        score_idx = self.ai_score_combo.currentIndex()
        self.pending_ai_score = score_idx if score_idx > 0 else None

    def add_empty_row(self):
        row = self.comp_table.rowCount()
        self.comp_table.insertRow(row)
        self.comp_table.setItem(row, 0, QTableWidgetItem("Malzeme"))
        self.comp_table.setItem(row, 4, QTableWidgetItem("0"))
        self.comp_table.setItem(row, 5, QTableWidgetItem("0"))

    def remove_row(self):
        self.comp_table.removeRow(self.comp_table.currentRow())
        self.recalc_totals()

    def clear_all_rows(self):
        """Tablodaki tüm satırları temizle"""
        if self.comp_table.rowCount() > 0:
            reply = QMessageBox.question(
                self, 
                "Onay", 
                "Tüm satırları silmek istediğinize emin misiniz?",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.comp_table.setRowCount(0)
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
        self.current_final_total = final_total # Store for later use
        
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
            # Analiz ID'sini al ve AI verilerini kaydet
            analysis = self.db.get_analysis_by_poz_no(poz_no)
            if analysis:
                analysis_id = analysis['id']

                # AI açıklaması ve prompt'u kaydet
                ai_explanation = getattr(self, 'last_ai_explanation', None)
                ai_prompt = getattr(self, 'last_ai_prompt', None)
                if ai_explanation or ai_prompt:
                    self.db.update_analysis_ai_data(analysis_id, ai_explanation, ai_prompt)

                # Puanı kaydet
                pending_score = getattr(self, 'pending_ai_score', None)
                if pending_score:
                    self.db.update_analysis_score(analysis_id, pending_score)

            QMessageBox.information(self, "Kayıt", "Analiz başarıyla kaydedildi!")

            # Değişkenleri temizle
            self.last_ai_explanation = None
            self.last_ai_prompt = None
            self.pending_ai_score = None

            return True
        else:
            QMessageBox.critical(self, "Hata", "Kayıt sırasında hata oluştu. Poz No benzersiz olmalıdır.")
            return False

    def save_and_add_to_project(self):
        """Save analysis and add to active project cost"""
        if self.save_analysis():
            # Get Price from label
            # Get Price from stored value or label
            price = 0.0
            if hasattr(self, 'current_final_total'):
                price = self.current_final_total
            else:
                try:
                    # Fallback parsing
                    txt = self.final_total_label.text()
                    val_str = txt.split(':')[1].replace(' TL', '').strip()
                    # Check format: 1,234.56 vs 1.234,56
                    if ',' in val_str and '.' in val_str:
                         if val_str.find('.') < val_str.find(','): # 1.234,56
                             price = float(val_str.replace('.', '').replace(',', '.'))
                         else: # 1,234.56
                             price = float(val_str.replace(',', ''))
                    elif ',' in val_str: # 123,45
                         price = float(val_str.replace(',', '.'))
                    else:
                         price = float(val_str)
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

    def export_analysis_to_pdf(self):
        """Birim fiyat analizini PDF olarak kaydet"""
        from PyQt5.QtWidgets import QFileDialog
        from datetime import datetime

        poz_no = self.poz_no_input.text().strip()
        description = self.desc_input.text().strip()

        if not poz_no or not description:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce Poz No ve Tanım alanlarını doldurun!")
            return

        if self.comp_table.rowCount() == 0:
            QMessageBox.warning(self, "Uyarı", "Analiz tablosunda bileşen bulunmuyor!")
            return

        # Dosya kaydetme dialogu
        default_name = f"Analiz_{poz_no.replace('.', '_').replace('/', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "PDF Olarak Kaydet",
            default_name,
            "PDF Dosyası (*.pdf)"
        )

        if not filepath:
            return

        try:
            from pdf_exporter import PDFExporter

            exporter = PDFExporter()

            # Analiz bilgilerini hazırla
            work_name = self.db.get_setting("work_name")
            
            analysis_info = {
                'poz_no': poz_no,
                'description': description,
                'unit': self.unit_input.text(),
                'ai_explanation': getattr(self, 'last_ai_explanation', ''),
                'work_name': work_name if work_name else ""
            }

            # Bileşenleri topla
            components = []
            for i in range(self.comp_table.rowCount()):
                try:
                    comp = {
                        'type': self.comp_table.item(i, 0).text() if self.comp_table.item(i, 0) else 'Malzeme',
                        'code': self.comp_table.item(i, 1).text() if self.comp_table.item(i, 1) else '',
                        'name': self.comp_table.item(i, 2).text() if self.comp_table.item(i, 2) else '',
                        'unit': self.comp_table.item(i, 3).text() if self.comp_table.item(i, 3) else '',
                        'quantity': float(self.comp_table.item(i, 4).text() or 0) if self.comp_table.item(i, 4) else 0,
                        'unit_price': float(self.comp_table.item(i, 5).text() or 0) if self.comp_table.item(i, 5) else 0
                    }
                    components.append(comp)
                except:
                    continue

            # PDF oluştur
            success = exporter.export_birim_fiyat_analizi(filepath, analysis_info, components)

            if success:
                QMessageBox.information(self, "Başarılı", f"PDF başarıyla kaydedildi:\n{filepath}")

                # PDF'i aç
                import os
                os.startfile(filepath)
            else:
                QMessageBox.critical(self, "Hata", "PDF oluşturulurken bir hata oluştu!")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"PDF oluşturma hatası:\n{str(e)}")
