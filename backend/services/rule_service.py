import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from database import DatabaseManager

class RuleService:
    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager if db_manager else DatabaseManager()

    def add_rule(self, trigger_keywords: List[str], required_items: List[Dict], condition_text: str) -> int:
        """
        Yeni bir kural ekle.
        
        Args:
            trigger_keywords: Kuralın tetiklenmesi için gereken anahtar kelimeler
            required_items: Kural tetiklendiğinde olması gereken kalemler
            condition_text: İnsan tarafından okunabilir koşul açıklaması
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        cursor.execute('''
            INSERT INTO user_rules (trigger_keywords, required_items, condition_text, created_date)
            VALUES (?, ?, ?, ?)
        ''', (json.dumps(trigger_keywords, ensure_ascii=False), 
              json.dumps(required_items, ensure_ascii=False), 
              condition_text, 
              now))
        
        rule_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return rule_id

    def get_all_rules(self) -> List[Dict]:
        """Tüm aktif kuralları getir"""
        conn = self.db.get_connection()
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM user_rules WHERE is_active = 1')
        rules = cursor.fetchall()
        conn.close()
        
        # JSON alanları parse et
        for rule in rules:
            try:
                rule['trigger_keywords'] = json.loads(rule['trigger_keywords'])
                rule['required_items'] = json.loads(rule['required_items'])
            except:
                rule['trigger_keywords'] = []
                rule['required_items'] = []
                
        return rules

    def find_matching_rules(self, description: str) -> List[Dict]:
        """
        Verilen tanım için uygulanan kuralları bul.
        Basit anahtar kelime eşleşmesi kullanır (case-insensitive).
        """
        rules = self.get_all_rules()
        matches = []
        desc_lower = description.lower()
        
        for rule in rules:
            keywords = rule.get('trigger_keywords', [])
            if not keywords:
                continue
                
            # Tüm anahtar kelimeler tanımda geçiyor mu?
            # (Basit mantık: AND. İleride OR veya karmaşık mantık eklenebilir)
            if any(kw.lower() in desc_lower for kw in keywords):
                matches.append(rule)
                
        return matches

    def increment_usage(self, rule_id: int):
        """Kural kullanım sayısını artır"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE user_rules SET use_count = use_count + 1 WHERE id = ?', (rule_id,))
        conn.commit()
        conn.close()

    def delete_rule(self, rule_id: int):
        """Kuralı sil (soft delete)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE user_rules SET is_active = 0 WHERE id = ?', (rule_id,))
        conn.commit()
        conn.close()
