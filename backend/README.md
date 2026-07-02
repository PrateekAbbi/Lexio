# Backend

The backend is a FastAPI service for authenticated PDF ingestion, vector indexing, and cited document Q&A.

The compatibility entrypoint remains [main.py](main.py), so this command still starts the API:

```bash
uvicorn main:app --reload
```

## Responsibilities

- Verify Supabase bearer tokens for every protected request.
- Enforce per-user ownership for documents, sessions, and messages.
- Extract text from uploaded PDFs.
- Classify common legal document types and assign role labels.
- Redact PII before chunks are embedded or sent to answer generation.
- Store document vectors in ChromaDB.
- Store metadata and chat history in Supabase.
- Retrieve relevant chunks and generate cited answers with OpenAI.
- Block identity-seeking queries that ask for hidden names, contact details, IDs, or account data.

## Layout

```text
backend/
  main.py                 Uvicorn compatibility entrypoint
  app/
    main.py               FastAPI app factory, CORS, health route, routers
    config.py             Typed environment settings
    api/                  Route handlers, dependencies, HTTP error mapping
    clients/              OpenAI, Supabase, and Chroma client factories
    repositories/         Supabase persistence operations
    services/             Auth, PDF, PII, ingestion, retrieval, prompt, Q&A workflows
    models.py             Internal dataclasses
    schemas.py            Request schemas
  tests/                  Unit tests for service boundaries and API health
```

## Environment

Create the local environment file:

```bash
cp .env.example .env
```

Core settings:

```text
OPENAI_API_KEY=your_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_ANSWER_MODEL=gpt-4o
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
CORS_ORIGINS=http://localhost:5173,https://your-frontend-domain.vercel.app
```

Local ChromaDB:

```text
CHROMA_MODE=local
CHROMA_PATH=./chroma_store
```

Chroma Cloud:

```text
CHROMA_MODE=cloud
CHROMA_TENANT=your_chroma_tenant
CHROMA_DATABASE=your_chroma_database
CHROMA_API_KEY=your_chroma_api_key
```

`SUPABASE_SERVICE_ROLE_KEY` is server-only. Do not expose it in frontend env files, Vercel variables, browser code, or client logs.

## Install And Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs at `http://localhost:8000`.

FastAPI docs are available locally at:

```text
http://localhost:8000/docs
```

## API

Protected routes require:

```text
Authorization: Bearer <supabase_access_token>
```

Routes:

- `GET /health` - returns `{"status":"ok"}` and does not require auth.
- `POST /upload` - accepts multipart `file`, validates PDF input, extracts text, redacts PII, embeds chunks, stores vectors, and creates a `documents` row.
- `POST /sessions` - accepts `{"document_id":"..."}` and creates a session for an owned document.
- `GET /sessions` - returns the signed-in user's sessions with document metadata.
- `GET /sessions/{session_id}/messages` - returns persisted chat history for an owned session.
- `POST /sessions/{session_id}/query` - accepts `{"question":"..."}`, retrieves relevant chunks, generates an answer, persists the exchange, and returns answer sources.

## Ingestion Flow

1. Validate that the upload is a non-empty PDF.
2. Extract page text with PyMuPDF.
3. Classify the document type using local keyword matching.
4. Detect PII using Presidio plus local sensitive-field patterns.
5. Replace detected entities with role or entity placeholders such as `[LANDLORD]`, `[TENANT]`, `[COMPENSATION]`, or `[EMAIL]`.
6. Split redacted page text into chunks with citation metadata.
7. Embed chunks with OpenAI.
8. Store vectors in ChromaDB collection `doc_{document_id}`.
9. Store document metadata in Supabase.

If Supabase metadata persistence fails after vector insertion, the service attempts to delete the newly created Chroma collection so retries do not leave unreachable vector data.

## Q&A Flow

1. Select the locked answer plan before reading document text or chat history.
2. Verify the requested session belongs to the current user.
3. Block identity-seeking queries before embedding or model generation.
4. Embed the latest question.
5. Retrieve the top matching chunks from ChromaDB.
6. Run a second PII validation pass on retrieved chunks.
7. Build a text-only OpenAI chat payload.
8. Persist both the user question and assistant answer in Supabase.

## Prompt-Injection Controls

The document Q&A flow uses [app/services/prompt_security.py](app/services/prompt_security.py).

- Retrieved document chunks, prior messages, and the latest question are wrapped as untrusted data.
- Prior messages are not replayed as separate instruction-bearing chat roles.
- The chat payload does not include `tools`, `functions`, `function_call`, or `tool_choice`.
- OpenAI receives no Supabase client, service role key, database credentials, or write-capable tool.
- Supabase writes happen only in repository code after model output returns.

## Privacy And Audit Controls

- PII redaction is local-only and happens before embedding.
- Role labels preserve legal context while hiding names and contact details.
- Identity-revealing requests are blocked with a privacy-safe response.
- Query-time PII leak checks redact retrieved chunks again before answer generation.
- Audit events are written to `pii_audit.log`.

## Verification

Run these from `backend/`:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile main.py app/*.py app/api/*.py app/clients/*.py app/repositories/*.py app/services/*.py tests/*.py
```

The tests cover health checks, Chroma configuration, chunking, PDF extraction, PII role labeling/redaction, query guardrails, source formatting, and prompt-injection defenses.
