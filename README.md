<div align="center">

# ⭐ North Star

**An AI career coach that reads your resume like a coach would — section by section, evidence over branding.**

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Redis](https://img.shields.io/badge/Redis-sessions-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![OpenAI](https://img.shields.io/badge/OpenAI-analysis-412991?logo=openai&logoColor=white)](https://openai.com/)
[![Docker](https://img.shields.io/badge/Docker-single%20image-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![AWS](https://img.shields.io/badge/AWS-ECS%20Fargate-FF9900?logo=amazonaws&logoColor=white)](https://aws.amazon.com/fargate/)

</div>

---

> I uploaded my own resume to test this. It flagged that I brand myself an "AI Engineer" when the evidence on the page reads as someone still in transition. It was right. The goal of North Star is to be that honest — to tell you what your resume *demonstrates*, not just what it *claims*.

## What it does

Upload a resume (PDF) and North Star returns a structured, section-aware analysis:

- **ATS score** — an overall rating plus sub-scores for keyword match, formatting, and quantification.
- **Section-by-section breakdown** — the LLM identifies *every* section, including non-standard ones you invented, and scores each with specific strengths, issues, and suggestions.
- **Length verdict** — an opinionated one-page-preferred assessment (page count is a hard fact; whether the length is *justified* is the model's judgment).
- **Career direction** — where your resume points, based on demonstrated evidence rather than self-branding, plus 2–3 realistic parallel paths with concrete requirements and an effort rating.
- **Job Fit** — paste a specific job description and get an honest, evidence-based match score, what lines up vs. what's missing, gaps to close, and concrete ways to tailor the resume for *that* role.
- **Coaching chat** — a follow-up conversation about your analysis (or job fit), grounded in your resume and its scores, with a per-session message limit enforced by the server.
- **Monitoring & feedback** — every request is recorded to a durable SQLite store (latency, token usage, scores, errors), a 👍/👎 widget captures result quality, and a `/metrics.html` dashboard surfaces the aggregates.
- **Abuse & cost guardrails** — a per-IP daily request cap, upload-size / job-description / message length limits, and PDF-only validation, so the OpenAI spend and the service stay bounded under real traffic.

## Architecture

```mermaid
flowchart LR
    U[Single-page UI<br/>vanilla HTML/CSS/JS] -->|multipart PDF| A[POST /api/analyze]
    A -->|thread-offload| E[PyMuPDF<br/>text + page count]
    E --> L[OpenAI<br/>gpt-4o-mini]
    L -->|validated against| S[Pydantic schema]
    S --> R[(Redis<br/>session + TTL)]
    R -->|session_id + analysis| U
    U -->|POST /api/chat| C[Coaching chat]
    C --> R
```

The flow: the browser uploads a PDF → FastAPI extracts text (offloaded to a thread so the blocking parse can't freeze the event loop) → OpenAI analyzes it → the response is **validated against a Pydantic schema** before anything trusts it → a session is stored in Redis → the structured analysis returns to the UI. Follow-up chat messages reload that session and answer grounded in the resume + analysis.

The whole thing ships as **one FastAPI service**: the API lives under `/api`, and the frontend is a single self-contained `static/index.html` served by FastAPI itself — no separate frontend server, no build step.

## Tech stack

**Backend**
- **FastAPI** (async) + **Uvicorn**
- **Pydantic v2** for typed, validated data contracts; **pydantic-settings** for config
- **PyMuPDF** for PDF text extraction
- **OpenAI** (`gpt-4o-mini`) for analysis and chat
- **Redis** (async client) for session state

**Frontend**
- A single **vanilla HTML/CSS/JS** file (`static/index.html`) — **no framework, no build step, no npm**
- Handwritten CSS design system — glassmorphism, light/dark themes, responsive, `prefers-reduced-motion` aware
- Animations (count-up, ring fills, reveals) built with `requestAnimationFrame` + CSS — no animation library
- Served directly by FastAPI via `StaticFiles`

**Infra**
- **Docker** — a single `python:3.13-slim` image running Uvicorn (no Node stage, no nginx)
- **AWS ECS Fargate** (Express Mode) behind an **Application Load Balancer** — *deployed and live*
- **Redis Cloud** for session state; **SQLite** on a mounted volume for metrics

## Engineering decisions worth calling out

A few choices that reflect how the system is built, not just what it does:

- **The Pydantic schema is the contract, the prompt is the guidance.** The LLM is instructed to return a specific shape, but its output is *validated* against that schema. If it returns malformed or out-of-range data, validation fails, a retry fires, and only conforming data is ever trusted. Prompt steers; schema enforces.
- **Async where it helps, threads where it doesn't.** Network I/O (OpenAI, Redis) is awaited so the server stays responsive. The CPU-bound PDF parse is offloaded via `asyncio.to_thread` so it can't block the event loop — a distinction that matters under real load.
- **Custom exception hierarchy mapped to HTTP semantics.** `ExtractionError`, `AnalysisError`, and `SessionError` translate into meaningful status codes (422 / 502 / 503) so failures are precise instead of generic 500s.
- **Evidence-critical prompting.** The model is explicitly instructed to distinguish what a resume *claims* from what it *demonstrates*, and to surface the gap — which is what makes it a coach rather than a mirror.
- **The server owns the session limit.** The chat message cap lives in the backend; the frontend reflects whatever the server enforces, so the two can never disagree.
- **One deployable, no build pipeline.** Collapsing the UI into a single static file served by the API means one container, one process, and no Node toolchain to ship or secure.
- **The rate limiter fails open, on purpose.** Per-IP daily limits are enforced in Redis, but if Redis is unreachable the limiter allows the request through — a cost cap matters less than keeping the tool available. The real client IP is resolved from `X-Forwarded-For` by counting `trusted_proxy_hops` from the right, so a spoofed leftmost header can't dodge the cap.

## Getting started

### Prerequisites
- Python 3.13
- An OpenAI API key
- A Redis instance (local via Docker, or a free Redis Cloud database)

### Run it locally

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

# Optional — monitoring
METRICS_DB_PATH=data/metrics.db   # durable SQLite store (default shown)
ADMIN_TOKEN=some-long-secret      # guards GET /api/metrics + /metrics.html; if unset, the dashboard is open

# Optional — abuse / cost guardrails (defaults shown)
DAILY_IP_LIMIT=5            # combined /analyze + /fit requests per IP per day
TRUSTED_PROXY_HOPS=1        # X-Forwarded-For hops: ALB=1, CloudFront+ALB=2
MAX_UPLOAD_BYTES=5242880    # 5 MB PDF cap
MAX_JD_CHARS=20000          # job-description length cap
MAX_MESSAGE_CHARS=4000      # chat message length cap
```

Run it:

```bash
uvicorn app.main:app --reload
```

- App (UI): `http://127.0.0.1:8000/`
- Interactive API docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

### Run with Docker

```bash
docker build -t north-star .
docker run -p 8000:8000 --env-file .env north-star
```

Then open `http://127.0.0.1:8000/`.

## Deployment (AWS)

North Star runs on **AWS ECS Fargate** (Express Mode), which provisions the service and an
**Application Load Balancer** from the container image. The image is built from the single
`Dockerfile`, pushed to **Amazon ECR**, and served by Uvicorn with `--proxy-headers` so the ALB's
`X-Forwarded-For` is trusted for real-client IP resolution.

- **Sessions** — external **Redis Cloud** via `REDIS_URL` (no in-cluster Redis to manage).
- **Metrics** — SQLite on the container's `/app/data` volume (single-instance; scaling past one task
  requires moving metrics to a shared store).
- **Config** — `OPENAI_API_KEY`, `REDIS_URL`, and `ADMIN_TOKEN` are injected as task environment /
  secrets, never baked into the image (`.dockerignore` excludes `.env`, `data/`, and local state).
- **Proxy** — set `TRUSTED_PROXY_HOPS=1` for a single ALB so the per-IP rate limit attributes to the
  real client rather than a spoofable header.
- **Health checks** — point the ALB target group at `GET /ready` (verifies Redis) and keep `GET /health`
  for cheap liveness. The container also has a Docker `HEALTHCHECK` hitting `/health`.

## CI/CD (GitHub Actions)

Two workflows live in `.github/workflows/`:

- **`ci.yml`** — on every pull request and push: installs deps, runs `ruff check` and `pytest`. The
  suite fakes Redis and OpenAI, so no secrets are needed.
- **`deploy.yml`** — on push to `master`: re-runs lint + tests, then (via **GitHub OIDC**, no stored
  AWS keys) logs in to ECR, builds and pushes the image tagged with the commit SHA (and `latest`),
  fetches the live ECS task definition, swaps in the new image, and updates the service — waiting for
  it to reach stability.

**One-time AWS setup** (console or CLI):

1. Create the GitHub OIDC identity provider in IAM (`token.actions.githubusercontent.com`,
   audience `sts.amazonaws.com`).
2. Create an IAM role whose trust policy allows this repo/branch to assume it via that provider, with
   permissions for: `ecr:GetAuthorizationToken` + image push/pull, `ecs:DescribeTaskDefinition`,
   `ecs:RegisterTaskDefinition`, `ecs:UpdateService`, `ecs:DescribeServices`, and `iam:PassRole` for
   the task's execution/task roles.

**GitHub → Settings → Secrets and variables → Actions → Variables** (all non-secret):

| Variable | Example |
|---|---|
| `AWS_ROLE_ARN` | `arn:aws:iam::123456789012:role/north-star-deploy` |
| `AWS_REGION` | `ap-south-1` |
| `ECR_REPOSITORY` | `north-star` |
| `ECS_CLUSTER` | `north-star-cluster` |
| `ECS_SERVICE` | `north-star-service` |
| `ECS_TASK_FAMILY` | `north-star` |
| `ECS_CONTAINER_NAME` | `north-star` |

## Observability (AWS CloudWatch)

The app is instrumented to feed CloudWatch **without any AWS SDK or IAM in the request path**:

- **Structured logs** — `app/logging_config.py` emits single-line JSON to stdout with a per-request
  `request_id` (set by a middleware in `app/main.py`, echoed on the `X-Request-ID` response header).
  In ECS the awslogs driver ships these to CloudWatch Logs, queryable in Logs Insights.
- **Metrics via EMF** — `app/observability.py` prints one CloudWatch [Embedded Metric Format](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html)
  line per request (namespace **`NorthStar`**). CloudWatch auto-extracts `RequestCount`, `ErrorCount`,
  `LatencyTotalMs`, `LatencyLlmMs`, `ExtractMs`, token counts, and `EstCostUsd` — as a fleet aggregate
  and sliced by endpoint (`Kind` = review/fit/chat). Emission is wired once inside
  `metrics.record_event`, so every recorded event publishes automatically.
- **Dashboard + alarms (IaC)** — `infra/cloudwatch.yaml` (CloudFormation) provisions a `north-star`
  dashboard (app metrics + ALB + ECS widgets) and alarms (error count, latency p95, ALB 5xx, unhealthy
  hosts, ECS CPU) that notify an SNS email subscription.

Deploy the monitoring stack:

```bash
aws cloudformation deploy \
  --template-file infra/cloudwatch.yaml \
  --stack-name north-star-observability \
  --parameter-overrides \
    AlarmEmail=you@example.com \
    ClusterName=<cluster> ServiceName=<service> \
    LoadBalancerFullName=app/<alb-name>/<id> \
    TargetGroupFullName=targetgroup/<tg-name>/<id>
```

Enable ECS Container Insights once so the CPU/memory widgets populate:

```bash
aws ecs update-cluster-settings --cluster <cluster> \
  --settings name=containerInsights,value=enabled
```

## Testing

The test suite fakes Redis and OpenAI, so it runs offline with no API key. Install the test-only
dependencies (kept out of the runtime `requirements.txt`) first:

```bash
pip install -r requirements-dev.txt
pytest
ruff check app tests   # lint (same check CI runs)
```

It covers the rate limiter (daily budgeting, fail-open on Redis errors, `X-Forwarded-For` hop
resolution) in `tests/test_ratelimit.py`, the endpoint input guardrails (size caps, PDF-only,
length limits, shared daily cap across `/analyze` + `/fit`) in `tests/test_endpoints.py`, the EMF
metric shape in `tests/test_observability.py`, and liveness/readiness + request-ID correlation in
`tests/test_health.py`.

## API reference

| Method & path | Body | Returns |
|---|---|---|
| `POST /api/analyze` | multipart form, field `file` (PDF) | `{ session_id, analysis }` |
| `POST /api/fit` | multipart form, `file` (PDF) + `job_description` (text) | `{ session_id, fit }` |
| `POST /api/chat` | JSON `{ session_id, message }` | `{ reply, messages_remaining, limit_reached }` |
| `POST /api/feedback` | JSON `{ session_id, rating, comment? }` (`rating`: `up`\|`down`) | `{ status }` |
| `GET /api/metrics` | query `?token=` or header `X-Admin-Token` | aggregate monitoring JSON |
| `GET /health` | — | `{ "status": "ok" }` (liveness — process is up) |
| `GET /ready` | — | `{ "status": "ready" }`, or `503` if Redis is unreachable (readiness) |

**Notes**
- Sessions are stored in Redis and expire after **1 hour** of inactivity.
- The coaching chat is capped at **5 messages per session**; the 6th request returns `429`.
- `analysis` contains: `ats`, `length`, `sections[]`, `overall_improvements[]`, `primary_path`, `parallel_paths[]`, and a `summary`.
- `fit` contains: `match_score`, `verdict`, `matched_requirements[]`, `missing_requirements[]`, `strengths_for_role[]`, `gaps[]`, `tailoring_suggestions[]`, and a `summary`.
- **Metrics** persist to SQLite (`METRICS_DB_PATH`); `GET /api/metrics` requires `ADMIN_TOKEN` when one is set. The dashboard lives at `/metrics.html`.
- Each IP is capped at **5 combined `/analyze` + `/fit` requests per day** (`DAILY_IP_LIMIT`); over-budget requests return `429` with a `Retry-After` header.
- Input guardrails: uploads over **5 MB** → `413`, non-PDF uploads → `400`, over-long job descriptions → `413`, over-long chat messages → `422`.

## Project structure

```
north-star/
├── app/                     # FastAPI backend
│   ├── main.py              # app wiring: lifespan, request-id middleware, /health + /ready, static mount
│   ├── config.py            # typed settings from .env
│   ├── schemas.py           # Pydantic data contracts
│   ├── extractor.py         # PDF → text + page count
│   ├── analyzer.py          # OpenAI analysis + fit + chat, schema validation
│   ├── session.py           # Redis session layer + message limit
│   ├── metrics.py           # durable SQLite metrics + feedback store (also emits EMF)
│   ├── observability.py     # CloudWatch EMF metric emission (stdout, no SDK)
│   ├── logging_config.py    # structured JSON logging + request-id contextvar
│   ├── ratelimit.py         # per-IP daily rate limiter (Redis, fail-open)
│   ├── routes.py            # endpoints + rate-limit dependency wiring
│   └── errors.py            # custom exception types
├── static/
│   ├── index.html           # entire self-contained frontend (tabs, results, chat)
│   └── metrics.html         # monitoring dashboard
├── tests/
│   ├── test_endpoints.py    # endpoint guardrails (faked Redis + OpenAI)
│   ├── test_ratelimit.py    # rate-limiter unit tests
│   ├── test_observability.py # EMF metric shape
│   ├── test_health.py       # liveness/readiness + request-id
│   └── conftest.py          # shared fixtures / sample payloads
├── infra/
│   └── cloudwatch.yaml      # CloudFormation: dashboard + alarms + SNS
├── .github/workflows/
│   ├── ci.yml               # lint + test on PR/push
│   └── deploy.yml           # build → ECR → ECS deploy (OIDC) on master
├── pyproject.toml           # ruff config
├── pytest.ini
├── Dockerfile               # single-image build (+ HEALTHCHECK)
└── requirements.txt
```

## Status & roadmap

North Star is **actively in development** — built in public.

- [x] Async backend: PDF extraction, OpenAI analysis, schema validation, Redis sessions
- [x] `/api/analyze` endpoint — working end to end
- [x] `/api/chat` endpoint — coaching conversation with per-session limit
- [x] `/api/fit` endpoint — resume-to-job fit analysis
- [x] Frontend — glassmorphism UI, light/dark, animated scoring, Resume Review + Job Fit tabs, PDF export, how-to/FAQ (single-file, no build)
- [x] Monitoring — SQLite metrics + feedback widget + `/metrics.html` dashboard
- [x] Abuse guardrails — per-IP daily rate limit, upload/JD/message caps, PDF-only validation
- [x] Test suite — rate-limiter + endpoint guardrail tests (pytest, fakeredis)
- [x] Single-container Docker image
- [x] AWS ECS Fargate deployment — live behind an Application Load Balancer
- [ ] Public live demo link

---

<div align="center">
<sub>Built by <b>Vishal Gopalkrishna</b> — feedback and issues welcome.</sub>
<br/>
<sub>
<a href="mailto:gopalkrishna.vishal@gmail.com">Email</a> ·
<a href="https://github.com/vishal786-commits">GitHub</a> ·
<a href="https://www.linkedin.com/in/vishal-gopalkrishna-33852413/">LinkedIn</a>
</sub>
<br/>
<sub>© 2026 Vishal Gopalkrishna</sub>
</div>
