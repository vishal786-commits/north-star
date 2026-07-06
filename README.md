<div align="center">

# ⭐ North Star

**An AI career coach that reads your resume like a coach would — section by section, evidence over branding.**

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Redis](https://img.shields.io/badge/Redis-sessions-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![OpenAI](https://img.shields.io/badge/OpenAI-analysis-412991?logo=openai&logoColor=white)](https://openai.com/)

</div>

---

> I uploaded my own resume to test this. It flagged that I brand myself an "AI Engineer" when the evidence on the page reads as someone still in transition. It was right. The goal of North Star is to be that honest — to tell you what your resume *demonstrates*, not just what it *claims*.

## What it does

Upload a resume (PDF) and North Star returns a structured, section-aware analysis:

- **ATS score** — an overall rating plus sub-scores for keyword match, formatting, and quantification.
- **Section-by-section breakdown** — the LLM identifies *every* section, including non-standard ones you invented, and scores each with specific strengths, issues, and suggestions.
- **Length verdict** — an opinionated one-page-preferred assessment (page count is a hard fact; whether the length is *justified* is the model's judgment).
- **Career direction** — where your resume points, based on demonstrated evidence rather than self-branding, plus 2–3 realistic parallel paths with concrete requirements and an effort rating.
- **Coaching chat** *(in progress)* — a follow-up conversation about your analysis, with a per-session message limit.

## Architecture

```mermaid
flowchart LR
    U[React UI<br/>glassmorphism] -->|multipart PDF| A[POST /analyze]
    A -->|thread-offload| E[PyMuPDF<br/>text + page count]
    E --> L[OpenAI<br/>gpt-4o-mini]
    L -->|validated against| S[Pydantic schema]
    S --> R[(Redis<br/>session + TTL)]
    R -->|session_id + analysis| U
    U -->|POST /chat WIP| C[Coaching chat]
    C --> R
```

The flow: the browser uploads a PDF → FastAPI extracts text (offloaded to a thread so the blocking parse can't freeze the event loop) → OpenAI analyzes it → the response is **validated against a Pydantic schema** before anything trusts it → a session is stored in Redis → the structured analysis returns to the UI.

## Tech stack

**Backend**
- **FastAPI** (async) + **Uvicorn**
- **Pydantic v2** for typed, validated data contracts; **pydantic-settings** for config
- **PyMuPDF** for PDF text extraction
- **OpenAI** (`gpt-4o-mini`) for analysis
- **Redis** (async client, cloud-hosted) for session state

**Frontend**
- **React 18** + **Vite**
- Handwritten CSS design system — glassmorphism, light/dark themes, responsive
- Animations (count-up, ring fills, reveals) built with a small rAF hook + CSS — **no animation library**, ~51 KB gzipped

**Infra**
- **Docker** (multi-stage build, nginx serving static + proxying the API)
- **AWS ECS Fargate** target *(deployment in progress)*

## Engineering decisions worth calling out

A few choices that reflect how the system is built, not just what it does:

- **The Pydantic schema is the contract, the prompt is the guidance.** The LLM is instructed to return a specific shape, but its output is *validated* against that schema. If it returns malformed or out-of-range data, validation fails, a retry fires, and only conforming data is ever trusted. Prompt steers; schema enforces.
- **Async where it helps, threads where it doesn't.** Network I/O (OpenAI, Redis) is awaited so the server stays responsive. The CPU-bound PDF parse is offloaded via `asyncio.to_thread` so it can't block the event loop — a distinction that matters under real load.
- **Custom exception hierarchy mapped to HTTP semantics.** `ExtractionError`, `AnalysisError`, and `SessionError` translate into meaningful status codes (422 / 502 / 503) so failures are precise instead of generic 500s.
- **Evidence-critical prompting.** The model is explicitly instructed to distinguish what a resume *claims* from what it *demonstrates*, and to surface the gap — which is what makes it a coach rather than a mirror.
- **The server owns the session limit.** The chat message cap lives in the backend; the frontend reflects whatever the server enforces, so the two can never disagree.

## Getting started

### Prerequisites
- Python 3.13, Node 20+
- An OpenAI API key
- A Redis instance (local via Docker, or a free Redis Cloud database)

### Backend

```bash
# from the project root
python -m venv venv
venv\Scripts\Activate.ps1        # Windows
# source venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
```

Create a `.env` in the project root:

```env
OPENAI_API_KEY=sk-your-key
REDIS_URL=redis://default:password@host:port   # or redis://localhost:6379
```

Run it:

```bash
uvicorn app.main:app --reload
```

Interactive API docs at `http://127.0.0.1:8000/docs`.

### Frontend

```bash
cd north-star-frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. The dev server proxies `/api/*` to the backend, so no CORS setup is needed locally. To preview the UI on mock data without a running backend, set `USE_MOCK = true` in `src/api.js`.

## Project structure

```
north-star/
├── app/                     # FastAPI backend
│   ├── main.py              # app + router wiring
│   ├── config.py            # typed settings from .env
│   ├── schemas.py           # Pydantic data contracts
│   ├── extractor.py         # PDF → text + page count
│   ├── analyzer.py          # OpenAI call + schema validation
│   ├── session.py           # Redis session layer
│   ├── routes.py            # /analyze endpoint
│   └── errors.py            # custom exception types
├── north-star-frontend/     # React + Vite frontend
│   └── src/
│       ├── components/      # UI components
│       ├── api.js           # single backend integration seam
│       ├── theme.jsx        # light/dark context
│       └── hooks.js         # count-up + score helpers
└── requirements.txt
```

## Status & roadmap

North Star is **actively in development** — built in public.

- [x] Async backend: PDF extraction, OpenAI analysis, schema validation, Redis sessions
- [x] `/analyze` endpoint — working end to end
- [x] React frontend — glassmorphism UI, light/dark, animated scoring
- [ ] `/chat` endpoint — coaching conversation *(next)*
- [ ] AWS ECS Fargate deployment
- [ ] Live demo

---

<div align="center">
<sub>Built by Vishal Gopalkrishna. Feedback and issues welcome.</sub>
</div>
