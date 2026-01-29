
import os
import json
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from database import DatabaseManager

# --- Custom Tools ---

class ConstructionTools:
    
    @tool("Search PDF Database")
    def search_pdfs(query: str):
        """
        Search for construction items, unit prices, and descriptions in the local PDF/CSV database.
        Useful for finding similar items or checking current market rates.
        Input should be a search query string (e.g., "C25 Beton", "Duvar Örülmesi").
        Returns a list of finding items with their details.
        """
        # Note: In a real implementation with dependency on PyQt5, we might need a workaround.
        # Here we will try to access the DatabaseManager or a simplified search logic.
        # For now, let's use a direct DB search or simulate it if the full search engine isn't available in this context.
        # Ideally, we should reuse the logic from analysis_builder.py's extract_and_format_context
        # But for separation of concerns, let's do a basic DB text search if possible, or assume context is passed differently.
        
        # Fallback: Since the PDF search engine is complex and tied to PyQt memory in this app architecture,
        # we might rely on the 'context' passed to the agent initially. 
        # However, for a true tool, let's implement a basic SQLite search if keywords exist in 'quantity_takeoffs' or similar,
        # OR better, simply return a message saying "Please refer to the Context provided in the task description" if we can't easily access the in-memory search engine.
        
        # Let's try to search via DatabaseManager if we had a table for it.
        # Since we don't have a full text search table for PDF content in SQLite (it's in memory/JSON cache),
        # we will simulate this tool being 'active' but relying on the context injected by the main app.
        
        return f"Searching for '{query}'... (Note: In this specific implementation, relevant PDF data is injected into your context. Please use the 'PDF Bilgileri' section provided in your instructions.)"

    @tool("Calculate Transport Cost")
    def calculate_transport(distance_km: float, density: float, k_factor: float = 1.0, a_factor: float = 1.0):
        """
        Calculates transport cost using KGM (Karayolları) formulas.
        Args:
            distance_km: Distance in Kilometers.
            density: Material density (ton/m3).
            k_factor: Road condition factor (default 1.0).
            a_factor: Difficulty factor (default 1.0).
        Returns:
            Calculated cost per ton and per m3.
        """
        m = distance_km * 1000
        
        # Formula 07.005/K (< 10km)
        if m < 10000:
            f_ton = 1.25 * 0.00017 * k_factor * m * a_factor
        else:
            # Formula 07.006/K (> 10km)
            f_ton = 1.25 * k_factor * (0.0007 * m + 0.01) * a_factor
            
        f_m3 = f_ton * density
        
        return f"Distance: {distance_km}km. Cost: {f_ton:.2f} TL/ton, {f_m3:.2f} TL/m3"

# --- Crew Manager ---

class ConstructionCrewManager:
    def __init__(self, api_key, model_name="openai/gpt-4o", base_url="https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=0.2,
            default_headers={
                "HTTP-Referer": "https://approximate-cost-app", # Optional, for OpenRouter rankings
                "X-Title": "Approximate Cost App (CrewAI)"
            }
        )

    def run_analysis(self, description, unit, context_data="", nakliye_params=None):
        nakliye_params = nakliye_params or {}
        
        # 1. Define Agents
        
        # Researcher: Finds data
        researcher = Agent(
            role='Kıdemli İnşaat Araştırmacısı',
            goal='Verilen poz için en doğru malzeme ve fiyat verilerini bulmak.',
            backstory="""Sen deneyimli bir metraj mühendisisin. 
            Görevin, veritabanındaki (sana sağlanan kontekstteki) benzer pozları inceleyerek 
            yeni oluşturulacak pozun hangi bileşenlerden (çimento, kum, işçilik vb.) oluşması gerektiğini belirlemektir.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            # tools=[ConstructionTools.search_pdfs] # Optional, context is often enough
        )

        # Analyst: Creates the breakdown
        analyst = Agent(
            role='Birim Fiyat Analisti',
            goal='Poz analizini bileşenlerine ayırmak ve miktarlandırmak.',
            backstory="""Sen Çevre ve Şehircilik Bakanlığı formatlarına hakim bir analistsin.
            Araştırmacının bulduğu verileri kullanarak; birim fiyat analizini oluşturan 
            Malzeme, İşçilik, Makine ve Nakliye kalemlerini listelemeli ve miktarlarını (analiz normlarına uygun olarak) belirlemelisin.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

        # Auditor: Final check and JSON formatting
        auditor = Agent(
            role='Baş Denetçi ve Format Uzmanı',
            goal='Analizi matematiksel olarak doğrulamak ve JSON formatına çevirmek.',
            backstory="""Sen titiz bir denetçisin. Analistin hazırladığı taslağı kontrol edersin.
            Özellikle Nakliye hesaplarını KGM formüllerine göre doğrularsın.
            Son olarak, çıktıyı sistemin kullanabileceği kusursuz bir JSON formatına dönüştürürsün.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[ConstructionTools.calculate_transport]
        )

        # 2. Define Tasks
        
        task_research = Task(
            description=f"""
            Analiz Edilecek Poz: {description}
            Birim: {unit}
            
            MEVCUT veri bağlamını (aşağıda) kullanarak bu pozun yapım şartlarını ve olası girdi kalemlerini araştır.
            Hangi malzemeler (çimento, demir, vb.) ve hangi işçilikler gerekir?
            
            BAĞLAM:
            {context_data}
            """,
            agent=researcher,
            expected_output="Gerekli malzeme ve işçiliklerin listesi ve kısa açıklamaları."
        )

        task_analysis = Task(
            description=f"""
            Araştırmacının bulgularını kullanarak '{description}' pozu için detaylı analiz tablosu taslağı oluştur.
            Her bir kalemin (Malzeme/İşçilik) yaklaşık miktarını (Quantity) ve Rayiç No'sunu (biliyorsan) belirle.
            Nakliye kalemlerini de eklemeyi unutma (mesafe: {nakliye_params.get('mesafe', 20000)/1000} km).
            """,
            agent=analyst,
            expected_output="Miktarları belirlenmiş detaylı analiz bileşenleri listesi."
        )

        formula_info = f"""
            KGM Nakliye Parametreleri:
            Mesafe (M): {nakliye_params.get('mesafe', 20000)} metre
            K: {nakliye_params.get('k', 1.0)}
            A: {nakliye_params.get('a', 1.0)}
            Yoğunluklar: Kum={nakliye_params.get('yogunluk_kum')}, Demir={nakliye_params.get('yogunluk_demir')}, Beton={nakliye_params.get('yogunluk_beton')}
        """

        task_audit = Task(
            description=f"""
            Analistin taslağını al ve son kontrolleri yap.
            1. Nakliye hesaplarını şu parametrelerle kesinleştir: {formula_info}
            2. Tüm kalemlerin toplamını kontrol et.
            3. Sonucu SADECE aşağıdaki JSON formatında ver:
            
            {{
              "explanation": "Analiz yönteminin özeti...",
              "components": [
                  {{ "type": "Malzeme", "code": "...", "name": "...", "unit": "...", "quantity": 0.0, "unit_price": 0.0 }},
                  {{ "type": "Nakliye", "code": "...", "name": "...", "unit": "ton", "quantity": 0.0, "unit_price": 0.0 }}
              ]
            }}
            """,
            agent=auditor,
            expected_output="Final valid JSON string."
        )

        # 3. Create Crew
        crew = Crew(
            agents=[researcher, analyst, auditor],
            tasks=[task_research, task_analysis, task_audit],
            verbose=True,
            process=Process.sequential
        )

        result = crew.kickoff()
        return result

if __name__ == "__main__":
    # Test
    print("CrewAI Backend Test")
