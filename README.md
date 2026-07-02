# Legal Document Intake Pipeline

Lexio is a full-stack legal document review application. Users sign in with Google through Supabase Auth, upload contract PDFs, and ask multi-turn questions that are answered with retrieved document citations.

The project is intended for local development and portfolio/demo deployment. It is not a substitute for legal advice.

## Features

- Google OAuth sign-in with Supabase sessions.
- Authenticated FastAPI backend with per-user document/session ownership checks.
- PDF text extraction with PyMuPDF.
- Local PII detection, role labeling, and redaction before embedding.
- OpenAI embeddings and answer generation.
- ChromaDB vector retrieval with local persistence or Chroma Cloud.
- Supabase tables for document metadata, chat sessions, and messages.
- React/Vite workspace with upload flow, session history, chat, citations, and latency metrics.
- Prompt-injection controls that wrap retrieved text, chat history, and user questions as untrusted data.

## Project Structure

```text
legal-pipeline/
  backend/        FastAPI API, ingestion, retrieval, guardrails, tests
  frontend/       React + Vite client
  sample-docs/    Synthetic PDFs and generators for local testing
  supabase/       Database schema and row-level security policies
```

## Prerequisites

- Node.js 18+
- Python 3.11+
- OpenAI API key
- Supabase project
- Google OAuth credentials configured in Supabase Auth
- Optional: Chroma Cloud account if you do not want local ChromaDB storage

## Supabase Setup

1. Create a Supabase project.
2. In Supabase, open `Authentication -> Providers` and enable Google.
3. Create Google OAuth credentials in Google Cloud and add the client ID and client secret to Supabase.
4. Add this authorized redirect URI in Google Cloud:

```text
https://xxxx.supabase.co/auth/v1/callback
```

Replace `xxxx` with your Supabase project reference.

5. In Supabase SQL Editor, run [supabase/schema.sql](supabase/schema.sql).
6. In `Project Settings -> API`, copy the Project URL, anon key, and service role key.

The schema creates `documents`, `sessions`, and `messages` tables with row-level security policies so browser-side access is limited to the signed-in user's rows.

## Environment Setup

Backend:

```bash
cd legal-pipeline/backend
cp .env.example .env
```

Required backend values:

```text
OPENAI_API_KEY=your_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_ANSWER_MODEL=gpt-4o
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
CORS_ORIGINS=http://localhost:5173,https://your-frontend-domain.vercel.app
CHROMA_MODE=local
CHROMA_PATH=./chroma_store
```

Use the Supabase service role key only on the backend. Never expose it in frontend environment variables.

For Chroma Cloud, set:

```text
CHROMA_MODE=cloud
CHROMA_TENANT=your_chroma_tenant
CHROMA_DATABASE=your_chroma_database
CHROMA_API_KEY=your_chroma_api_key
```

Frontend:

```bash
cd legal-pipeline/frontend
cp .env.example .env
```

Required frontend values:

```text
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
```

For local development, omit `VITE_API_BASE_URL` or set it to `/api`. Vite proxies `/api` to `http://localhost:8000` through [frontend/vite.config.js](frontend/vite.config.js). For deployed frontend builds, set `VITE_API_BASE_URL` to the public backend URL, or use the existing Vercel rewrite in [frontend/vercel.json](frontend/vercel.json).

## Run Locally

Start the backend:

```bash
cd legal-pipeline/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`.

Start the frontend in another terminal:

```bash
cd legal-pipeline/frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

## Local Workflow

1. Open `http://localhost:5173`.
2. Sign in with Google.
3. Upload a PDF from [sample-docs](sample-docs), or another text-based contract PDF.
4. Start a session after ingestion finishes.
5. Ask document-specific questions and inspect the cited source snippets.

Scanned/image-only PDFs are not currently supported. The backend expects extractable PDF text.

## Example Questions

```text
What obligations survive termination, and for how long?
```

```text
Which party can terminate the agreement, and what notice is required?
```

```text
What law governs the agreement and where must disputes be brought?
```

## API Overview

All application endpoints except `/health` require a Supabase bearer token in the `Authorization` header.

- `GET /health` - health check.
- `POST /upload` - upload and ingest a PDF.
- `POST /sessions` - create a chat session for an uploaded document.
- `GET /sessions` - list the current user's sessions.
- `GET /sessions/{session_id}/messages` - list persisted messages for a session.
- `POST /sessions/{session_id}/query` - ask a question against the session document.

## Architecture Notes

- Supabase handles Google OAuth and issues JWTs for logged-in users.
- The React frontend signs in with `@supabase/supabase-js` and sends the current Supabase access token to FastAPI.
- FastAPI verifies bearer tokens with Supabase Auth and checks `user_id` ownership before returning documents, sessions, or messages.
- Supabase stores document metadata, chat sessions, and message history.
- ChromaDB stores vectors in one collection per document, named `doc_{document_id}`.
- OpenAI receives only redacted document chunks, prior chat history wrapped as untrusted text, and the latest question.
- Local audit events for PII redaction, blocked identity-seeking queries, and query-time leak checks are written to `backend/pii_audit.log`.

## Verification

Backend:

```bash
cd legal-pipeline/backend
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile main.py app/*.py app/api/*.py app/clients/*.py app/repositories/*.py app/services/*.py tests/*.py
```

Frontend:

```bash
cd legal-pipeline/frontend
npm run build
```

## Sample Documents

Synthetic PDFs for testing are available in [sample-docs](sample-docs). They contain no real legal or confidential information.
