# Natural Language-Based Search and Retrieval from Video

![Backend](https://img.shields.io/badge/backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/frontend-Next.js-111827)
![License](https://img.shields.io/badge/license-MIT-blue)

An end-to-end, grounded video intelligence workspace for searching and asking follow-up questions across local uploads and YouTube videos.

Production-style MVP for asking grounded natural-language questions over uploaded videos and YouTube videos.

## Features

- Multiple video upload and multiple YouTube URL ingestion
- Asynchronous processing with Celery and Redis
- FFmpeg media metadata and audio extraction
- Timestamp-aware speech-to-text abstraction
- Representative frame extraction
- OCR abstraction for slide/screen text
- Vision abstraction for frame descriptions
- Multimodal temporal chunking
- Configurable embedding service
- Hybrid retrieval over semantic and keyword signals
- Grounded answer generation with verification
- Timestamped source cards and YouTube timestamp links
- Modern Next.js workbench UI
- Backend tests and evaluation script

## Tech Stack

- Frontend: Next.js, React, TypeScript, Tailwind CSS, Radix Dialog, lucide-react
- Backend: FastAPI, SQLAlchemy, Pydantic, Celery
- Processing: FFmpeg, Whisper-compatible CLI, Tesseract-compatible OCR
- Storage: PostgreSQL + pgvector in Docker; SQLite fallback for local tests
- Queue: Redis

## Architecture

See [docs/architecture.md](docs/architecture.md).

Core pipeline:

`Video -> audio -> timestamped transcript -> frames -> OCR/vision -> multimodal chunks -> embeddings -> retrieval -> grounded RAG -> verification`

## Environment

Copy `.env.example` to `.env` and adjust values.

Important variables:

- `DATABASE_URL`
- `SYNC_DATABASE_URL`
- `REDIS_URL`
- `STORAGE_PATH`
- `MAX_UPLOAD_SIZE`
- `LLM_PROVIDER`, `LLM_API_KEY`, `MODEL_NAME`
- `EMBEDDING_PROVIDER`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`
- `SPEECH_PROVIDER`, `WHISPER_MODEL`
- `VISION_PROVIDER`
- `OCR_PROVIDER`
- `NEXT_PUBLIC_API_BASE`

The default `local` providers are deterministic and keyless. For stronger production quality, plug hosted or local model implementations into the service interfaces:

- `SpeechToTextService.transcribe`
- `EmbeddingService.embed`
- `VisionService.describe_frame`
- `OCRService.extract_text`
- `LLMService.generate_answer`

## Run With Docker

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`

## Run Locally

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]" psycopg[binary]
uvicorn app.main:app --reload
```

Worker:

```bash
cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## API

- `POST /api/videos/upload`
- `POST /api/videos/youtube`
- `GET /api/videos`
- `GET /api/videos/{id}`
- `DELETE /api/videos/{id}`
- `GET /api/videos/{id}/status`
- `GET /api/videos/{id}/segments`
- `GET /api/videos/{id}/stream`
- `POST /api/search`
- `POST /api/ask`

## Retrieval

Each `video_chunk` contains:

- `video_id`
- `start_time`
- `end_time`
- `transcript`
- `visual_description`
- `ocr_text`
- `combined_text`
- `embedding`

Search combines embedding cosine similarity with keyword overlap, then returns timestamped chunks. The current MVP keeps embeddings as JSON for SQLite compatibility in tests; Docker uses PostgreSQL + pgvector and the schema is ready to evolve to native vector indexes.

## Hallucination Prevention

The ask endpoint retrieves a small evidence set, generates an answer only from those chunks, and runs a grounding verifier. Weak retrieval or unsupported answers return:

`I couldn't find this information in the provided videos.`

No frontend API key is required, and no outside knowledge is used by the default answer service.

## Timestamp Links

Uploaded videos use the HTML video player and set:

```ts
video.currentTime = source.start_time;
video.play();
```

YouTube sources return a timestamp URL such as:

`https://www.youtube.com/watch?v=ABC123&t=497s`

## Tests

```bash
cd backend
pytest
```

Covered areas:

- timestamp formatting
- YouTube timestamp URL generation
- YouTube URL validation
- filename sanitization
- retrieval on synthetic data
- grounded answer acceptance
- unsupported-question rejection

## Evaluation

Run after the app is up and sample videos are indexed:

```bash
python scripts/evaluate.py
```

Metrics:

- Precision@1
- MRR
- timestamp accuracy
- unsupported-question rejection rate

Dataset: [docs/evaluation_dataset.json](docs/evaluation_dataset.json)

## Demo Scenario

Add:

1. DBMS Lecture 1
2. DBMS Lecture 2
3. SQL Lecture

Ask:

- `What is the difference between clustered and non-clustered indexes?`
- `What are the three components of the CAP theorem shown in the slide?`
- `What is the time complexity of Dijkstra's algorithm?`

The final query should be rejected unless that information appears in the provided videos.

## Known Limitations

- Default local LLM is extractive and conservative; wire a stronger hosted/local LLM behind `LLMService` for more fluent synthesis.
- Native pgvector operators are not yet used in ORM retrieval because tests run against SQLite.
- Scene detection is represented by interval sampling; OpenCV scene-difference sampling can be added behind the same processing service.
- YouTube availability depends on `yt-dlp`, network access, and platform restrictions.

## Future Improvements

- Native pgvector index and PostgreSQL full-text ranking
- Cross-encoder reranker
- Streaming answer responses
- Better progress events through WebSockets or server-sent events
- Thumbnail generation
- Provider implementations for OpenAI, local Whisper, PaddleOCR/EasyOCR, and VLMs

