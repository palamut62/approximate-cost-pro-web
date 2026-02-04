
import os
import json
import logging
from pathlib import Path
import re
import csv
import zipfile
import glob

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ColabVectorDB")

def install_dependencies():
    """Install minimal dependencies for Vector DB generation"""
    logger.info("Installing dependencies...")
    os.system("pip install chromadb sentence-transformers pandas tqdm")

class SimpleCSVLoader:
    def __init__(self, data_folder):
        self.data_folder = Path(data_folder)
        self.poz_data = {}

    def run(self):
        # Scan CSVs in ANALIZ and PDF folders
        for csv_path in glob.glob(str(self.data_folder / "**/*.csv"), recursive=True):
            try:
                self._load_csv(csv_path)
            except Exception as e:
                logger.error(f"Error loading {csv_path}: {e}")
        return self.poz_data

    def _load_csv(self, csv_path):
        import pandas as pd
        df = pd.read_csv(csv_path, encoding='utf-8-sig') # Handle BOM
        
        # Check required columns (Loose check)
        # Adapt keys based on backend logic
        key_map = {
            'Poz No': 'poz_no',
            'Açıklama': 'description', 
            'Birim': 'unit',
            'Kurum': 'institution',
            'Birim Fiyatı': 'unit_price'
        }
        
        for _, row in df.iterrows():
            poz_info = {}
            for csv_key, model_key in key_map.items():
                if csv_key in row:
                    poz_info[model_key] = str(row[csv_key]).strip()
            
            # Fallback for price
            if 'unit_price' not in poz_info:
                 for cola in row.index:
                     if 'Fiyat' in str(cola):
                         poz_info['unit_price'] = str(row[cola]).strip()
                         break
            
            # Fallback for poz_no
            if 'poz_no' not in poz_info and 'Poz No' in row:
                 poz_info['poz_no'] = str(row['Poz No']).strip()

            if 'poz_no' in poz_info:
                self.poz_data[poz_info['poz_no']] = poz_info

def generate_vector_db():
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error("Dependencies not found. Run install_dependencies() first.")
        return

    # Check for GPU
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")

    # Paths
    base_dir = Path("content") if os.path.exists("content") else Path(".")
    data_dir = base_dir / "data" # Unzipped data location
    persist_dir = base_dir / "chroma_db"
    
    # 1. Load Data
    logger.info("Loading Data...")
    loader = SimpleCSVLoader(data_dir)
    poz_data = loader.run()
    logger.info(f"Loaded {len(poz_data)} items.")

    if not poz_data:
        logger.warning("No data found! Make sure you uploaded 'data.zip' containing CSVs.")
        return

    # 2. Initialize ChromaDB
    logger.info("Initializing Vector DB...")
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(
        name="poz_data_collection",
        metadata={"hnsw:space": "cosine"}
    )

    # 3. Model
    logger.info(f"Loading Model (Device: {device})...")
    model = SentenceTransformer('emrecan/bert-base-turkish-cased-mean-nli-stsb-tr', device=device)

    # 4. Ingest (Batch Processing)
    batch_size = 500 # GPU usually handles larger batches well, but let's be safe
    items = list(poz_data.values())
    total_batches = (len(items) + batch_size - 1) // batch_size

    logger.info(f"Starting Ingestion ({len(items)} items in {total_batches} batches)...")

    ids = []
    documents = []
    metadatas = []

    for i, poz in enumerate(items):
        code = poz.get('poz_no')
        if not code: continue
        
        desc = poz.get('description', '')
        doc_text = f"{code} {desc}"
        
        meta = {
            "code": code,
            "unit": poz.get('unit', ''),
            "price": str(poz.get('unit_price', '0')),
            "description": desc
        }

        ids.append(code)
        documents.append(doc_text)
        metadatas.append(meta)

        if len(ids) >= batch_size or i == len(items) - 1:
            try:
                embeddings = model.encode(documents).tolist()
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
                if (i // batch_size) % 5 == 0:
                     logger.info(f"Batch {i // batch_size + 1}/{total_batches} done.")
            except Exception as e:
                logger.error(f"Batch error: {e}")
            
            ids = []
            documents = []
            metadatas = []

    logger.info("Ingestion Complete!")
    return persist_dir

def zip_directory(folder_path, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                zipf.write(os.path.join(root, file), 
                           os.path.relpath(os.path.join(root, file), 
                           os.path.join(folder_path, '..')))

if __name__ == "__main__":
    # --- Instructions ---
    # 1. Upload 'data.zip' (containing your ANALIZ and PDF folders with CSVs) to Colab.
    # 2. Run this script.
    
    print("--- Approximate Cost Vector DB Generator ---")
    
    # Auto-extract data.zip if exists
    if os.path.exists("data.zip"):
        print("Extracting data.zip...")
        with zipfile.ZipFile("data.zip", 'r') as zip_ref:
            zip_ref.extractall("data")
    
    install_dependencies()
    output_dir = generate_vector_db()
    
    if output_dir:
        print("Zipping output...")
        zip_directory(output_dir, "chroma_db_output.zip")
        print("Done! Download 'chroma_db_output.zip' and replace your local 'chroma_db' folder.")
