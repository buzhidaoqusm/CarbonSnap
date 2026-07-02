# CarbonSnap

CarbonSnap is a full-stack sustainability platform for recycling guidance, community knowledge sharing, reusable goods discovery, project participation, and impact tracking. The application combines a Flask backend, a Vue 3 frontend, seedable demo data, and an optional AI-assisted recycling workflow with retrieval, graph evidence, and traceable decision metadata.

## Features

- Recycling assistance with AI chat, image analysis, nearby recycling search, and answer traceability.
- Community forum flows for posts, comments, likes, recommendations, and retrieval-backed AI context.
- Marketplace and project modules for reusable goods, orders, community projects, and contributions.
- Ledger, notification, profile, and gamification features for tracking user activity and impact.
- Optional Graph Agent mode using LangGraph, Neo4j GraphRAG, forum RAG guardrails, deterministic tools, and an Agent Trace panel.
- Seed scripts and tests for local development, demos, and regression checks.

## Tech Stack

- **Frontend:** Vue 3, Vite, Vue Router, Vitest, GSAP, Three.js, Leaflet.
- **Backend:** Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-JWT-Extended, pytest.
- **AI and retrieval:** OpenAI-compatible providers, FAISS, optional LangGraph and Neo4j.
- **Data:** SQLite by default for local development, with configurable database URL support.

## Repository Structure

```text
backend/      Flask application, API routes, services, models, migrations, scripts, and tests
frontend/     Vue 3 application, views, components, API clients, styles, and frontend tests
data/seeds/   Demo data, seed metadata, and seed asset references
docs/         Project documentation, deployment notes, and design references
infra/        Infrastructure placeholders and deployment-related structure
scripts/      Development and maintenance notes
tools/        Tooling placeholders
```

## Getting Started

### Prerequisites

- Python 3.11 or a compatible Python 3.x runtime.
- Node.js 20 or a compatible recent Node.js runtime.
- Optional: Docker, if you want to run Neo4j locally for Graph Agent mode.

### Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
flask --app run.py db upgrade
python run.py
```

The backend runs at `http://127.0.0.1:5000` by default.

Before using external AI providers, edit `backend/.env` and provide the relevant API keys. Keep `backend/.env` local only; do not commit it.

### Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs at `http://127.0.0.1:5173` by default.

## Configuration

The backend reads local configuration from `backend/.env`. Start from `backend/.env.example` and update only the values needed for your environment.

Common settings include:

- `JWT_SECRET_KEY`: application signing secret for local or deployed environments.
- `LLM_PROVIDER`: AI provider selection.
- `OPENROUTER_API_KEY` / `QWEN_API_KEY`: optional provider credentials.
- `UPLOAD_ROOT`: optional custom upload directory.
- `AI_TRACE_ENABLED`: enables trace metadata in AI responses.
- `AI_GRAPH_AGENT_ENABLED`: enables the optional Graph Agent flow.
- `AI_NEO4J_GRAPHRAG_ENABLED`: enables Neo4j-backed graph retrieval when Neo4j is configured.

## Optional Graph Agent

The application runs without Neo4j. Enable Graph Agent only when you need the full AI engineering showcase with graph retrieval and detailed trace metadata.

Start Neo4j locally:

```powershell
docker run -d --name carbonsnap-neo4j --restart unless-stopped `
  -p 127.0.0.1:7474:7474 `
  -p 127.0.0.1:7687:7687 `
  -e NEO4J_AUTH=neo4j/YOUR_STRONG_PASSWORD `
  -v carbonsnap-neo4j-data:/data `
  neo4j:5
```

Add the graph settings to `backend/.env`:

```env
AI_TRACE_ENABLED=true
AI_GRAPH_AGENT_ENABLED=true
AI_NEO4J_GRAPHRAG_ENABLED=true
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=YOUR_STRONG_PASSWORD
```

Seed the graph:

```powershell
cd backend
.\.venv\Scripts\activate
python scripts\seed_recycling_graph.py
```

If Neo4j is not available, keep `AI_NEO4J_GRAPHRAG_ENABLED=false`. The application will continue to use the standard chat, forum RAG, memory, and recycling flows.

## Seed Data

Seed files live under `data/seeds/`. The seed format is documented in `data/seeds/README.md`.

Import the full demo dataset:

```powershell
cd backend
.\.venv\Scripts\activate
python scripts\seed_example_data.py
```

Import only AI demo conversations and related records:

```powershell
cd backend
.\.venv\Scripts\activate
python scripts\seed_ai_example_data.py
```

Reset local data and re-import seeds:

```powershell
cd backend
.\.venv\Scripts\activate
python scripts\reset_all_data.py
python scripts\seed_example_data.py
```

## Testing

Run backend tests:

```powershell
cd backend
.\.venv\Scripts\activate
python -m pytest tests -q
```

Run frontend tests:

```powershell
cd frontend
npm run test
```

Run the deterministic AI evaluation suite:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\unit\test_eval_suite.py -q
```

## Security Notes

- Never commit `.env` files, local databases, logs, generated media, dependency folders, or API keys.
- Rotate any credential that was previously committed or shared outside a trusted environment.
- Keep Neo4j bound to `127.0.0.1` unless it is protected by a production-grade network and authentication setup.
- Use strong production values for `JWT_SECRET_KEY`, provider keys, database credentials, and Neo4j credentials.

## Documentation

- Development spec: `docs/DEVELOPMENT_SPEC.md`
- Deployment guide: `docs/deployment/DEPLOYMENT_GUIDE_ZH.md`
- Seed data guide: `data/seeds/README.md`
