# Backend_LangFlu_WebApp

FastAPI backend that handles Google OAuth for LangFlu. It redirects the user to Google, exchanges the authorization code for tokens, stores a short-lived session in an HTTP-only cookie, and exposes a simple `/auth/me` endpoint for the frontend.

## Setup

1. Create a Google OAuth client (Web) in Cloud Console.
   - Authorized redirect URI: `http://localhost:8080/auth/google/callback`
   - Authorized JavaScript origin: your frontend origin (e.g. `http://localhost:5173`)
2. Copy `.env.example` to `.env` and fill in the values.
3. Install deps & run:
   ```bash
   # from Backend_LangFlu_WebApp
   venv1\Scripts\python.exe -m pip install -r requirements.txt  # or pip install fastapi uvicorn httpx python-jose python-dotenv
   venv1\Scripts\uvicorn responseApp:app --reload --port 8080
   ```

## Env vars

- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI`
- `FRONTEND_ORIGIN` – SPA origin for CORS + post-login redirect (default `http://localhost:5173`)
- `SESSION_SECRET` – random string to sign JWT session + state
- `SESSION_COOKIE_NAME` – optional, defaults to `lf_session`
- `SESSION_TTL_MINUTES` – optional, defaults to 60
- `STATE_TTL_MINUTES` – optional, defaults to 5
- `COOKIE_SECURE` – `true` to set `Secure` on the cookie (use in HTTPS)

## Endpoints

- `GET /auth/google/start` – redirects to Google consent
- `GET /auth/google/callback` – handles the code exchange and sets session cookie, then redirects to `FRONTEND_ORIGIN`
- `GET /auth/me` – returns `{ user }` from the session cookie
- `POST /auth/logout` – clears the session cookie
