# mail-manager

A modular email-intelligence and personal productivity engine that ingests emails from Gmail and Microsoft 365 Outlook, analyzes them using locally hosted LLMs, manages tasks and projects, provides a combined calendar view, and maintains living documents — all running on local infrastructure with zero paid cloud services.

See [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for full architecture and technical details.

## Prerequisites

- [Docker](https://www.docker.com/) & Docker Compose
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- [Node.js](https://nodejs.org/) 22+ with npm
- A Google Cloud project with Gmail API, Google Tasks API, and Google Calendar API enabled (see [Google Cloud Setup](#google-cloud-setup))
- A Microsoft Azure app registration for Outlook and Calendar access (see [Microsoft Azure Setup](#microsoft-azure-setup))

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/Monty-92/mail-manager.git
cd mail-manager

# 2. Copy env template and fill in Google OAuth credentials
cp .env.example .env

# 3. Start the full stack
docker compose up

# 4. Run database migrations
make migrate
```

The frontend will be available at `http://localhost:3000` and the BFF API at `http://localhost:8000/api/v1/`.

## Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Gmail API**, **Google Tasks API**, and **Google Calendar API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Set application type to **Web application**
6. Add `http://localhost:8000/auth/callback` as an authorized redirect URI
7. Copy the Client ID and Client Secret into your `.env` file

## Microsoft Azure Setup

1. Go to [Azure App Registrations](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps)
2. Click **New registration**
3. Set name to `mail-manager`, supported account types to **Personal Microsoft accounts only**
4. Add `http://localhost:8000/auth/ms/callback` as a redirect URI (Web platform)
5. Go to **Certificates & secrets** → **New client secret** → copy the value
6. Go to **API permissions** → **Add**: `Mail.Read`, `Calendars.Read`, `User.Read` (Microsoft Graph, delegated)
7. Copy the Application (client) ID and client secret into `MS_CLIENT_ID` and `MS_CLIENT_SECRET` in your `.env` file
8. Leave `MS_TENANT_ID=common` for personal accounts

## Commands

| Task | Command |
|------|---------|
| Start full stack | `make up` or `docker compose up` |
| Start in background | `make up-d` |
| Stop all services | `make down` |
| Run migrations | `make migrate` |
| Run all tests | `make test` |
| Test one service | `make test-svc svc=ingestion` |
| Lint all | `make lint` |
| Lint one service | `make lint-svc svc=ingestion` |
| View logs | `make logs` |
| Full cleanup | `make clean` |

## Architecture

```
Frontend (Vue 3) → BFF (FastAPI) → Internal Services → PostgreSQL + pgvector
                                                     → Redis (pub/sub)
                                                     → Ollama (local LLM)
```

8 Python microservices: Ingestion (Gmail + Outlook), Preprocessing, LLM Analysis, Topic Tracking, Summary Generation, Task Management, Calendar Sync, and BFF.

## Project Structure

```
mail-manager/
├── PROJECT_OVERVIEW.md          # Authoritative architecture reference
├── README.md                    # This file
├── docker-compose.yml           # Full stack definition
├── Makefile                     # Common commands
├── .env.example                 # Environment variable template
├── services/
│   ├── ingestion/               # Gmail + Outlook email ingestion
│   ├── preprocessing/           # Text cleaning + embeddings
│   ├── llm-analysis/            # LLM summarization + classification
│   ├── topic-tracking/          # Topic management + evolution
│   ├── summary-generation/      # Daily summary generation
│   ├── task-management/         # Task extraction + Google Tasks sync
│   ├── calendar-sync/           # Google + Outlook calendar aggregation
│   └── bff/                     # Backend-for-Frontend API layer
├── frontend/                    # Vue 3 + Tailwind + TypeScript
├── db/
│   └── migrations/              # SQL migrations
└── docs/                        # Additional documentation
```

## License

Private