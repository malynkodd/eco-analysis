# Eco Analysis — Techno-Economic Analysis Platform

A microservice web platform for techno-economic and ecological evaluation of
environmental measures (insulation, equipment replacement, treatment
facilities, renewable energy). Built as a diploma thesis project — Igor
Sikorsky Kyiv Polytechnic Institute, 2026.

The system runs every relevant analysis method on the same portfolio of
alternatives — financial (NPV / IRR / BCR / Payback / LCCA), multi-criteria
(AHP + TOPSIS), ecological impact (CO₂ reduction + regulatory damage),
scenario modelling (what-if / sensitivity / break-even) — and produces a
consensus ranking + PDF/Excel report.

---

## Contents

- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Quick start](#quick-start)
- [Default credentials](#default-credentials)
- [Services & ports](#services--ports)
- [API reference](#api-reference)
- [Implemented methods](#implemented-methods)
- [Database schema](#database-schema)
- [Environment variables](#environment-variables)
- [Testing & CI](#testing--ci)
- [Repository layout](#repository-layout)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Browser (React 19 + Vite)                 │
│                http://localhost  /  https://localhost        │
└──────────────────────────────┬───────────────────────────────┘
                               │  /api/v1/*  (envelope: {data, error, meta})
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                NGINX Gateway   (ports 80, 443)               │
│   TLS · CORS · rate limiting · JWT auth_request · routing    │
└──┬─────┬────────┬────────┬────────┬────────┬────────┬────────┘
   │     │        │        │        │        │        │
   ▼     ▼        ▼        ▼        ▼        ▼        ▼
 auth project financial  eco  multi-crit scenario comparison report
                    \________________________________/
                          inter-service calls via
                       eco_common.http_client (httpx
                       + retry + circuit breaker
                       + X-Request-ID propagation)
                               │
                               ▼
                        PostgreSQL 15
              ◄── Alembic migrations (one-shot container)
```

All eight backend services are FastAPI apps running under
`gunicorn + uvicorn.workers.UvicornWorker`, share a single Dockerfile pattern,
and expose the same envelope and `/health` contract via `eco_common`.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8, React Router 6, Recharts 3, axios |
| Backend | Python 3.11, FastAPI 0.111, Pydantic 2.7, SQLAlchemy 2.0 |
| Numerics | NumPy 1.26, SciPy 1.13 (Brent's method for IRR & break-even) |
| Auth | RS256 JWT (python-jose), bcrypt (passlib, ≥10 rounds) |
| Database | PostgreSQL 15, Alembic 1.13 (idempotent migrations) |
| HTTP client | httpx 0.27 with bespoke retry + circuit breaker |
| Reports | ReportLab 4.1 (PDF), openpyxl 3.1 (Excel), Matplotlib 3.9 |
| Observability | structlog 24, prometheus-client 0.20 |
| Gateway | NGINX (TLS 1.2/1.3, `auth_request` JWT subrequest, gzip) |
| Tests | pytest, ruff, pyright |
| Orchestration | Docker Compose v3 |

---

## Quick start

Prerequisites: Docker + Docker Compose, OpenSSL.

```bash
# 1. Configure environment
cp .env.example .env
$EDITOR .env                       # set strong POSTGRES_PASSWORD + ADMIN_PASSWORD

# 2. Generate JWT keypair (RS256) and self-signed TLS cert
./scripts/generate_keys.sh
./scripts/generate_tls.sh

# 3. Build and start the entire stack
docker compose up -d --build

# 4. Tail logs while migrations apply and services come up healthy
docker compose logs -f migrations auth-service
```

Open <https://localhost> (accept the self-signed certificate). The NGINX
gateway terminates TLS on port 443 and redirects port 80 → 443.

```bash
# Useful commands
docker compose ps                  # see container health
docker compose down                # stop and remove containers
docker compose down -v             # also wipe the postgres volume
```

---

## Default credentials

The auth service auto-creates the admin user on first boot from the
`ADMIN_*` env vars. After the first successful boot, those env vars can be
removed — the service will **not** recreate or reset the admin.

```
username: admin                          (from $ADMIN_USERNAME)
password: change_me_strong_password      (from $ADMIN_PASSWORD)
role:     admin
```

New users register through the UI (`/register`) as **analyst** by default.
Promotion to **manager** requires an admin via `PATCH /api/v1/auth/users/{id}/role`.

---

## Services & ports

Only the gateway and Postgres expose ports to the host. Internal services
listen on container port `8000` and are reachable through NGINX at
`/api/v1/<service>/`.

| Service | Container | Internal port | Public path | Role |
|---|---|---|---|---|
| nginx | `eco_nginx` | 80, 443 *(host)* | `/`, `/api/v1/*` | TLS + gateway |
| postgres | `eco_postgres` | 5432 *(host)* | — | Database |
| migrations | `eco_migrations` | — | — | One-shot Alembic upgrade |
| frontend | `eco_frontend` | 3000 *(internal)* | `/` | React SPA |
| auth-service | `eco_auth` | 8000 | `/api/v1/auth/` | RS256 JWT, RBAC |
| project-service | `eco_project` | 8000 | `/api/v1/projects/` | Projects + measures + full-analysis orchestrator |
| financial-service | `eco_financial` | 8000 | `/api/v1/financial/` | NPV, IRR, BCR, Payback, LCCA |
| eco-impact-service | `eco_eco` | 8000 | `/api/v1/eco/` | CO₂ reduction, regulatory damage |
| multi-criteria-service | `eco_multicriteria` | 8000 | `/api/v1/multicriteria/` | AHP, TOPSIS |
| scenario-service | `eco_scenario` | 8000 | `/api/v1/scenario/` | What-if, sensitivity, break-even |
| comparison-service | `eco_comparison` | 8000 | `/api/v1/comparison/` | Cross-method ranking, Pareto |
| report-service | `eco_report` | 8000 | `/api/v1/reports/` | PDF + Excel |

Each service has Swagger docs at `/api/v1/<service>/docs` (disabled when
`ENVIRONMENT=production`).

NGINX rate-limit zones: `auth` 3 req/s burst 5, `api` 10 req/s burst 20
(reports get burst 10 with a 120 s read timeout for PDF generation).

---

## API reference

All paths below are public paths (the gateway prefix is included). Every
endpoint except `/health`, `/auth/login`, and `/auth/register` requires a
`Bearer` JWT.

### Auth — `/api/v1/auth/`

| Method | Path | Notes |
|---|---|---|
| POST | `/register` | Self-registration as `analyst` |
| POST | `/login` | OAuth2 password flow → RS256 access token |
| GET | `/me` | Current user profile |
| GET | `/users` | Admin only |
| PATCH | `/users/{user_id}/role` | Admin only — promote/demote |
| GET | `/health` | Liveness |
| GET | `/internal/verify` | Gateway-internal `auth_request` target |

### Projects — `/api/v1/projects/`

| Method | Path | Notes |
|---|---|---|
| POST | `/` | Create project |
| GET | `/` | List (paginated, owner-scoped for analysts) |
| GET | `/{project_id}` | Read |
| PATCH | `/{project_id}` | Update name/description |
| DELETE | `/{project_id}` | Delete (cascades to measures + results) |
| GET | `/{project_id}/alternatives` | Portfolio of measures |
| POST | `/{project_id}/measures` | Add measure |
| PATCH | `/{project_id}/measures/{measure_id}` | Update measure |
| DELETE | `/{project_id}/measures/{measure_id}` | Remove measure |
| PATCH | `/{project_id}/status` | Manager/admin status override |
| PATCH | `/{project_id}/approve` | Manager/admin |
| PATCH | `/{project_id}/reject` | Manager/admin (with comment) |
| POST | `/{project_id}/analyze/full` | **Orchestrator**: runs financial + eco + AHP + TOPSIS + sensitivity + comparison concurrently |

### Financial analysis — `/api/v1/financial/`

| Method | Path | Returns |
|---|---|---|
| POST | `/analyze` | NPV, IRR, BCR, simple + discounted payback, LCCA, year-by-year breakdown |
| POST | `/analyze/portfolio` | Same, for a list of measures with shared discount rate |
| POST | `/projects/{project_id}/analyze` | Run + persist as `FinancialResult` row |
| GET | `/projects/{project_id}/results` | Paginated history |
| GET | `/results/{result_id}` | Single persisted result |

### Ecological impact — `/api/v1/eco/`

| Method | Path | Returns |
|---|---|---|
| POST | `/analyze` | CO₂ reduction (t/yr), carbon footprint, averted damage (UA / EU regulatory or legacy linear), `cost_per_tonne_reduction_uah` over project lifespan, optional pollutant breakdown |
| POST | `/analyze/portfolio` | Aggregated portfolio totals |
| GET | `/emission-factors` | IPCC/Min Eco emission table |
| GET | `/damage-coefficients` | Regulatory damage coefficients (UA & EU) per pollutant |
| POST | `/projects/{project_id}/analyze` | Persist |
| GET | `/projects/{project_id}/results` | History |
| GET | `/results/{result_id}` | One |

### Multi-criteria — `/api/v1/multicriteria/`

| Method | Path | Notes |
|---|---|---|
| POST | `/ahp` | Saaty pairwise matrix → eigenvector weights + CR check |
| POST | `/topsis` | Decision matrix + caller-supplied weights |
| POST | `/combined` | AHP feeds weights into TOPSIS in one call (rejects when CR ≥ 0.1) |
| POST | `/projects/{project_id}/ahp` | Persist AHP |
| POST | `/projects/{project_id}/topsis` | Persist TOPSIS |
| GET | `/projects/{project_id}/ahp/results` | Paginated AHP history |
| GET | `/projects/{project_id}/topsis/results` | Paginated TOPSIS history |
| GET | `/results/ahp/{result_id}` | One AHP |
| GET | `/results/topsis/{result_id}` | One TOPSIS |

### Scenario — `/api/v1/scenario/`

| Method | Path | Notes |
|---|---|---|
| POST | `/whatif` | Recalculate NPV under parameter overrides |
| POST | `/sensitivity` | Tornado-chart data — each parameter varied independently, sorted by impact |
| POST | `/breakeven` | Brent's method finds the parameter values where NPV = 0 |
| POST | `/projects/{project_id}/whatif` etc. | Project-scoped + persisted variants |
| GET | `/projects/{project_id}/results` | History |
| GET | `/results/{result_id}` | One |

### Comparison — `/api/v1/comparison/`

| Method | Path | Notes |
|---|---|---|
| POST | `/compare` | Cross-method consensus + conflict detection + Pareto front |
| POST | `/compare/portfolio` | Alias of `/compare` |
| POST | `/projects/{project_id}/compare` | Pulls financial + eco + AHP + TOPSIS results from sibling services and persists |
| GET | `/projects/{project_id}/results` | History |
| GET | `/results/{result_id}` | One |

### Reports — `/api/v1/reports/`

| Method | Path | Notes |
|---|---|---|
| POST | `/generate` | PDF from a fully-formed `ReportInput` |
| POST | `/generate/excel` | Excel from a fully-formed `ReportInput` |
| POST | `/projects/{project_id}/pdf` | Pulls all sibling results, generates PDF |
| POST | `/projects/{project_id}/excel` | Same, Excel |

PDF sections: project parameters · financial table & charts · eco impact ·
consolidated ranking · AHP weights · TOPSIS ranking · sensitivity tornado ·
multi-criteria radar · recommendation justification.

---

## Implemented methods

### Financial (`services/financial-service/calculator.py`)

| Method | Formula |
|---|---|
| **NPV** | `Σ CFₜ / (1+r)ᵗ`, with `cash_flows[0]` as the t=0 outlay |
| **IRR** | Sign-change bracket check, then `scipy.optimize.brentq` over `[-0.999, +10.0]`; returns `None` with `converged=False` when no real root exists |
| **BCR** | `Σ PV(savings) / (initial_investment + Σ PV(opex))`, years 1…N |
| **Simple Payback** | `initial_investment / annual_net_cash_flow` (closed-form for flat cash flows) |
| **Discounted Payback** | Cumulative discounted cash flow with linear in-year interpolation |
| **LCCA** | `initial + PV(opex) + PV(maintenance) − PV(residual_value)` (maintenance & residual are optional inputs) |

### Multi-criteria (`services/multi-criteria-service/`)

* **AHP** (`ahp.py`) — validates the matrix is square, reciprocal, and on the
  Saaty 1–9 scale; computes weights as the principal eigenvector via
  `numpy.linalg.eig`; computes `CI = (λ_max − n)/(n−1)` and
  `CR = CI / RI` using the Saaty RI table
  `[0, 0, 0.58, 0.9, 1.12, 1.24, 1.32, 1.41, 1.45, 1.49]`; rejects with a
  warning when `CR ≥ 0.1`. Cost criteria are auto-flipped during scoring.
* **TOPSIS** (`topsis.py`) — six classical steps: column-wise L2
  normalisation, weight application, ideal/anti-ideal extraction with
  benefit/cost direction, Euclidean distances `D⁺` and `D⁻`, closeness
  coefficient `C = D⁻ / (D⁺ + D⁻)`, descending rank.

### Eco impact (`services/eco-impact-service/calculator.py`)

* IPCC + Ukrainian National Inventory emission factors for `natural_gas`,
  `electricity`, `coal`, `diesel`, `heating_oil`.
* Carbon footprint with `GWP_CO2 = 1.0` (IPCC AR6, 100-year horizon).
* Averted damage — choice of methodology:
  * `UA` — Ministry of Environmental Protection coefficient table
    (CO₂, NOx, SOx, PM, VOC).
  * `EU` — ExternE / EEA damage cost handbook (converted to UAH/t).
  * `legacy` — single linear `damage_coefficient` (default).
* `cost_per_tonne_reduction_uah = initial_investment / (annual_co2 × lifespan)`
  when both are supplied.
* `MeasureType` enum: insulation, equipment replacement, treatment facility,
  renewable energy, process optimisation, transport.
* `PollutantCategory` enum: co2, nox, sox, pm, voc — each contributes via
  per-fuel co-emission factors.

### Scenario (`services/scenario-service/calculator.py`)

* **What-if** — recomputes NPV under explicit parameter overrides and
  reports `(base_npv, new_npv, npv_change, npv_change_percent)`.
* **Sensitivity** — varies each parameter independently across `±X%` in
  `2·steps + 1` points; emits min/max/impact_absolute/impact_percent;
  results are sorted descending by `impact_absolute` for direct
  rendering as a tornado chart.
* **Break-even** — `scipy.optimize.brentq` (`xtol=1e-4`, `maxiter=200`)
  finds the parameter value where `NPV = 0` for `expected_savings`,
  `initial_investment`, `discount_rate`; brute-force scan 1…100 for
  `lifetime_years`.

### Comparison (`services/comparison-service/calculator.py`)

* Per-method rankings (NPV, IRR, BCR, payback, CO₂, AHP, TOPSIS).
* **Consensus** — average rank across all available methods.
* **Conflicts** — flagged when `max(rank) − min(rank) > n/2`.
* **Pareto front** — non-dominated set on (cost ↓, effect ↑).

---

## Database schema

Defined in `db/models.py`, migrated via Alembic (`alembic/versions/`).

* `users` — `id`, `email` (unique), `username` (unique),
  `hashed_password`, `role` (`analyst|manager|admin`), `created_at`,
  `updated_at`.
* `projects` — `id`, `name`, `description`, `owner_id` → `users.id`
  (cascade delete), `status` (`pending|approved|rejected`),
  `manager_comment`, timestamps. Indexed on `owner_id`, `status`.
* `measures` — `id`, `project_id` → `projects.id` (cascade),
  `name`, `measure_type` (`insulation|equipment|treatment|renewable`),
  `initial_investment`, `operational_cost`, `expected_savings`,
  `lifetime_years`, `emission_reduction`. Indexed on `project_id`.
* Result tables: `financial_results`, `ahp_results`, `topsis_results`,
  `eco_results`, `scenario_results`, `comparison_results`. Each has
  `id` (BigInt), `project_id` FK, `input_data` (JSONB), `result_data`
  (JSONB), `version`, `status`, timestamps.

Migrations are idempotent and round-trip safe — verified in CI by an
upgrade → downgrade → upgrade cycle against a live Postgres 15.

---

## Environment variables

All variables live in `.env` (see `.env.example`).

| Variable | Default / example | Used by |
|---|---|---|
| `ENVIRONMENT` | `development` / `production` | All services (disables `/docs` in prod) |
| `WORKERS` | `4` | gunicorn worker count |
| `POSTGRES_USER` | `ecouser` | postgres |
| `POSTGRES_PASSWORD` | *(set strong)* | postgres |
| `POSTGRES_DB` | `ecodb` | postgres |
| `DATABASE_URL` | `postgresql://ecouser:…@postgres:5432/ecodb` | All DB-backed services |
| `JWT_PRIVATE_KEY_PATH` | `/run/keys/jwt_private.pem` | auth-service only |
| `JWT_PUBLIC_KEY_PATH` | `/run/keys/jwt_public.pem` | All services (verification) |
| `JWT_ISSUER` | `eco-analysis-auth` | All |
| `JWT_AUDIENCE` | `eco-analysis-api` | All |
| `JWT_EXPIRE_MINUTES` | `60` | auth-service |
| `BCRYPT_ROUNDS` | `12` (min `10` enforced) | auth-service |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `ADMIN_EMAIL` | first-boot bootstrap | auth-service |
| `CORS_ALLOWED_ORIGINS` | `http://localhost,http://127.0.0.1,https://localhost` | All |
| `TLS_CERT_PATH` / `TLS_KEY_PATH` | `/etc/nginx/ssl/{cert,key}.pem` | nginx |

The JWT private key lives **only** in the auth-service container; every
other service mounts the public key read-only and verifies tokens locally
(no central token-introspection round-trip).

---

## Testing & CI

```bash
# Run the full unit suite (63 tests)
pytest tests/unit/

# Targeted runs
pytest tests/unit/test_financial_calculator.py
pytest tests/unit/test_ahp.py tests/unit/test_topsis.py

# Lint + types
ruff check .
ruff format --check .
pyright

# Frontend
cd frontend
npm install
npm run lint
npm run build
```

The unit suite covers:

| File | Tests | Subject |
|---|---:|---|
| `test_financial_calculator.py` | 17 | NPV, IRR, BCR, payback, LCCA, end-to-end `analyze_measure` |
| `test_ahp.py` | 9 | Saaty validation, eigenvector, CR check, scoring |
| `test_topsis.py` | 7 | Six TOPSIS steps, benefit/cost orientation |
| `test_scenario_calculator.py` | 11 | What-if, sensitivity, break-even |
| `test_envelope.py` | 9 | Pagination + envelope contract |
| `test_circuit_breaker.py` | 5 | Failure threshold + half-open recovery |
| `test_orchestration.py` | 5 | `InternalAPI` + result unwrapping |
| **Total** | **63** | |

CI (`.github/workflows/ci.yml`) runs four jobs on push and PR:

1. **Lint** — ruff (check + format), pyright (warnings only).
2. **Test** — pytest with `--cov-report=xml --junitxml=junit.xml`.
3. **Build** — matrix Docker build for all eight services with GHA cache.
4. **Migrations** — Alembic upgrade → downgrade → upgrade against a live
   Postgres 15 service container.

Performance benchmarks live in `benchmarks/scaling.py`
(AHP / TOPSIS / sensitivity / break-even at varying input sizes).

---

## Repository layout

```
eco-analysis/
├── alembic/                  # versioned database migrations
│   └── versions/
│       ├── 0001_initial_schema.py
│       └── 0002_owner_username_to_owner_id.py
├── benchmarks/               # scaling.py + README
├── db/                       # SQLAlchemy models + base + migrations Dockerfile
├── docs/                     # algorithms.md, api.md, architecture.md
├── eco_common/               # shared library: api_setup, auth, envelope,
│                             # http_client (retry + circuit breaker), internal,
│                             # logging_setup, metrics, exceptions
├── frontend/                 # React 19 + Vite SPA
│   ├── src/
│   │   ├── api/              # axios client + envelope unwrap + endpoints
│   │   ├── components/       # Navbar, ErrorBoundary, TornadoMini
│   │   ├── context/          # AuthContext (JWT + role flags)
│   │   ├── pages/            # Login, Register, Dashboard, Project,
│   │   │                     # Analysis, MultiCriteria, Scenario, Admin
│   │   ├── App.jsx, main.jsx
│   │   └── index.css         # design tokens + shared components
│   ├── Dockerfile
│   └── vite.config.js
├── keys/                     # RS256 keypair (mounted into containers)
├── nginx/
│   ├── nginx.conf            # gateway, TLS, JWT auth_request, rate limits
│   ├── errors/               # 404 / 5xx pages
│   └── ssl/                  # self-signed dev cert
├── scripts/
│   ├── generate_keys.sh      # RS256 keypair
│   └── generate_tls.sh       # self-signed nginx cert
├── services/
│   ├── auth-service/
│   ├── project-service/
│   ├── financial-service/
│   ├── eco-impact-service/
│   ├── multi-criteria-service/
│   ├── scenario-service/
│   ├── comparison-service/
│   └── report-service/
├── tests/unit/               # 63 unit tests
├── .github/workflows/ci.yml  # lint · test · build · migrations round-trip
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── pyproject.toml
└── README.md
```
