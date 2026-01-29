# Approximate Cost Pro (Web)

İnşaat metraj ve yaklaşık maliyet hesaplama platformu. PDF ve CSV kaynaklarından veri ayıklar, AI destekli analizler yapar ve projelendirme sağlar.

## 🚀 Hızlı Başlatma

Uygulamanın hem backend (FastAPI) hem de frontend (Next.js) kısımlarını tek bir komutla başlatmak için:

```bash
python3 start_web.py
```

Bu komut:
- **Backend:** `http://localhost:8000`
- **Frontend:** `http://localhost:3000`
adreslerinde uygulamayı ayağa kaldıracaktır.

## 🛠️ Kurulum

### 1. Python Bağımlılıkları
```bash
pip install -r requirements.txt
```

### 2. Frontend Bağımlılıkları
```bash
cd web-app
npm install
```

## 🏗️ Mimari
- **Backend:** FastAPI (Python 3.10+)
- **Frontend:** Next.js 14, Tailwind CSS, TanStack Table
- **Veritabanı:** SQLite
- **AI:** OpenAI Assistants, Gemini, OpenRouter

---
*Not: Eski masaüstü sürümünü çalıştırmak için `python3 main.py` komutunu kullanabilirsiniz.*
