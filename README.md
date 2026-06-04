# ScreenTextOrganizer
Local screenshot OCR & text organizer

Local web tool for reviewing saved screenshots, book excerpts, interview-question images, and other image-based notes.

## Workflow

1. Scan an image folder.
2. Generate thumbnails and store metadata in SQLite.
3. Run OCR to extract text: PaddleOCR first, RapidOCR fallback, Ollama vision fallback when available.
4. Run local rule analysis, optionally enhanced by Ollama.
5. Review items in a browser table.
6. Copy text, edit OCR output, keep, mark for review, or move source images to the Windows recycle bin.
7. Export JSON or CSV.

## Project Layout

- `backend/` FastAPI backend and SQLite storage.
- `frontend/` Vite React UI.
- `docs/` research notes and implementation plan.
- `data/` generated at runtime for SQLite and thumbnails.

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Optional Ollama

Install Ollama for Windows from the official installer, then pull the recommended lightweight vision model:

```powershell
ollama pull qwen3.5:2b-q4_K_M
ollama run qwen3.5:2b-q4_K_M "用一句话说明你能做什么"
```

The app works without Ollama by falling back to rule-based analysis.

## OCR Model Cache

PaddleOCR writes model and runtime cache files under `data/paddlex-cache/` and
`data/paddle-home/` so it does not require write access to the Windows user
profile. The first OCR run can take a long time while downloading PaddleOCR
models. If PaddleOCR is unavailable, the backend falls back to RapidOCR and then
to Ollama vision OCR.

## Smoke Test

With the backend running:

```powershell
cd backend
.\.venv\Scripts\python smoke_test.py
```
