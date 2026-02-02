import subprocess
import os
import sys
import signal
import time

def run_app():
    # Root directory
    root_dir = os.path.dirname(os.path.abspath(__file__))
    web_app_dir = os.path.join(root_dir, "web-app")
    
    print("🚀 Uygulama başlatılıyor...")

    # 1. Backend (FastAPI) başlat
    print("📡 Backend başlatılıyor (Port 8000)...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=root_dir
    )

    # 2. Frontend (Next.js) başlat
    print("💻 Frontend başlatılıyor (Port 3000)...")
    frontend_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=web_app_dir
    )

    def signal_handler(sig, frame):
        print("\n👋 Uygulama kapatılıyor...")
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    
    print("\n✅ Sistem aktif!")
    print("🔗 Frontend: http://localhost:3000")
    print("🔗 Backend: http://localhost:8000")
    print("⌨️  Durdurmak için Ctrl+C tuşlarına basın.\n")

    # Süreçleri açık tut
    while True:
        time.sleep(1)

if __name__ == "__main__":
    run_app()
