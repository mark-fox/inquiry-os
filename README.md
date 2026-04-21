# InquiryOS – AI Research Workspace

InquiryOS is an AI research application built to demonstrate practical AI engineering, full-stack development, and real-world workflow orchestration.

Given a complex research question, InquiryOS runs a structured multi-stage pipeline that:

- plans the research task
- searches the web for relevant sources
- reads and summarizes source content
- ranks and filters sources by relevance
- synthesizes a structured answer with citations

The system persists runs, sources, steps, and answers, and presents them in a workspace-style interface designed for transparency and traceability.

---

## What the Application Does

A user submits a research question such as:

> Should a startup use open-source LLMs or paid APIs for production?

InquiryOS then executes a staged workflow:

1. **Planner**  
   Breaks the question into smaller research sub-questions.

2. **Searcher**  
   Retrieves relevant web sources for the topic.

3. **Reader**  
   Fetches source content, extracts usable text, and produces summaries.

4. **Ranker / Filter**  
   Scores sources for relevance and selects the strongest candidates for synthesis.

5. **Synthesizer**  
   Produces a structured answer with:
   - summary
   - key points
   - risks
   - recommendation
   - confidence score
   - inline source citations

---

## Core Features

- Multi-stage AI pipeline: planner → searcher → reader → synthesizer
- Real-time execution with live status updates
- Source relevance scoring and filtering before synthesis
- Structured answer generation with citations
- Answer quality indicators such as:
  - coverage
  - source usage
  - confidence
- Persistent run history with a workspace-style UI
- Explainable source ranking hints
- Clickable citations linked to supporting sources
- Async execution flow with failure handling and retry support

---

## Tech Stack

### Backend
- Python
- FastAPI
- Async SQLAlchemy
- PostgreSQL
- Pydantic v2
- Ollama integration through an LLM abstraction layer
- Background task execution for pipeline runs

### Frontend
- React
- Vite
- TypeScript
- Tailwind CSS
- Component-based workspace UI

### Infrastructure
- Docker-based local database setup
- Environment-driven configuration

---

## Architecture Overview

InquiryOS is designed as a modular AI system rather than a single prompt wrapper.

### Major components

- **Pipeline Orchestrator**  
  Coordinates execution across each research stage.

- **Planner**  
  Creates an initial structured plan for the research question.

- **Searcher**  
  Retrieves candidate sources from the web.

- **Reader**  
  Fetches and extracts source content, then produces summaries and relevance scores.

- **Synthesizer**  
  Generates the final structured answer from the strongest sources.

- **Persistence Layer**  
  Stores research runs, steps, sources, answers, and pipeline events.

- **Frontend Workspace**  
  Displays run history, pipeline state, sources, and synthesized answers in a split-pane UI.

### Engineering priorities

This project emphasizes:

- clear separation of concerns
- traceable multi-step AI workflows
- explainability over black-box outputs
- deterministic validation around model output
- practical full-stack architecture

---

## Example Output

### Example 1

**Research question:**
> Is it worth starting an AI consulting business in 2026?

**Pipeline behavior:**
- Retrieved multiple web sources
- Ranked and filtered sources before synthesis
- Used top 3 of 5 sources for final answer

**Sample output (abridged):**

**Summary**  
Starting an AI consulting business in 2026 is a viable option, but requires careful consideration of market and industry trends.

**Key Points**
- Demand for AI consulting is expected to grow as adoption increases across industries [3]  
- Emerging areas like cloud computing and edge AI create new opportunities for consultants [1]

**Risks**
- Market saturation may make it difficult to stand out [2]  
- Rapid technological change may require continuous reskilling [2]

**Recommendation**  
Develop a strong understanding of industry trends, build a professional network, and focus on delivering high-value solutions. Proceed only if you can continuously adapt to changing technologies and market conditions.

---

### Example 2

**Research question:**
> Is it better to fine-tune a model or use retrieval-augmented generation (RAG)?

**Pipeline behavior:**
- Collected and summarized multiple technical sources
- Ranked sources based on relevance to the query
- Filtered weaker sources before synthesis

**Sample output (abridged):**

**Summary**  
Fine-tuning and RAG are different approaches to improving AI performance, with tradeoffs depending on the use case.

**Key Points**
- Fine-tuning adapts a model to specific data but may not generalize well [1]  
- RAG retrieves external knowledge and can improve flexibility and accuracy [2]

**Risks**
- Fine-tuning can lead to overfitting and poor generalization [3]  
- RAG systems depend on the quality of retrieved data [2]

**Recommendation**  
Use RAG when flexibility and up-to-date knowledge are required. Consider fine-tuning only when you have high-quality domain-specific data and a well-defined task.

---

## Repository Structure

```text
inquiry-os/
  apps/
    api/
      app/
        api/
        core/
        db/
        schemas/
        services/
    web/
      src/
        components/
        api/
  infra/
  README.md
```

---

## Development Setup

### Backend

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

### Environment

Backend configuration is managed through environment variables, including:

- `DATABASE_URL`
- `LLM_PROVIDER`
- `LLM_MODEL`
- `OLLAMA_BASE_URL`

Example local configuration uses:

- PostgreSQL for persistence
- Ollama for local model inference

---

## What This Project Demonstrates

InquiryOS showcases practical AI engineering skills in areas that are directly relevant to production-oriented AI roles:

- designing multi-step AI pipelines
- integrating LLMs into structured systems
- combining deterministic logic with model-generated output
- building explainable, source-backed AI features
- handling async execution and run state management
- developing full-stack AI applications with a clean separation between frontend and backend concerns

---

## Why This Project Matters

Many AI demos stop at a single prompt and response. InquiryOS focuses on the systems side of AI engineering:

- how answers are constructed
- which sources were used
- how pipeline stages are executed and tracked
- how output quality is evaluated
- how users inspect and trust results

The result is a stronger example of applied AI product engineering than a basic chatbot or prompt wrapper.
