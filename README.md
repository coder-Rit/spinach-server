# Spinach Server

FastAPI backend for [Spinach](https://spinach.ddns.net/) — projects, work items, comments, JWT auth, ChromaDB vector search, and Spina AI chat.

**Live app:** https://spinach.ddns.net/  
**Frontend repo:** https://github.com/coder-Rit/spinach-client

## Stack

- Python 3.13+
- FastAPI + Uvicorn
- PostgreSQL (async SQLAlchemy)
- Alembic migrations
- ChromaDB
- JWT authentication
- LLM providers (Gemini, OpenRouter, etc.)

## Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- PostgreSQL 14+
- API keys for your chosen LLM provider(s)

## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/coder-Rit/spinach-server.git
   cd spinach-server
   ```

2. Install dependencies with uv:

   ```bash
   uv sync
   ```

   Or with pip:

   ```bash
   pip install -r requirements.txt
   ```

3. Create PostgreSQL database:

   ```bash
   createdb spinach_1
   ```

4. Copy environment variables — create `.env` in the project root:

   ```env
   environment=dev
   APP_PORT=9000

   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=spinach_1

   CHROMA_COLLECTION_NAME=spinach_v5

   JWT_SECRET_KEY=change-me-to-a-long-random-secret
   JWT_ACCESS_TOKEN_EXPIRE_DAYS=30

   GEMINI_MODEL=gemini-3-flash-preview
   GEMINI_API_KEY_1=your-key-here
   ```

   Add additional `GEMINI_API_KEY_2` … `GEMINI_API_KEY_5` if you use key rotation. Set `OPENROUTER_MODEL` / `OPENROUTER_API_KEY` if using OpenRouter.

5. Run database migrations:

   ```bash
   uv run alembic upgrade head
   ```

6. Start the API:

   ```bash
   uv run run.py
   ```

   API listens on `http://localhost:9000` by default.

## Default user (startup)

On each server start, the app ensures a demo user exists in **PostgreSQL** and **ChromaDB**:

| Field    | Value                       |
| -------- | --------------------------- |
| Name     | John Doe                    |
| Email    | `john.doe@spinach.ddns.net` |
| Password | `johndoe123`                |

Override in `.env` with `default_user_name`, `default_user_email`, `default_user_password`.

## CORS

Allowed frontend origins include `http://localhost:3000` and `https://spinach.ddns.net`. Add more origins in `app/main.py` if needed.

## API

- Base path: `/api/v1`
- Auth: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- Projects, work items, comments, LLM chat under `/api/v1/...`

## Project structure

- `app/api/v1/` — route handlers
- `app/services/` — business logic
- `app/models/` — SQLAlchemy models
- `app/db/` — session, ChromaDB, default user seed
- `alembic/` — migrations
- `chroma_db/` — local Chroma persistence (created at runtime)

## Links

- [Live app](https://spinach.ddns.net/)
- [Frontend](https://github.com/coder-Rit/spinach-client)
- [Backend (this repo)](https://github.com/coder-Rit/spinach-server)
