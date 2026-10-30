# MindTrace: Intelligent Multimedia Learning Companion

**University FYP-1**: Persistent Misconception Tracking with Local Offline Speech-to-Text & Diagnostic Checkpoints.

---

## 1. 100% Free Local Speech Transcription (No Paid APIs)

MindTrace uses **`faster-whisper`** running locally on your computer via **CPU with INT8 quantization**.
- **No OpenAI API Key** required.
- **No paid cloud subscriptions** or token costs.
- **Completely offline**: Models (`base` and `tiny`) are automatically cached locally on your machine and reused.
- Supports common audio/video formats: **MP4, MOV, WEBM, MP3, WAV, M4A, OGG** using native PyAV and FFmpeg.

---

## 2. Quick Start with PowerShell

### A. Start Everything with One Click
Double-click the root batch file:
```powershell
.\start_mindtrace.bat
```

### B. Or Run Services Manually in Separate PowerShell Terminals

#### Terminal 1: Backend (FastAPI on Port 8000)
```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

#### Terminal 2: Frontend (Vite/React on Port 5173)
```powershell
cd frontend
npm run dev
```

Then open your browser to **http://localhost:5173**.
- **Demo Student Login**: `demo@mindtrace.edu`
- **Password**: `mindtrace123`

---

## 3. Dependency Installation

If setting up on a fresh machine or virtual environment:
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> **Note on Audio/Video Decoding**:
> MindTrace includes `av` (PyAV), which bundles FFmpeg multimedia codecs for MP4, MP3, WAV, M4A, and OGG natively. If you wish to install system-wide FFmpeg on Windows:
> ```powershell
> winget install Gyan.FFmpeg
> ```

---

## 4. End-to-End Processing Flow

The system processes uploaded recordings through a genuine multi-stage pipeline:

1. **`/upload`** (`POST`):
   Saves the multimedia file and registers the lecture in SQLite.
2. **`/transcribe/{id}`** (`POST`):
   Runs local `faster-whisper` on CPU to extract genuine spoken words with millisecond-accurate timestamps (`start_time` and `end_time`).
3. **`/generate/{id}`** (`POST`):
   Segments spoken content into cohesive pedagogical concepts and synthesizes diagnostic checkpoints / MCQs strictly grounded in the transcript.
4. **`/segments/{id}`** (`GET`):
   Retrieves all timestamped spoken transcript segments for player timeline alignment.
5. **`/answer`** (`POST`):
   Evaluates student MCQ submissions, records attempts persistently, and updates misconception states (*Suspected* &rarr; *Confirmed* &rarr; *Resolved* &rarr; *Recurred*).
6. **`/report/{recording_id}`** (`GET`):
   Compiles comprehensive student learning analytics and friction points.

---

## 5. Automated Verification Test Suite

To verify all 12 stages of the complete workflow (including local Faster-Whisper transcription on real uploaded video):

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python test_complete_workflow.py
```

