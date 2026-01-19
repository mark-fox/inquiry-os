# InquiryOS – AI Research Workspace

InquiryOS is an **AI research workspace / OS**.  
Given a complex research question, InquiryOS will (over multiple phases):

- Plan the research using a planner agent
- Search the web for relevant material
- Read and summarize sources
- Synthesize an answer with inline citations
- Persist runs, plans, sources, and answers in a searchable research notebook UI

> **Status:** Early scaffolding. Backend & frontend skeletons are in place; data model, agents, and notebook UI come next.

---

## Tech Stack

**Monorepo:** `inquiry-os`

- **Backend** – `apps/api`
  - Python, FastAPI
  - Pydantic Settings for config
  - (Planned) SQLAlchemy + Postgres + asyncpg
  - (Planned) pgvector for embeddings & retrieval
  - (Planned) Internal agent orchestration layer (planner, searcher, reader, synthesizer)

- **Frontend** – `apps/web`
  - Vite + React + TypeScript
  - TailwindCSS **3.4.4** (pinned, not latest)
  - Semantic theme tokens in `tailwind.config.cjs` (e.g. `bg-app-bg`, `text-app-muted`, etc.)
  - (Planned) shadcn/ui components

- **Infra** – `infra/` (planned)
  - Docker & docker‑compose for local/dev environments

---

## Repository Structure

Planned / emerging structure:

```text
inquiry-os/
  apps/
    api/
      app/
        api/
          v1/
            endpoints/
              # research_runs.py (planned)
            router.py
        core/
          config.py
          # logging.py, llm providers, orchestrator (planned)
      requirements.txt
      .env.example
    web/
      index.html
      package.json
      tsconfig.json
      vite.config.ts
      tailwind.config.cjs
      postcss.config.cjs
      src/
        main.tsx
        App.tsx
        components/
          layout/
            Shell.tsx
        # api/, pages/, hooks/, types/ (planned)
  infra/
    # docker-compose.yml, Dockerfiles (planned)
  .gitignore
  README.md
```

---

## Environment & Configuration

### Backend (`apps/api`)

Configuration is handled via **Pydantic Settings** in `app/core/config.py`.

Key environment variables (see `apps/api/.env.example`):

- `API_PORT` – API port (default: `8000`)
- `DATABASE_URL` – Postgres URL (used once DB is wired)
- `LLM_PROVIDER` – `"ollama"` (default) or `"openai"` (planned)
- `LLM_MODEL` – model identifier, e.g. `llama3`
- `OLLAMA_BASE_URL` – default `http://localhost:11434`
- `OPENAI_API_KEY` – optional, for hosted models (planned)
- `OPENAI_MODEL` – default `gpt-4.1-mini` (planned)

For local development you can copy the example file:

```bash
cd apps/api
cp .env.example .env
```

The API will still run without a `.env` file thanks to sensible defaults.

### Frontend (`apps/web`)

Tailwind and PostCSS are configured using **CommonJS** configs (because `package.json` uses `"type": "module"`):

- `tailwind.config.cjs`
- `postcss.config.cjs`

Semantic theme tokens live in `tailwind.config.cjs` under `theme.extend.colors.app`, e.g.:

- `bg-app-bg`
- `bg-app-surface`
- `border-app-border`
- `text-app-text`
- `text-app-muted`
- `text-app-accent`

To change the visual theme of InquiryOS, you mainly update `tailwind.config.cjs` and (as needed) shared layout components like `Shell.tsx`.

---

## Development Setup

### Prerequisites

- **Python** 3.11+ (or your chosen 3.x; the project uses a venv per app)
- **Node.js** (18+ recommended)
- **npm** (or pnpm/yarn if you prefer, but examples use npm)

---

## Backend: FastAPI API (`apps/api`)

1. Navigate to the API app:

   ```bash
   cd inquiry-os/apps/api
   ```

2. (Windows) List installed Python versions:

   ```bash
   py -0p
   ```

3. Create a virtual environment with a specific Python version (example: 3.11):

   ```bash
   py -3.11 -m venv .venv
   ```

4. Activate the virtual environment:

   ```bash
   .\.venv\Scripts\Activate
   ```

5. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

6. Run the API with Uvicorn:

   ```bash
   uvicorn app.main:app --reload
   ```

7. Verify it’s working:

   - Health check: http://127.0.0.1:8000/health
   - Ping endpoint: http://127.0.0.1:8000/api/ping

---

## Frontend: Vite + React (`apps/web`)

1. Navigate to the web app:

   ```bash
   cd inquiry-os/apps/web
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Start the dev server:

   ```bash
   npm run dev
   ```

4. Open the app in your browser:

   - http://localhost:5173/

You should see a simple **InquiryOS – AI Research Workspace** shell with a “New Research Run” section. This shell is powered by Tailwind and a reusable `Shell` layout component.

---

## Roadmap (High-Level)

**Phase 1 – Thin Vertical Slice (MVP)**

- Data model: `research_runs`, `research_steps`, `sources`, `answers`
- Planner, searcher, reader, synthesizer agents
- Web search + page fetching + summarization
- Final synthesized answer with inline citations
- Persisted research runs with basic detail view

**Phase 2 – Research Notebook & UX**

- List & filter past runs
- Notebook view (Overview, Plan, Sources, Synthesis, Notes)
- Personal notes per run
- Split-pane and collapsible source cards

**Phase 3 – Multi-Agent & Quality Controls**

- Critic/verifier agent
- Evidence scoring & confidence indicators
- Rerun/refine flows tied to previous runs

**Phase 4 – Evaluation & Show-Off Features**

- Small evaluation harness (golden questions)
- Architecture docs & diagrams
- Optional user accounts for per-user research history

---

