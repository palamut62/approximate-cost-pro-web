import os
import sys
from backend.services.ai_service import AIAnalysisService
from dotenv import load_dotenv
import logging

# Setup logging to console
logging.basicConfig(level=logging.DEBUG)

# Load env variables
load_dotenv()

def test_ai():
    print("Testing AI Service...")
    service = AIAnalysisService()
    
    # Simple test case
    description = "C25 hazır beton dökülmesi"
    unit = "m3"
    
    try:
        print("Sending request to OpenRouter...")
        # Reduce timeout for quick testing if possible, but keep it realistic
        result = service.generate_analysis(description, unit)
        print("✅ Success!")
        print(result)
    except Exception as e:
        print("\n❌ Failed!")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ai()
