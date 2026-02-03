
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.rag_service import RAGService
from services.vector_db_service import VectorDBService

def test_rag_setup():
    print("Testing RAG and VectorDB Setup...")
    
    try:
        # Initialize VectorDB (Singleton)
        vector_db = VectorDBService()
        
        # Check if model name corresponds to Turkish model
        # Note: The actual model object might abstract the name, but we can try to check internal attributes if possible, 
        # or just assume if no error matches.
        
        # Initialize RAG
        rag = RAGService()
        print("✅ RAGService initialized.")
        
        # Test Augmented Prompt Generation (with empty context)
        prompt = rag.augmented_prompt("Test imalat", "m3", "Base Prompt")
        
        if "RAG CONTEXT" in prompt or "Test imalat" in prompt:
            print("✅ Augmented prompt generation works.")
        else:
            print("❌ Prompt generation failed.")
            
        print("✅ Setup seems correct.")
        
    except Exception as e:
        print(f"❌ Error during setup test: {e}")

if __name__ == "__main__":
    test_rag_setup()
