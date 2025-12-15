import sqlite3
import json
from datetime import datetime
from pathlib import Path

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
