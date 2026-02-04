import sqlite3
import json
from datetime import datetime
from pathlib import Path
from backend.utils.logger import get_db_logger

logger = get_db_logger()
base_logger = logger

class DatabaseManager:
    def __init__(self, db_path="data.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Veritabanı tablolarını oluştur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Projeler tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                employer TEXT,
                contractor TEXT,
                location TEXT,
                project_code TEXT,
                project_date TEXT,
                created_date TEXT,
                updated_date TEXT,
                status TEXT DEFAULT 'Active'
            )
        ''')

        # Mevcut tabloya yeni sütunlar ekle (migration)
        try:
            cursor.execute('ALTER TABLE projects ADD COLUMN employer TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE projects ADD COLUMN contractor TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE projects ADD COLUMN location TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE projects ADD COLUMN project_code TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE projects ADD COLUMN project_date TEXT')
        except:
            pass

        # Proje Kalemleri (Keşif Özeti)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                poz_no TEXT,
                description TEXT,
                unit TEXT,
                quantity REAL,
                unit_price REAL,
                total_price REAL,
                notes TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            )
        ''')

        # Özel Analizler / Yeni Pozlar
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poz_no TEXT UNIQUE,
                name TEXT,
                unit TEXT,
                total_price REAL,
                created_date TEXT,
                is_ai_generated BOOLEAN DEFAULT 0
            )
        ''')

        # Analiz Detayları (Malzeme/İşçilik)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER,
                type TEXT, -- Malzeme, İşçilik, Makine
                code TEXT,
                name TEXT,
                unit TEXT,
                quantity REAL,
                unit_price REAL,
                total_price REAL,
                FOREIGN KEY (analysis_id) REFERENCES custom_analyses (id) ON DELETE CASCADE
            )
        ''')

        # Ayarlar (API Key vb.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        # PDF/Analiz Veri Kaynakları
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pdf_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                file_name TEXT,
                source_type TEXT,  -- 'PDF' veya 'ANALIZ'
                file_hash TEXT,
                file_size INTEGER,
                added_date TEXT,
                last_checked TEXT,
                is_changed BOOLEAN DEFAULT 0
            )
        ''')

        # Proje İmalat Metrajları
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quantity_takeoffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT,
                similar_count REAL DEFAULT 1,
                length REAL,
                width REAL,
                height REAL,
                quantity REAL,
                unit TEXT,
                notes TEXT,
                created_date TEXT
            )
        ''')
        
        # Quantity Groups (İmalat Grupları)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quantity_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                unit TEXT,
                created_date TEXT
            )
        ''')

        # Migration: Add group_id to quantity_takeoffs if not exists
        try:
            cursor.execute('ALTER TABLE quantity_takeoffs ADD COLUMN group_id INTEGER REFERENCES quantity_groups(id) ON DELETE CASCADE')
        except:
            pass

        # Migration: Add user_prompt to quantity_groups if not exists
        try:
            cursor.execute('ALTER TABLE quantity_groups ADD COLUMN user_prompt TEXT')
        except:
            pass

        # Migration: Add methodology to quantity_groups if not exists
        try:
            cursor.execute('ALTER TABLE quantity_groups ADD COLUMN methodology TEXT')
        except:
            pass

        try:
            cursor.execute('ALTER TABLE quantity_groups ADD COLUMN score INTEGER DEFAULT 0')
        except:
            pass

        # Migration: Add score and ai_explanation to custom_analyses if not exists
        try:
            cursor.execute('ALTER TABLE custom_analyses ADD COLUMN score INTEGER DEFAULT 0')
        except:
            pass

        try:
            cursor.execute('ALTER TABLE custom_analyses ADD COLUMN ai_explanation TEXT')
        except:
            pass

        try:
            cursor.execute('ALTER TABLE custom_analyses ADD COLUMN user_prompt TEXT')
        except:
            pass

        # İmza Sahipleri Tablosu (Kontrol Eden ve Onaylayan)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signatories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                title TEXT,
                full_name TEXT,
                position TEXT,
                date_text TEXT,
                order_num INTEGER DEFAULT 0
            )
        ''')

        # Migration: Add date_text to signatories if not exists
        try:
            cursor.execute('ALTER TABLE signatories ADD COLUMN date_text TEXT')
        except:
            pass

        # Varsayılan imza sahiplerini ekle (eğer yoksa)
        cursor.execute('SELECT COUNT(*) FROM signatories')
        if cursor.fetchone()[0] == 0:
            default_signatories = [
                ('hazirlayan', '', '', 'Hazırlayan', '', 0),
                ('kontrol1', '', '', '1. Kontrol Eden', '', 1),
                ('kontrol2', '', '', '2. Kontrol Eden', '', 2),
                ('kontrol3', '', '', '3. Kontrol Eden', '', 3),
                ('onaylayan', '', '', 'Onaylayan Amir', '', 4),
            ]
            cursor.executemany('''
                INSERT INTO signatories (role, title, full_name, position, date_text, order_num)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', default_signatories)

        # AI Feedback/Düzeltme Tablosu - Kullanıcı düzeltmelerinden öğrenme
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_prompt TEXT NOT NULL,
                original_unit TEXT,
                correction_type TEXT,
                correction_description TEXT,
                correct_components TEXT,
                keywords TEXT,
                created_date TEXT,
                use_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        # User Rules / Öğrenilen Kurallar Tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_keywords TEXT, -- JSON list of keywords
                required_items TEXT,   -- JSON list of required components
                condition_text TEXT,   -- Human readable condition
                created_date TEXT,
                use_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        conn.commit()
        conn.close()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    # --- Project Methods ---
    def create_project(self, name, description="", employer="", contractor="", location="", project_code="", project_date=""):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute('''INSERT INTO projects
                          (name, description, employer, contractor, location, project_code, project_date, created_date, updated_date)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (name, description, employer, contractor, location, project_code, project_date, now, now))
        project_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return project_id

    def update_project(self, project_id, name=None, description=None, employer=None, contractor=None, location=None, project_code=None, project_date=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Mevcut veriyi al
        cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        current = cursor.fetchone()
        if not current:
            conn.close()
            return False

        columns = [desc[0] for desc in cursor.description]
        current_dict = dict(zip(columns, current))

        # Sadece verilen değerleri güncelle
        new_name = name if name is not None else current_dict.get('name', '')
        new_desc = description if description is not None else current_dict.get('description', '')
        new_employer = employer if employer is not None else current_dict.get('employer', '')
        new_contractor = contractor if contractor is not None else current_dict.get('contractor', '')
        new_location = location if location is not None else current_dict.get('location', '')
        new_code = project_code if project_code is not None else current_dict.get('project_code', '')
        new_date = project_date if project_date is not None else current_dict.get('project_date', '')

        cursor.execute('''UPDATE projects SET
                          name = ?, description = ?, employer = ?, contractor = ?,
                          location = ?, project_code = ?, project_date = ?, updated_date = ?
                          WHERE id = ?''',
                       (new_name, new_desc, new_employer, new_contractor, new_location, new_code, new_date, now, project_id))
        conn.commit()
        conn.close()
        return True

    def rename_project(self, project_id, new_name):
        """Sadece proje adını güncelle"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        cursor.execute('UPDATE projects SET name = ?, updated_date = ? WHERE id = ?', 
                       (new_name, now, project_id))
        
        row_count = cursor.rowcount
        conn.commit()
        conn.close()
        return row_count > 0

    def get_project(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        columns = [description[0] for description in cursor.description]
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(zip(columns, row))
        return None

    def clear_project_items(self, project_id):
        """Projedeki tüm kalemleri sil (maliyeti sıfırla)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM project_items WHERE project_id = ?', (project_id,))
        conn.commit()
        conn.close()

    def get_projects(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM projects ORDER BY updated_date DESC')
        columns = [description[0] for description in cursor.description]
        projects = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return projects
        
    def delete_project(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        conn.commit()
        conn.close()

    # --- Project Item Methods ---
    def add_project_item(self, project_id, poz_no, description, unit, quantity, unit_price):
        conn = self.get_connection()
        cursor = conn.cursor()
        total_price = quantity * unit_price
        cursor.execute('''
            INSERT INTO project_items (project_id, poz_no, description, unit, quantity, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (project_id, poz_no, description, unit, quantity, unit_price, total_price))
        conn.commit()
        conn.close()
        
    def get_project_items(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM project_items WHERE project_id = ?', (project_id,))
        columns = [description[0] for description in cursor.description]
        items = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return items

    def update_project_item(self, item_id, quantity=None, unit_price=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Mevcut veriyi al
        cursor.execute('SELECT quantity, unit_price FROM project_items WHERE id = ?', (item_id,))
        current = cursor.fetchone()
        if not current:
            conn.close()
            return False
            
        new_qty = quantity if quantity is not None else current[0]
        new_price = unit_price if unit_price is not None else current[1]
        new_total = new_qty * new_price
        
        cursor.execute('UPDATE project_items SET quantity = ?, unit_price = ?, total_price = ? WHERE id = ?',
                       (new_qty, new_price, new_total, item_id))
        conn.commit()
        conn.close()
        return True

    def delete_project_item(self, item_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM project_items WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()

    # --- Analysis Methods ---
    def save_analysis(self, poz_no, name, unit, components, is_ai=False):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Calculate total
        total = sum(c['total_price'] for c in components)
        # Apply 25% overhead (standard)
        total_with_overhead = total * 1.25
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        try:
            # Main analysis entry
            cursor.execute('''
                INSERT INTO custom_analyses (poz_no, name, unit, total_price, created_date, is_ai_generated)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (poz_no, name, unit, total_with_overhead, now, 1 if is_ai else 0))
            analysis_id = cursor.lastrowid
            
            # Components
            for comp in components:
                cursor.execute('''
                    INSERT INTO analysis_components (analysis_id, type, code, name, unit, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (analysis_id, comp['type'], comp['code'], comp['name'], comp['unit'], 
                      comp['quantity'], comp['unit_price'], comp['total_price']))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Analysis save error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
            
    def get_custom_analyses(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM custom_analyses ORDER BY created_date DESC')
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_analysis_by_poz_no(self, poz_no):
        """Poz numarasına göre analiz getir"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM custom_analyses WHERE poz_no = ?', (poz_no,))
        columns = [description[0] for description in cursor.description]
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(zip(columns, row))
        return None

    def get_analysis_components(self, analysis_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM analysis_components WHERE analysis_id = ?', (analysis_id,))
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results

    def delete_analysis(self, analysis_id):
        """Analizi ve (CASCADE sayesinde) bileşenlerini sil"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM custom_analyses WHERE id = ?', (analysis_id,))
        conn.commit()
        conn.close()

    def add_analysis_component(self, analysis_id, comp_type, code, name, unit, quantity, unit_price):
        """Analize yeni bileşen ekle"""
        conn = self.get_connection()
        cursor = conn.cursor()
        total_price = quantity * unit_price
        cursor.execute('''
            INSERT INTO analysis_components (analysis_id, type, code, name, unit, quantity, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (analysis_id, comp_type, code, name, unit, quantity, unit_price, total_price))
        component_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return component_id

    def update_analysis_component(self, component_id, comp_type=None, code=None, name=None, unit=None, quantity=None, unit_price=None):
        """Analiz bileşenini güncelle"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Mevcut veriyi al
        cursor.execute('SELECT * FROM analysis_components WHERE id = ?', (component_id,))
        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        current = dict(zip(columns, row))

        new_type = comp_type if comp_type is not None else current['type']
        new_code = code if code is not None else current['code']
        new_name = name if name is not None else current['name']
        new_unit = unit if unit is not None else current['unit']
        new_quantity = quantity if quantity is not None else current['quantity']
        new_unit_price = unit_price if unit_price is not None else current['unit_price']
        new_total = new_quantity * new_unit_price

        cursor.execute('''UPDATE analysis_components SET
                          type = ?, code = ?, name = ?, unit = ?, quantity = ?, unit_price = ?, total_price = ?
                          WHERE id = ?''',
                       (new_type, new_code, new_name, new_unit, new_quantity, new_unit_price, new_total, component_id))
        conn.commit()
        conn.close()
        return True

    def delete_analysis_component(self, component_id):
        """Analiz bileşenini sil"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM analysis_components WHERE id = ?', (component_id,))
        conn.commit()
        conn.close()

    def update_analysis_total(self, analysis_id):
        """Analiz toplam tutarını bileşenlerden hesapla ve güncelle"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Bileşenlerin toplamını hesapla
        cursor.execute('SELECT SUM(total_price) FROM analysis_components WHERE analysis_id = ?', (analysis_id,))
        result = cursor.fetchone()
        total = result[0] if result[0] else 0

        # %25 kâr ekle
        total_with_overhead = total * 1.25

        cursor.execute('UPDATE custom_analyses SET total_price = ? WHERE id = ?', (total_with_overhead, analysis_id))
        conn.commit()
        conn.close()
        return total_with_overhead

    def update_analysis_score(self, analysis_id, score):
        """Analiz puanını güncelle"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE custom_analyses SET score = ? WHERE id = ?', (score, analysis_id))
        conn.commit()
        conn.close()

    def update_analysis_ai_data(self, analysis_id, ai_explanation, user_prompt):
        """Analiz AI açıklaması ve kullanıcı promptunu güncelle"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE custom_analyses SET ai_explanation = ?, user_prompt = ? WHERE id = ?',
                       (ai_explanation, user_prompt, analysis_id))
        conn.commit()
        conn.close()

    def get_analysis_details(self, analysis_id):
        """Analiz detaylarını getir (score, ai_explanation, user_prompt dahil)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT score, ai_explanation, user_prompt FROM custom_analyses WHERE id = ?', (analysis_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {'score': result[0], 'ai_explanation': result[1], 'user_prompt': result[2]}
        return None

    # --- Settings Methods ---
    def get_setting(self, key):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def set_setting(self, key, value):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        conn.commit()
        conn.close()

    # --- PDF Source Methods ---
    def add_pdf_source(self, file_path, source_type):
        """Yeni PDF/Analiz kaynağı ekle"""
        import hashlib
        from pathlib import Path

        file_path = str(file_path)
        path_obj = Path(file_path)

        if not path_obj.exists():
            return None

        # Dosya hash'i hesapla
        file_hash = self._calculate_file_hash(file_path)
        file_size = path_obj.stat().st_size
        file_name = path_obj.name
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO pdf_sources (file_path, file_name, source_type, file_hash, file_size, added_date, last_checked)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (file_path, file_name, source_type, file_hash, file_size, now, now))
            source_id = cursor.lastrowid
            conn.commit()
            return source_id
        except Exception as e:
            logger.error(f"PDF source ekleme hatası: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()

    def _calculate_file_hash(self, file_path):
        """Dosyanın MD5 hash'ini hesapla"""
        import hashlib
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            logger.error(f"Error calculating hash for file: {file_path}", exc_info=True)
            return None

    def get_pdf_sources(self, source_type=None):
        """Tüm PDF kaynaklarını getir, opsiyonel olarak türe göre filtrele"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if source_type:
            cursor.execute('SELECT * FROM pdf_sources WHERE source_type = ? ORDER BY added_date DESC', (source_type,))
        else:
            cursor.execute('SELECT * FROM pdf_sources ORDER BY source_type, added_date DESC')

        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results

    def delete_pdf_source(self, source_id):
        """PDF kaynağını sil"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM pdf_sources WHERE id = ?', (source_id,))
        conn.commit()
        conn.close()

    def check_pdf_sources_for_changes(self):
        """Tüm PDF kaynaklarını kontrol et ve değişenleri işaretle"""
        from pathlib import Path

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM pdf_sources')
        columns = [description[0] for description in cursor.description]
        sources = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()

        changed_files = []
        missing_files = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        for source in sources:
            file_path = source['file_path']
            path_obj = Path(file_path)

            if not path_obj.exists():
                missing_files.append(source)
                continue

            current_hash = self._calculate_file_hash(file_path)
            if current_hash != source['file_hash']:
                changed_files.append(source)
                # Değişikliği işaretle
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE pdf_sources SET is_changed = 1, last_checked = ? WHERE id = ?
                ''', (now, source['id']))
                conn.commit()
                conn.close()
            else:
                # Değişiklik yok, sadece kontrol tarihini güncelle
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE pdf_sources SET is_changed = 0, last_checked = ? WHERE id = ?
                ''', (now, source['id']))
                conn.commit()
                conn.close()

        return {'changed': changed_files, 'missing': missing_files}

    def update_pdf_source_hash(self, source_id):
        """PDF kaynağının hash'ini güncelle (dosya güncellendikten sonra)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT file_path FROM pdf_sources WHERE id = ?', (source_id,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            return False

        file_path = result[0]
        new_hash = self._calculate_file_hash(file_path)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE pdf_sources SET file_hash = ?, is_changed = 0, last_checked = ? WHERE id = ?
        ''', (new_hash, now, source_id))
        conn.commit()
        conn.close()
        return True
        return True

        conn.commit()
        conn.close()
        return True

    def get_takeoffs_by_group(self, group_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM quantity_takeoffs WHERE group_id = ? ORDER BY id', (group_id,))
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results

    # --- Quantity Group Methods ---
    def add_quantity_group(self, name, unit, user_prompt="", methodology=""):
        """Yeni bir imalat grubu oluştur"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO quantity_groups (name, unit, created_date, user_prompt, methodology) VALUES (?, ?, datetime('now'), ?, ?)", 
                       (name, unit, user_prompt, methodology))
        group_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return group_id

    def update_quantity_group_score(self, group_id, score):
        """Grubun AI puanını güncelle"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE quantity_groups SET score = ? WHERE id = ?", (score, group_id))
        conn.commit()
        conn.close()

    def get_quantity_groups(self):
        """Tüm imalat gruplarını getir (En yeni en üstte)"""
        import sqlite3
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # id, name, unit, created_date, user_prompt, methodology, score
        cursor.execute("SELECT * FROM quantity_groups ORDER BY id DESC")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def delete_quantity_group(self, group_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        # Delete items first (though cascade might work if enabled)
        cursor.execute('DELETE FROM quantity_takeoffs WHERE group_id = ?', (group_id,))
        cursor.execute('DELETE FROM quantity_groups WHERE id = ?', (group_id,))
        conn.commit()
        conn.close()

    # --- Quantity Takeoff Methods ---
    def add_quantity_takeoff(self, description, similar_count, length, width, height, quantity, unit, notes, group_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        cursor.execute('''
            INSERT INTO quantity_takeoffs (description, similar_count, length, width, height, quantity, unit, notes, created_date, group_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (description, similar_count, length, width, height, quantity, unit, notes, now, group_id))
        
        takeoff_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return takeoff_id
        
    def get_quantity_takeoffs(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM quantity_takeoffs ORDER BY created_date DESC')
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_dashboard_stats(self):
        """Dashboard için özet istatistikleri getir"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # 1. Toplam Poz Sayısı (Project Items + Custom Analyses)
        cursor.execute("SELECT COUNT(*) FROM project_items")
        p_items = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM custom_analyses")
        c_items = cursor.fetchone()[0]
        stats['item_count'] = p_items + c_items
        
        # 2. Dosya Sayısı
        cursor.execute("SELECT COUNT(*) FROM pdf_sources")
        stats['file_count'] = cursor.fetchone()[0]
        
        # 3. Proje Sayısı
        cursor.execute("SELECT COUNT(*) FROM projects")
        stats['project_count'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
        
    def delete_quantity_takeoff(self, takeoff_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM quantity_takeoffs WHERE id = ?', (takeoff_id,))
        conn.commit()
        conn.close()
        
    def update_quantity_takeoff(self, takeoff_id, description, similar_count, length, width, height, quantity, unit, notes):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE quantity_takeoffs
            SET description = ?, similar_count = ?, length = ?, width = ?, height = ?, quantity = ?, unit = ?, notes = ?
            WHERE id = ?
        ''', (description, similar_count, length, width, height, quantity, unit, notes, takeoff_id))

        conn.commit()
        conn.close()

    # --- Signatory Methods (İmza Sahipleri) ---
    def get_signatories(self):
        """Tüm imza sahiplerini getir"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM signatories ORDER BY order_num')
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_signatory_by_role(self, role):
        """Belirli bir role göre imza sahibini getir"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM signatories WHERE role = ?', (role,))
        columns = [description[0] for description in cursor.description]
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(zip(columns, row))
        return None

    def update_signatory(self, role, title, full_name, position, date_text=""):
        """İmza sahibi bilgilerini güncelle"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE signatories
            SET title = ?, full_name = ?, position = ?, date_text = ?
            WHERE role = ?
        ''', (title, full_name, position, date_text, role))
        conn.commit()
        conn.close()

    def get_all_signatories_for_pdf(self):
        """PDF için tüm imza sahiplerini formatlanmış olarak getir"""
        signatories = self.get_signatories()
        result = {}
        for sig in signatories:
            result[sig['role']] = {
                'title': sig.get('title', ''),
                'full_name': sig.get('full_name', ''),
                'position': sig.get('position', ''),
                'date_text': sig.get('date_text', '')
            }
        return result

    # --- AI Feedback Methods (Kullanıcı Düzeltmelerinden Öğrenme) ---

    def save_ai_feedback(self, original_prompt: str, original_unit: str,
                         correction_type: str, correction_description: str,
                         correct_components: list, keywords: list = None):
        """
        Kullanıcının AI düzeltmesini kaydet.

        Args:
            original_prompt: Orijinal poz tanımı (örn: "beton santrali ile 1m3 taş duvar")
            original_unit: Orijinal birim (m3, m2 vb.)
            correction_type: Düzeltme tipi ('wrong_method', 'missing_item', 'wrong_price', 'wrong_quantity')
            correction_description: Kullanıcının açıklaması
            correct_components: Doğru bileşenler listesi (JSON)
            keywords: Anahtar kelimeler listesi
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Anahtar kelimeleri otomatik çıkar
        if not keywords:
            keywords = self._extract_keywords_from_prompt(original_prompt)

        cursor.execute('''
            INSERT INTO ai_feedback
            (original_prompt, original_unit, correction_type, correction_description,
             correct_components, keywords, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            original_prompt,
            original_unit,
            correction_type,
            correction_description,
            json.dumps(correct_components, ensure_ascii=False),
            json.dumps(keywords, ensure_ascii=False),
            now
        ))

        feedback_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return feedback_id

    def _extract_keywords_from_prompt(self, prompt: str) -> list:
        """Prompt'tan anahtar kelimeleri çıkar"""
        stop_words = {'ve', 'ile', 'için', 'bir', 'bu', 'de', 'da', 'den', 'dan',
                      'nin', 'nın', 'ın', 'in', 'yapılması', 'imalatı', 'işi'}
        words = prompt.lower().replace('/', ' ').replace('-', ' ').split()
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        return keywords

    def get_relevant_feedback(self, prompt: str, unit: str = None, limit: int = 5) -> list:
        """
        Verilen prompt için ilgili geçmiş düzeltmeleri getir.
        Anahtar kelime eşleşmesine göre sıralar.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM ai_feedback
            WHERE is_active = 1
            ORDER BY use_count DESC, created_date DESC
        ''')

        columns = [description[0] for description in cursor.description]
        all_feedback = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()

        if not all_feedback:
            return []

        # Prompt'tan anahtar kelimeler
        prompt_keywords = set(self._extract_keywords_from_prompt(prompt))

        # Benzerlik puanı hesapla
        scored_feedback = []
        for fb in all_feedback:
            fb_keywords = set(json.loads(fb.get('keywords', '[]')))

            # Kesişim puanı
            common = prompt_keywords & fb_keywords
            if common:
                score = len(common) / max(len(prompt_keywords), 1)

                # Birim bonusu
                if unit and fb.get('original_unit', '').lower() == unit.lower():
                    score += 0.2

                scored_feedback.append((score, fb))

        # En yüksek puanlıları döndür (keyword fallback — Vector DB primary)
        scored_feedback.sort(key=lambda x: x[0], reverse=True)
        return [fb for score, fb in scored_feedback[:limit] if score > 0.5]

    def increment_feedback_use_count(self, feedback_id: int):
        """Feedback kullanım sayısını artır"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE ai_feedback SET use_count = use_count + 1 WHERE id = ?', (feedback_id,))
        conn.commit()
        conn.close()

    def get_all_feedback(self) -> list:
        """Tüm feedback kayıtlarını getir"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM ai_feedback ORDER BY created_date DESC')
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results

    def delete_feedback(self, feedback_id: int):
        """Feedback kaydını sil"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ai_feedback WHERE id = ?', (feedback_id,))
        conn.commit()
        conn.close()

    def toggle_feedback_active(self, feedback_id: int, is_active: bool):
        """Feedback aktiflik durumunu değiştir"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE ai_feedback SET is_active = ? WHERE id = ?', (1 if is_active else 0, feedback_id))
        conn.commit()
        conn.close()

    # --- User Rules (Öğrenilen Kategori Kuralları) ---

    def save_user_rule(self, trigger_keywords: list, required_items: list, condition_text: str) -> int:
        """Otomatik çıkarılan kuralı kaydet. Aynı trigger varsa tekrar ekleme."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Duplicate kontrolü: aynı trigger_keywords + required_items kombinasyonu var mı?
        trigger_json = json.dumps(sorted(trigger_keywords), ensure_ascii=False)
        cursor.execute(
            'SELECT id FROM user_rules WHERE trigger_keywords = ? AND is_active = 1',
            (trigger_json,)
        )
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return existing[0]

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute('''
            INSERT INTO user_rules (trigger_keywords, required_items, condition_text, created_date)
            VALUES (?, ?, ?, ?)
        ''', (
            trigger_json,
            json.dumps(required_items, ensure_ascii=False),
            condition_text,
            now
        ))
        rule_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return rule_id

    def get_matching_rules(self, description: str) -> list:
        """Verilen açıklamayla eşleşen aktif kuralları getir."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user_rules WHERE is_active = 1')
        columns = [desc[0] for desc in cursor.description]
        all_rules = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()

        desc_lower = description.lower()
        matched = []
        for rule in all_rules:
            try:
                triggers = json.loads(rule.get('trigger_keywords', '[]'))
            except:
                continue
            # Tüm trigger kelimeleri açıklamada varsa eşleşme
            if all(kw.lower() in desc_lower for kw in triggers):
                try:
                    rule['required_items'] = json.loads(rule.get('required_items', '[]'))
                except:
                    rule['required_items'] = []
                matched.append(rule)

        return matched

    def get_all_rules(self) -> list:
        """Tüm kuralları listele."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user_rules ORDER BY created_date DESC')
        columns = [desc[0] for desc in cursor.description]
        rules = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        for rule in rules:
            try:
                rule['trigger_keywords'] = json.loads(rule.get('trigger_keywords', '[]'))
                rule['required_items'] = json.loads(rule.get('required_items', '[]'))
            except:
                pass
        return rules

    def delete_rule(self, rule_id: int):
        """Kuralı sil."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user_rules WHERE id = ?', (rule_id,))
        conn.commit()
        conn.close()
