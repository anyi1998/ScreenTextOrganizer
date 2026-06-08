# ScreenTextOrganizer
Local screenshot OCR & text organizer.

[English](#english) | [中文 (Chinese)](#chinese) | [日本語 (Japanese)](#japanese) | [Deutsch (German)](#german)

---

<a id="english"></a>
## English

Local web tool for reviewing saved screenshots, book excerpts, interview-question images, and other image-based notes.

### Workflow
1. Scan an image folder.
2. Generate thumbnails and store metadata in SQLite.
3. Run OCR to extract text: PaddleOCR first, RapidOCR fallback, Ollama vision fallback when available.
4. Run local rule analysis, optionally enhanced by Ollama.
5. Review items in a browser table.
6. Copy text, edit OCR output, keep, mark for review, or move source images to the Windows recycle bin.
7. Export JSON, CSV, or Markdown for Obsidian-style note archives.

### Project Layout
- `backend/` FastAPI backend and SQLite storage.
- `frontend/` Vite React UI.
- `docs/` research notes and implementation plan.
- `data/` generated at runtime for SQLite and thumbnails.

### Production-Oriented Capabilities
- Operational overview: the home view shows library size, review queue, OCR progress, analysis progress, and keep/review/delete distribution from `/api/stats`.
- Content-aware rescans: unchanged files are left untouched, while changed image files reset stale OCR and analysis data.
- Cancellable OCR batches: cancellation stops the queue after the current image finishes so database state remains consistent.
- Cancellable analysis batches: long AI/Ollama analysis runs in a background worker with `/api/analyze/status` and `/api/analyze/cancel`.
- Unified task coordination: `/api/tasks/status` reports active background work and OCR/analysis batches are mutually exclusive to avoid model and database contention.
- Backend-managed AI configuration: API keys are saved in `.env`, can be cleared from the UI, and are returned to the browser only as masked metadata.
- Knowledge-base friendly exports: JSON and CSV support raw data portability, while Markdown export creates Obsidian-ready review notes with metadata, summaries, tags, OCR text, and notes.
- Explicit API contracts: core endpoints use response models for health, scan, OCR status, AI config, analysis runs, trash actions, and stats.
- Testable runtime isolation: `PIC_TEXT_PULL_DATA_DIR` and `PIC_TEXT_PULL_ENV_PATH` can redirect generated data and config.

### Quick Start

**Backend:**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

**Frontend:**
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`.

### Configuration
Copy `.env.example` to `.env`, or configure AI providers in the browser settings dialog.

Important environment variables:
- `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL`: OpenAI-compatible online analysis provider.
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`: optional local Ollama fallback.
- `PIC_TEXT_PULL_DATA_DIR`: runtime data directory for SQLite, thumbnails, and model cache.
- `PIC_TEXT_PULL_ENV_PATH`: config file path used by the backend settings API.
- `PIC_TEXT_PULL_ENV`: set to `production` for packaged or hosted deployments.
- `PIC_TEXT_PULL_CORS_ORIGINS`: comma-separated list of frontend origins allowed to call the API.
- `PIC_TEXT_PULL_SECURITY_HEADERS`: set to `0` only when an upstream proxy already injects equivalent headers.

For production-style local serving, build the frontend first and run only the backend:
```powershell
cd frontend
npm run build
cd ..\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
The backend serves `frontend/dist` automatically when it exists. SQLite runs with WAL and a 30s busy timeout so OCR batches and UI reads can coexist more reliably.

### Testing
Use the backend virtual environment so native OCR and trash dependencies resolve correctly:
```powershell
cd backend
.\.venv\Scripts\python -m pytest -p no:cacheprovider
```

Build the frontend:
```powershell
cd frontend
npm run build
```

### Optional Ollama
Install Ollama for Windows from the official installer, then pull the recommended lightweight vision model:
```powershell
ollama pull qwen3.5:2b-q4_K_M
```
The app works without Ollama by falling back to rule-based analysis.

### License
[MIT License](./LICENSE)

---

<details>
<summary><a id="chinese"></a><b>中文 (Chinese)</b></summary>

本地网页工具，用于审阅和整理已保存的截图、读书摘录、面试题截图以及其他基于图片的笔记。

### 工作流程
1. 扫描图片目录。
2. 生成缩略图并将元数据存储在 SQLite 中。
3. 运行 OCR 提取文字：首选 PaddleOCR，失败则使用 RapidOCR，如有配置也会使用 Ollama 视觉大模型作为最终后备。
4. 运行本地规则分析（可选开启 Ollama 增强分析）。
5. 在浏览器表格中审阅所有图片。
6. 复制文本、编辑 OCR 结果、保留、标记为待复核，或将原图直接移入 Windows 回收站。
7. 导出 JSON 或 CSV 数据。

### 目录结构
- `backend/` FastAPI 后端与 SQLite 数据库存储。
- `frontend/` Vite + React 界面前端。
- `docs/` 研究笔记和实现计划。
- `data/` 运行时生成的目录，存放数据库和缩略图。

### 快速开始
**后端:**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

**前端:**
```powershell
cd frontend
npm install
npm run dev
```
打开 `http://localhost:5173`。

### 可选: Ollama
安装官方 Windows 版 Ollama，并拉取推荐的轻量级视觉模型：
```powershell
ollama pull qwen3.5:2b-q4_K_M
```
如果不使用 Ollama，应用也会自动降级回基于规则的分析模式。

### 开源协议
[MIT License](./LICENSE)

</details>

---

<details>
<summary><a id="japanese"></a><b>日本語 (Japanese)</b></summary>

保存したスクリーンショット、本の抜粋、面接問題の画像など、画像ベースのメモをレビューして整理するためのローカルWebツール。

### ワークフロー
1. 画像フォルダをスキャンする。
2. サムネイルを生成し、メタデータをSQLiteに保存する。
3. OCRを実行してテキストを抽出する：PaddleOCRを最初に実行し、RapidOCR、利用可能であればOllamaビジョンモデルの順にフォールバックする。
4. ローカルのルール分析を実行する（オプションでOllamaによる強化も可能）。
5. ブラウザのテーブルでアイテムをレビューする。
6. テキストのコピー、OCR出力の編集、保持、レビュー待ちのマーク付け、または元の画像をWindowsのごみ箱に移動する。
7. JSONまたはCSVをエクスポートする。

### クイックスタート
**バックエンド:**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

**フロントエンド:**
```powershell
cd frontend
npm install
npm run dev
```
`http://localhost:5173` を開く。

### ライセンス
[MIT License](./LICENSE)

</details>

---

<details>
<summary><a id="german"></a><b>Deutsch (German)</b></summary>

Ein lokales Web-Tool zum Überprüfen und Organisieren von gespeicherten Screenshots, Buchauszügen, Bildern von Interviewfragen und anderen bildbasierten Notizen.

### Arbeitsablauf
1. Einen Bilderordner scannen.
2. Miniaturansichten generieren und Metadaten in SQLite speichern.
3. OCR ausführen, um Text zu extrahieren: zuerst PaddleOCR, als Fallback RapidOCR und falls verfügbar Ollama-Vision-Modelle.
4. Lokale Regelanalyse ausführen, optional erweitert durch Ollama.
5. Elemente in einer Browser-Tabelle überprüfen.
6. Text kopieren, OCR-Ausgabe bearbeiten, behalten, zur Überprüfung markieren oder Quellbilder in den Windows-Papierkorb verschieben.
7. JSON oder CSV exportieren.

### Schnellstart
**Backend:**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

**Frontend:**
```powershell
cd frontend
npm install
npm run dev
```
Öffnen Sie `http://localhost:5173`.

### Lizenz
[MIT License](./LICENSE)

</details>
