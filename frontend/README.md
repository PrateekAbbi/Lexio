# Frontend

The frontend is a React 19 and Vite client for the Lexio legal document review workspace.

## Features

- Google sign-in through Supabase Auth.
- Protected dashboard routes for signed-in users.
- PDF upload flow with progress state.
- Session sidebar with document metadata.
- Multi-turn chat against uploaded documents.
- Source/evidence panels for retrieved chunks.
- Workspace preferences stored in local storage.
- Automatic Supabase token refresh and logout handling when sessions expire.

## Environment

Create the local environment file:

```bash
cp .env.example .env
```

Required values:

```text
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
```

For local development, omit `VITE_API_BASE_URL` or set it to `/api`. The Vite dev server proxies `/api` to `http://localhost:8000`.

For deployment, either set `VITE_API_BASE_URL` to the public backend URL or keep requests on `/api` and configure a hosting rewrite. The current [vercel.json](vercel.json) rewrites `/api/:path*` to the Render backend URL.

Only use the Supabase anon key in frontend env files. The Supabase service role key belongs in the backend only.

## Install And Run

```bash
npm install
npm run dev
```

The dev server runs at:

```text
http://localhost:5173
```

## Scripts

- `npm run dev` - start Vite locally.
- `npm run build` - create a production build in `dist/`.
- `npm run preview` - preview the production build locally.

## Routes

- `/login` - Google OAuth sign-in.
- `/dashboard` - authenticated workspace with session list and upload entry point.
- `/session/:sessionId` - authenticated workspace focused on a selected chat session.

## Backend API Usage

API calls are centralized in [src/services/sessions.js](src/services/sessions.js). The lower-level wrapper in [src/api.js](src/api.js) reads the latest Supabase access token before each request, retries once after token refresh, and signs out when refresh fails.

The browser never calls Supabase with the service role key and never writes directly to ChromaDB.

## Verification

```bash
npm run build
```
