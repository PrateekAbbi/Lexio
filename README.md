# Legal Document Intake Pipeline

A local full-stack legal AI demo with Google OAuth, Supabase-backed session history, PDF ingestion, ChromaDB retrieval, and multi-turn cited Q&A.

## 1. Prerequisites

- Node 18+
- Python 3.11+
- OpenAI API key
- Supabase project
- Google OAuth credentials for Supabase Auth

## 2. Supabase setup

a. Create a free project at https://supabase.com.

b. Go to Authentication -> Providers -> enable Google. Create Google OAuth credentials at https://console.cloud.google.com and paste the client ID and client secret into Supabase.

Set the Authorized redirect URI in Google Cloud to:

```text
https://xxxx.supabase.co/auth/v1/callback
```

Replace `xxxx` with your Supabase project reference.

c. Go to SQL Editor -> paste the contents of [supabase/schema.sql](supabase/schema.sql) -> run it.

d. Go to Project Settings -> API -> copy the Project URL, anon key, and service role key.

## 3. Environment setup

Backend:

```bash
cd legal-pipeline/backend
cp .env.example .env
```

Fill in:

```text
OPENAI_API_KEY=your_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_ANSWER_MODEL=gpt-4o
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

Frontend:

```bash
cd legal-pipeline/frontend
cp .env.example .env
```

Fill in:

```text
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
```

The frontend never uses the service role key.

## 4. Run backend

```bash
cd legal-pipeline/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs at http://localhost:8000.

## 5. Run frontend

```bash
cd legal-pipeline/frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173.

## 6. Three example legal questions to test with a contract PDF

```text
What obligations survive termination, and for how long?
```

```text
Which party can terminate the agreement, and what notice is required?
```

```text
What law governs the agreement and where must disputes be brought?
```

## Architecture notes

- Supabase handles Google OAuth and issues JWTs for logged-in users.
- The React frontend signs in with `@supabase/supabase-js` and sends the Supabase access token to FastAPI.
- FastAPI verifies the token with `supabase.auth.get_user(token)`.
- Supabase stores document metadata, chat sessions, and messages.
- ChromaDB still persists vectors locally under `backend/chroma_store`.
- Each document has a separate Chroma collection named `doc_{document_id}`.
- Multi-turn context is loaded from the `messages` table and sent to the configured OpenAI answer model with the latest retrieved document chunks.
- Row Level Security policies are included so browser-side Supabase access can only see user-owned rows. Backend service-role queries also explicitly filter by `user_id` before returning data.

## Local sample documents

Synthetic PDFs for testing are available in [sample-docs](sample-docs). They contain no real legal or confidential information.
