
import time
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.services.local_pdf_service import get_local_pdf_service

def test_performance():
    service = get_local_pdf_service(force_new=True)
    
    # Test 1: Search for a POZ that is likely not in the PDF but in the CSV
    # This should trigger a full scan
    start_time = time.time()
    print("Testing slow search (not in index)...")
    res = service.get_description("NON_EXISTENT_POZ")
    end_time = time.time()
    print(f"Time taken for one slow search: {end_time - start_time:.2f}s")
    
    # Test 2: Search for the same POZ again
    # If not cached as 'not found', it will be slow again
    start_time = time.time()
    print("Testing second search (should be cached if fixed)...")
    res = service.get_description("NON_EXISTENT_POZ")
    end_time = time.time()
    print(f"Time taken for second search: {end_time - start_time:.2f}s")

if __name__ == "__main__":
    test_performance()
