# 🌿 Eco Analysis — Technico-Economic Analysis System

> Мікросервісна веб-система техніко-економічного аналізу впровадження екологічних заходів.
> Дипломний проект — КПІ ім. Ігоря Сікорського, 2026.

---

## Зміст

- [Архітектура](#архітектура)
- [Мікросервіси](#мікросервіси)
- [Технологічний стек](#технологічний-стек)
- [Швидкий старт](#швидкий-старт)
- [Доступи за замовчуванням](#доступи-за-замовчуванням)
- [Ролі користувачів](#ролі-користувачів)
- [Функціонал](#функціонал)
- [API convention](#api-convention)
- [Observability & ops](#observability--ops)
- [Розробка та тестування](#розробка-та-тестування)
- [Структура проєкту](#структура-проєкту)

---

## Архітектура

```
┌─────────────────────────────────────────────────────────┐
│                   Browser (React 19)                    │
│          http://localhost  (port 80 via Nginx)          │
└────────────────────────┬────────────────────────────────┘
                         │  /api/v1/*   +  envelope {data, error, meta}
┌────────────────────────▼────────────────────────────────┐
│                   Nginx API Gateway                     │
│    TLS · rate limiting · security headers · routing     │
└──┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬─────┘
   │      │      │      │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
 auth  project  fin   eco   multi  scen  comp  report
 :8000  :8000  :8000 :8000  :8000 :8000 :8000  :8000
   │      │      │     │     │     │     │     │
   │      │      └─────┴──┬──┴─────┴─────┴─────┘
   │      │               │  httpx retry + circuit breaker
   │      │               │  + X-Request-ID propagation
   ▼      ▼               ▼
 PostgreSQL 15   ←  Alembic migrations (dedicated container, runs once)
 (users, projects, AHP/TOPSIS JSONB results, …)
```

Усі сервіси будуються з однакового багатоступеневого Dockerfile, працюють
під непривілейованим UID 1001, обслуговуються через `gunicorn +
UvicornWorker`, а cross-service виклики йдуть через `eco_common.http_client`
із автоматичним retry, circuit-breaker'ом і X-Request-ID propagation.

---

## Мікросервіси

| Сервіс | Контейнер | Опис | Swagger |
|--------|-----------|------|---------|
| **auth-service** | `eco_auth` | RS256 JWT, реєстрація, адмінський bootstrap ролей | `/api/v1/auth/docs` |
| **project-service** | `eco_project` | CRUD проєктів та заходів, workflow затвердження | `/api/v1/projects/docs` |
| **financial-service** | `eco_financial` | NPV, IRR (Brent's method), BCR, Payback, LCCA | `/api/v1/financial/docs` |
| **eco-impact-service** | `eco_impact` | Вуглецевий слід CO₂, відвернений збиток, 5 видів палива | `/api/v1/eco/docs` |
| **multi-criteria-service** | `eco_multicriteria` | AHP (принциповий власний вектор, CR) + TOPSIS | `/api/v1/multicriteria/docs` |
| **scenario-service** | `eco_scenario` | What-if, tornado sensitivity, Break-even (brentq) | `/api/v1/scenario/docs` |
| **comparison-service** | `eco_comparison` | Консенсусний рейтинг, Pareto-фронт, виявлення конфліктів | `/api/v1/comparison/docs` |
| **report-service** | `eco_report` | PDF (ReportLab + matplotlib + DejaVu cyrillic) + Excel | `/api/v1/reports/docs` |
| **migrations** | `eco_migrations` | Alembic — одноразовий запуск, `depends_on: service_completed_successfully` | — |

---

## Технологічний стек

| Шар | Технології |
|-----|-----------|
| **Frontend** | React 19, React Router 6, Recharts 3, Axios |
| **Backend** | FastAPI 0.111, Pydantic v2, SQLAlchemy 2, Python 3.11 |
| **Database** | PostgreSQL 15, JSONB, Alembic migrations |
| **AuthN/Z** | RS256 JWT (python-jose), bcrypt (passlib), role-based guards |
| **Algorithms** | NumPy `linalg.eig` (AHP), SciPy `brentq` (IRR / break-even), Hwang–Yoon TOPSIS |
| **Reports** | ReportLab (PDF), openpyxl (Excel), matplotlib |
| **Observability** | structlog JSON, Prometheus metrics, X-Request-ID propagation |
| **Ops** | Docker Compose, multi-stage images, gunicorn + UvicornWorker, non-root UID 1001, Nginx (TLS, rate limiting) |
| **Quality** | pytest + pytest-cov, ruff, pyright, pre-commit, GitHub Actions CI |

---

## Швидкий старт

### Вимоги

- Docker 24+ та Docker Compose v2
- Python 3.11+ (для локальних тестів поза контейнерами)
- Мінімум 4 GB RAM

### 1. Клонування

```bash
git clone https://github.com/malynkodd/eco-analysis.git
cd eco-analysis
```

### 2. Згенеруй ключі та сертифікати

```bash
./scripts/generate_keys.sh   # → keys/jwt_private.pem + keys/jwt_public.pem
./scripts/generate_tls.sh    # → nginx/ssl/*.pem (self-signed, dev only)
```

### 3. Налаштуй `.env`

```bash
cp .env.example .env
```

Мінімальний вміст `.env` (безпечно для dev, **обов'язково змінити у
production**):

```env
ENVIRONMENT=development
WORKERS=4

POSTGRES_USER=ecouser
POSTGRES_PASSWORD=ecopassword
POSTGRES_DB=ecodb
DATABASE_URL=postgresql+psycopg2://ecouser:ecopassword@postgres:5432/ecodb

JWT_PRIVATE_KEY_PATH=/run/keys/jwt_private.pem
JWT_PUBLIC_KEY_PATH=/run/keys/jwt_public.pem
JWT_ISSUER=eco-analysis
JWT_AUDIENCE=eco-analysis-clients
JWT_EXPIRE_MINUTES=60

ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@example.com

CORS_ALLOWED_ORIGINS=http://localhost
```

### 4. Запуск

```bash
docker compose up --build
```

Контейнери стартують у такому порядку:

1. **postgres** — чекає healthcheck.
2. **migrations** — `alembic upgrade head`, потім зупиняється.
3. **8 app-сервісів** — паралельно, кожен з `wait_for_db.py` (де потрібно) і
   власним HTTP healthcheck `/health`.
4. **nginx** — стартує лише коли всі backend'и здорові.

Повний reset бази:

```bash
docker compose down -v && docker compose up --build
```

### 5. Використання

| URL | Опис |
|-----|------|
| **http://localhost** | Основний веб-інтерфейс |
| `http://localhost/api/v1/auth/docs` | Swagger — Auth |
| `http://localhost/api/v1/projects/docs` | Swagger — Projects |
| `http://localhost/api/v1/financial/docs` | Swagger — Financial |
| `http://localhost/api/v1/eco/docs` | Swagger — Eco Impact |
| `http://localhost/api/v1/multicriteria/docs` | Swagger — Multi-Criteria |
| `http://localhost/api/v1/scenario/docs` | Swagger — Scenario |
| `http://localhost/api/v1/comparison/docs` | Swagger — Comparison |
| `http://localhost/api/v1/reports/docs` | Swagger — Reports |

---

## Доступи за замовчуванням

| Логін | Пароль | Роль |
|-------|--------|------|
| `admin` | `admin123` | Admin — повний доступ + управління користувачами |

Акаунт адміна створюється автоматично при першому запуску (`ADMIN_*` env).
Нові користувачі реєструються з роллю **Analyst**; роль **Manager** можна
лише підвищити через адмін-панель.

---

## Ролі користувачів

| Роль | Може | Не може |
|------|------|---------|
| **Analyst** | Створювати проєкти, додавати заходи, запускати аналіз, завантажувати PDF/Excel | Бачити чужі проєкти, затверджувати |
| **Manager** | Бачити ВСІ проєкти, затверджувати/відхиляти з коментарем | Створювати проєкти, запускати аналіз |
| **Admin** | Все що може Analyst і Manager + управління ролями через `/admin` | Змінювати власну роль |

---

## Функціонал

### 💰 Фінансовий аналіз (`financial-service`)

- **NPV** — чиста приведена вартість з налаштовуваною ставкою дисконтування
- **IRR** — Brent's method у діапазоні [-99 %, +1000 %]; якщо корінь не
  існує, повертається `IRRResult(value=None, converged=False)` замість
  магічного `-1`
- **BCR** — PV(savings) / (investment + PV(opex))
- **Simple Payback** — `None` коли річний cash-flow ≤ 0
- **Discounted Payback** — інтерпольований рік, коли кумулятивний DCF ≥ 0
- **LCCA** — аналіз вартості життєвого циклу
- Повна таблиця грошових потоків по роках

### 🎯 Багатокритеріальний аналіз (`multi-criteria-service`)

- **AHP** — принциповий власний вектор через `numpy.linalg.eig`; Saaty
  1–9 scale + reciprocity validation; λ_max → CR; benefit/cost
  нормалізація альтернатив
- **TOPSIS** — Hwang & Yoon, нормалізована вага, відстань до ідеалу/анти-ідеалу
- Спільний workflow AHP + TOPSIS з виявленням розбіжностей і radar chart

### 📈 Сценарне моделювання (`scenario-service`)

- **What-if** — довільна зміна 5 параметрів, NPV delta + relative impact
- **Sensitivity (tornado)** — `impact_absolute` (грн) + `impact_percent`
- **Break-even** — SciPy `brentq` з fallback-верхніми межами для
  нульових базових значень

### 🌿 Екологічний ефект (`eco-impact-service`)

- Зменшення CO₂ для 5 видів палива (електроенергія, газ, вугілля, дизель, мазут)
- Відвернений економічний збиток (грн / тонна CO₂), монетизація сліду

### 📊 Порівняння та рейтинг (`comparison-service`)

- Консенсусний рейтинг по NPV, IRR, BCR, Payback, CO₂, AHP, TOPSIS —
  кожен метод рангує; фінальний консенсус = сума рангів
- `Optional[float]` safe-sorting: `None` завжди потрапляє в хвіст для
  «higher-is-better» і в голову для «lower-is-better»
- Pareto-фронт (NPV vs CO₂), виявлення конфліктних заходів

### 📄 Звіти (`report-service`)

- **PDF**: 6 вбудованих графіків (NPV bar, IRR+BCR, кумулятивний DCF,
  CO₂, radar, consensus) + DejaVu для кирилиці
- **Excel**: 5 аркушів — Summary, Financial, Environmental, Sensitivity, AHP/TOPSIS

### ✅ Workflow затвердження

Аналітик створює → **Pending** → Менеджер затверджує / відхиляє з коментарем.

---

## API convention

### Базовий префікс

Усі endpoints живуть під `/api/v1/<service>/...`. Версіонування виконується
префіксом шляху, а не заголовком.

### Response envelope

Кожна JSON-відповідь обгорнута в стандартний envelope — включно з
помилками та списками:

```jsonc
{
  "data": { /* payload або null */ },
  "error": {
    "code": "not_found",
    "message": "Project not found",
    "details": { "id": 42 }
  } /* або null */,
  "meta": {
    "request_id": "9f1c…",
    "timestamp": "2026-04-19T10:23:45.123+00:00",
    "pagination": { "page": 1, "limit": 20, "total": 57, "pages": 3 } /* або null */
  }
}
```

Binary-endpoints (`application/pdf`, `application/vnd.openxmlformats*`) не
обгортаються.

### Коди помилок

| HTTP | `error.code` |
|------|--------------|
| 400 | `bad_request` |
| 401 | `unauthorized` |
| 403 | `forbidden` |
| 404 | `not_found` |
| 409 | `conflict` |
| 422 | `validation_error` / `unprocessable_entity` |
| 429 | `too_many_requests` |
| 500 | `internal_error` |
| 502 | `bad_gateway` |
| 503 | `service_unavailable` |

### Пагінація

Ендпоїнти-списки приймають `?page=1&limit=20` (limit ≤ 100). Клієнт читає
`meta.pagination.pages` щоб зрендерити пагінатор.

---

## Observability & ops

| Сигнал | Де |
|--------|-----|
| **Liveness** | `GET /health` → 200 на кожному сервісі |
| **Metrics** | `GET /metrics` → Prometheus text format |
| **Request tracing** | `X-Request-ID` header echo-back + structlog `request_id` field + httpx propagation |
| **Logs** | JSON на stdout; uvicorn/gunicorn перехоплені в тому ж форматі |
| **Restart policy** | `unless-stopped` на кожному app-контейнері |

Prometheus-збирані метрики:

- `http_requests_total{method, path, status}` — Counter
- `http_request_duration_seconds{method, path}` — Histogram з гранулярними bucket'ами
- `http_requests_in_flight{method}` — Gauge

Cardinality обмежена шаблоном маршруту (`/projects/{project_id}`), а не
конкретним id.

---

## Розробка та тестування

### Unit tests + coverage

```bash
pip install pytest pytest-cov fastapi pydantic[email] sqlalchemy \
            numpy scipy httpx structlog prometheus-client \
            python-jose[cryptography]

pytest tests/unit --cov=eco_common \
                  --cov=services/multi-criteria-service \
                  --cov=services/financial-service \
                  --cov=services/scenario-service \
                  --cov-report=term-missing
```

Тести покривають калькулятори (AHP, TOPSIS, фінансовий, сценарний),
envelope + pagination, і circuit breaker.

### Lint + types

```bash
pip install ruff==0.4.10 pyright==1.1.370
ruff check .
ruff format --check .
pyright
```

### Pre-commit

```bash
pip install pre-commit && pre-commit install
pre-commit run --all-files
```

### CI

`.github/workflows/ci.yml` виконує lint → tests → Docker build (matrix по 8
сервісах) → Alembic round-trip (`upgrade head → downgrade base → upgrade head`)
проти короткоживучого PostgreSQL-container'а.

---

## Структура проєкту

```
eco-analysis/
├── docker-compose.yml                # 10 сервісів + healthchecks + restart policies
├── .env.example
├── pyproject.toml                    # ruff, pyright, pytest, coverage
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml          # lint → test → build → migrations
├── alembic/                          # SQLAlchemy migrations
├── alembic.ini
├── nginx/
│   └── nginx.conf                    # TLS, rate limiting, security headers
├── scripts/
│   ├── generate_keys.sh              # JWT RSA keypair
│   └── generate_tls.sh               # self-signed TLS cert
├── keys/                             # (gitignored) JWT keys
├── db/                               # Shared SQLAlchemy models
├── eco_common/                       # Package shared by every service
│   ├── api_setup.py                  # create_app() factory
│   ├── auth.py                       # RS256 JWT verification
│   ├── envelope.py                   # {data, error, meta} JSONResponse + paginate()
│   ├── exceptions.py                 # CircuitBreakerOpen, RemoteServiceError, …
│   ├── http_client.py                # httpx retry + circuit breaker + X-Request-ID
│   ├── internal.py                   # Typed internal-API wrappers
│   ├── logging_setup.py              # structlog JSON + uvicorn/gunicorn interception
│   └── metrics.py                    # Prometheus http_* collectors + /metrics
├── services/
│   ├── auth-service/                 # RS256 issuing, admin bootstrap
│   ├── project-service/              # CRUD + approval workflow, RBAC
│   ├── financial-service/            # NPV, IRR (brentq), BCR, Payback, LCCA
│   ├── eco-impact-service/           # CO₂, avoided damage
│   ├── multi-criteria-service/       # AHP eigenvector + TOPSIS
│   ├── scenario-service/             # What-if, Sensitivity, Break-even
│   ├── comparison-service/           # Consensus, Pareto, conflicts
│   └── report-service/               # PDF + Excel
├── tests/
│   ├── conftest.py                   # JWT bootstrap + per-service module loader
│   └── unit/                         # 58 unit tests
└── frontend/
    └── src/
        ├── api/index.js              # /api/v1/*, envelope unwrap, auth interceptor
        ├── context/AuthContext.jsx
        ├── pages/{Login,Register,Dashboard,Project,Analysis,Scenario,MultiCriteria,Admin}.jsx
        └── components/{Navbar,TornadoMini,ErrorBoundary}.jsx
```
