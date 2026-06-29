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

## Verification

Run these from `backend/`:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile main.py app/*.py app/api/*.py app/clients/*.py app/repositories/*.py app/services/*.py tests/*.py
```
