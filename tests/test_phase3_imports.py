
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

def test_phase3_imports():
    print("Testing Phase 3 Services...")
    
    try:
        from services.self_consistency_service import SelfConsistencyService
        print("✅ SelfConsistencyService imported.")
        
        from services.consensus_service import ConsensusAnalysisService
        print("✅ ConsensusAnalysisService imported.")
        
        from services.cot_service import ChainOfThoughtService
        print("✅ ChainOfThoughtService imported.")
        
        # Test Instantiation (Mock AI Service)
        class MockAIService:
            pass
            
        mock_ai = MockAIService()
        
        sc = SelfConsistencyService(mock_ai)
        ca = ConsensusAnalysisService(mock_ai)
        cot = ChainOfThoughtService()
        
        print("✅ All services instantiated successfully.")
        
    except Exception as e:
        print(f"❌ Error during Phase 3 verification: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_phase3_imports()
