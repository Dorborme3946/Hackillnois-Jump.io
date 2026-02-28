# JumpAI

AI-powered vertical jump analyzer. Upload a video, get your jump height, biomechanics scorecard (0–99), and a Claude-generated coaching report. Progress tracked over time via Supermemory.

**Stack:** React · FastAPI · YOLOv8 · Claude Sonnet · Supermemory · Modal (GPU)

---

## Quick Start (Local Dev)

### 1. Clone & configure

```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and SUPERMEMORY_API_KEY in .env
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
# → http://localhost:8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## Folder Structure

```
jumpai/
├── frontend/          # React 18 + Vite + Tailwind
├── backend/           # FastAPI app
│   ├── routers/       # API endpoints
│   ├── cv/            # YOLO pose, height calc, biomechanics
│   ├── ml/            # EliteJumpModel (PyTorch)
│   ├── scoring/       # 0–99 metric scoring
│   ├── ai/            # Claude Sonnet report generator
│   ├── memory/        # Supermemory client
│   ├── validators/    # Video constraint checking
│   └── db/            # Supabase client + migrations
├── modal_workers/     # GPU workers (YOLO inference)
├── ml_training/       # Offline elite model training
│   └── collect_data/  # YouTube scraper, labeler, augment
├── data/              # Elite clips, pose JSONs, gallery
└── docs/              # API reference, biomechanics research
```

---

## Environment Variables

See [.env.example](.env.example) for all required variables. Never commit `.env`.

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude Sonnet API key |
| `SUPERMEMORY_API_KEY` | Supermemory API key |
| `SUPABASE_URL` | Supabase project URL (optional for local dev) |
| `MODAL_TOKEN_ID` | Modal token (needed for GPU deploy) |

---

## Training the Elite Model

```bash
# 1. Download elite jump footage
cd ml_training/collect_data
python scraper.py --url "https://youtube.com/..." --label elite

# 2. Extract poses from clips (run pose_extractor on each clip)

# 3. Label the pose JSONs
python label_tool.py

# 4. Augment dataset
python augment.py --factor 3

# 5. Train
cd ..
python train.py --epochs 100

# 6. Export elite gallery
python export_gallery.py
```

---

## Deployment

- **Frontend:** Vercel (`vercel deploy` from `frontend/`)
- **Backend:** Railway (set env vars in Railway dashboard, auto-deploys from main)
- **GPU Workers:** Modal (`modal deploy modal_workers/app.py`)

---

## API

See [docs/API.md](docs/API.md) for full endpoint reference.

## Biomechanics

See [docs/BIOMECHANICS_RESEARCH.md](docs/BIOMECHANICS_RESEARCH.md) for metric methodology.
