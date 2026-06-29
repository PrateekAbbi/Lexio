# Backend Architecture

The FastAPI entrypoint remains `main.py` so the existing command still works:

```bash
uvicorn main:app --reload
```

Implementation code now lives under `app/`:

- `app/config.py` reads environment variables once and exposes typed settings.
- `app/api/` contains thin FastAPI route handlers and HTTP error mapping.
- `app/clients/` owns OpenAI, Supabase, and Chroma client setup.
- `app/repositories/` contains database operations and keeps Supabase queries out of routes.
- `app/services/` contains business workflows for auth, PDF extraction, chunking, ingestion, and Q&A.
- `app/models.py` and `app/schemas.py` separate internal dataclasses from HTTP request schemas.

Only top-level `main.py` remains as a compatibility entrypoint for `uvicorn main:app`.

## Prompt-Injection Controls

The document Q&A flow uses a fixed prompt plan from `app/services/prompt_security.py`.

- The locked plan is selected before retrieved document text or chat history is read.
- Retrieved document chunks, prior messages, and the latest user question are wrapped as untrusted data.
- Prior messages are not replayed as separate instruction-bearing chat roles.
- The OpenAI chat payload is text-only; no `tools`, `functions`, `function_call`, or `tool_choice` fields are sent.
- OpenAI receives no Supabase client, database credentials, or write-capable tool. Supabase writes are performed only by backend repository code after the model returns text.

## Verification

Run these from `backend/`:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile main.py app/*.py app/api/*.py app/clients/*.py app/repositories/*.py app/services/*.py tests/*.py
```
