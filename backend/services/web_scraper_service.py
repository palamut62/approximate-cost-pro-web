
import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import time
import random
import re

class WebScraperService:
    """Poz teknik tariflerini webden çeken ve önbelleğe alan servis"""
    
    def __init__(self, cache_file="poz_descriptions_cache.json"):
        # Path düzeltmesi: backend/PDF klasörü
        self.cache_path = Path(__file__).parent.parent / "PDF" / cache_file
        # Cache klasörünü oluştur
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.base_url = "https://www.birimfiyat.net"
        
        # Firecrawl Config
        import os
        self.firecrawl_key = os.getenv("FIRECRAWL_API_KEY") # .env'den oku
        self.firecrawl_url = "https://api.firecrawl.dev/v1/scrape"
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        self.cache = self._load_cache()

    def _load_cache(self):
        """Önbelleği yükle"""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[CACHE] Error loading cache: {e}")
        return {}
        
    def _call_firecrawl(self, url: str) -> dict:
        """Firecrawl API çağrısı"""
        if not self.firecrawl_key:
            print("[FIRECRAWL] API Key eksik!")
            return None
            
        try:
            headers = {
                "Authorization": f"Bearer {self.firecrawl_key}",
                "Content-Type": "application/json"
            }
            data = {
                "url": url,
                "formats": ["markdown"],
                "onlyMainContent": True
            }
            
            # 30 saniye timeout (render sürebilir)
            response = requests.post(self.firecrawl_url, headers=headers, json=data, timeout=45)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    return result.get("data", {})
            
            print(f"[FIRECRAWL] Error: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            print(f"[FIRECRAWL] Request Exception: {e}")
            return None

    def _save_cache(self):
        """Önbelleği kaydet"""
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[CACHE] Error saving cache: {e}")

    def get_description(self, poz_no: str) -> str:
        poz_no = poz_no.strip()
        if poz_no in self.cache:
            return self.cache[poz_no]
            
        print(f"[SCRAPER] {poz_no} için web araması başlatılıyor (Firecrawl)...")
        
        if self.firecrawl_key:
            description = self._scrape_with_firecrawl(poz_no)
        else:
            description = self._scrape_from_web_legacy(poz_no)
        
        # Her durumda kaydet
        self.cache[poz_no] = description if description else ""
        self._save_cache()
        return description
        
    def _scrape_with_firecrawl(self, poz_no: str) -> str:
        """Firecrawl kullanarak JS renderlı sayfadan veri çeker"""
        try:
            # 1. Arama Sayfasını Tara
            search_url = f"{self.base_url}/site-ici-arama?sitedeArama={poz_no}"
            print(f"[FIRECRAWL] Arama sayfası taranıyor: {search_url}")
            
            search_result = self._call_firecrawl(search_url)
            if not search_result: return ""
            
            markdown = search_result.get("markdown", "")
            
            # Markdown içinden linki bul
            # Format: [Link Text](https://www.birimfiyat.net/poz/...)
            # Regex: `\[.*?\]\((https://www\.birimfiyat\.net/.*?)\)`
            
            lines = markdown.split('\n')
            target_url = None
            
            for line in lines:
                if poz_no in line and ('birimfiyat.net' in line or '(' in line):
                    # URL çıkarma
                    url_match = re.search(r'\((https?://www\.birimfiyat\.net/[^)]+)\)', line)
                    if url_match:
                        url = url_match.group(1)
                        if 'site-ici-arama' not in url and len(url) > 35:
                            target_url = url
                            break
            
            if not target_url:
                # Fallback: Belki direkt metin içinde url vardır
                print(f"[FIRECRAWL] Markdown içinde link bulunamadı. İçerik özeti: {markdown[:200]}")
                return ""
                
            print(f"[FIRECRAWL] Hedef link bulundu: {target_url}")
            
            # 2. Detay Sayfasını Tara
            detail_result = self._call_firecrawl(target_url)
            if not detail_result: return ""
            
            detail_md = detail_result.get("markdown", "")
            
            # Metni temizle (Tarifi kısmını al)
            match = re.search(r'(Tarifi|Yapım Şartları|Kapsamı)[:\s]+(.*?)(?=(Analizi|Not|Ölçü)|$)', detail_md, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(2).strip()
            
            return detail_md[:1500] # Fallback (ilk 1500 karakter)

        except Exception as e:
            print(f"[FIRECRAWL] Process Error: {e}")
            return ""

    def _scrape_from_web_legacy(self, poz_no: str) -> str:
        """Eski legacy requests yöntemi (Bot korumasına takılabilir)"""
        try:
            # 1. Arama yap (/site-ici-arama?sitedeArama=...)
            search_url = f"{self.base_url}/site-ici-arama"
            params = {'sitedeArama': poz_no}
            
            response = requests.get(search_url, params=params, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                print(f"[SCRAPER] Search HTTP Error: {response.status_code}")
                return ""
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Sonuç linkini bul
            # Tahmini yapı: <div class="gs-title"><a href="...">
            # Aslında birimfiyat.net sonucu Google Custom Search gibi dönebilir mi?
            # Veya kendi listesi: <div class="arama-sonuc-item"><a href="...">
            
            result_link = None
            # Tüm linkleri tara ve içinde poz no geçen ve 'poz/' veya slug içeren linki al
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.text
                
                # Poz numarası linkte veya metinde geçiyor mu?
                if poz_no in href or poz_no in text:
                    # ve link detay sayfası gibi duruyor mu? (dizin değil)
                    # birimfiyat.net linkleri genelde uzundur
                    if len(href) > 30 and 'site-ici-arama' not in href:
                        result_link = href if href.startswith('http') else self.base_url + href
                        break
            
            if not result_link:
                print(f"[SCRAPER] {poz_no} için sonuç linki bulunamadı. Sayfa yapısı değişmiş olabilir.")
                return ""
                
            print(f"[SCRAPER] Detay sayfasına gidiliyor: {result_link}")
            
            # Detay sayfasına git
            detail_response = requests.get(result_link, headers=self.headers, timeout=10)
            if detail_response.status_code != 200:
                return ""
                
            detail_soup = BeautifulSoup(detail_response.content, 'html.parser')
            
            # Teknik tarifi bul
            # Genelde "Poz Tarifi", "Yapım Şartları", "Tarif" başlıkları altında olur.
            # Metni temizle
            
            content_div = detail_soup.find('div', class_=re.compile(r'(content|detail|aciklama|description)'))
            
            text = ""
            if content_div:
                text = content_div.get_text(separator=' ', strip=True)
            else:
                # Body içindeki en uzun metin bloğunu bul?
                text = detail_soup.body.get_text(separator=' ', strip=True)
            
            # Metni temizle ve kısalt
            match = re.search(r'(Tarifi|Yapım Şartları|Kapsamı)[:\s]+(.*?)(?=(Analizi|Not|Ölçü)|$)', text, re.IGNORECASE | re.DOTALL)
            if match:
                description = match.group(2).strip()
            else:
                description = text[:1000] # Fallback
                
            print(f"[SCRAPER] İçerik çekildi ({len(description)} karakter)")
            return description

        except Exception as e:
            print(f"[SCRAPER] Hata: {e}")
            return ""

# Singleton
_scraper_service = None

def get_scraper_service():
    global _scraper_service
    if _scraper_service is None:
        _scraper_service = WebScraperService()
    return _scraper_service
