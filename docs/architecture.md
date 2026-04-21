# Архітектура системи

## Загальний огляд

Платформа реалізована як набір незалежних мікросервісів, що спілкуються через
HTTP/REST за єдиним API-контрактом `{data, error, meta}`. Шлюз **nginx**
виконує маршрутизацію за префіксом `/api/v1/<service>/...` і перевіряє
JWT-токени через `auth_request` перед пропусканням трафіку до бекенду.

## Склад компонентів

| Шар | Компонент | Технології |
|-----|-----------|------------|
| Клієнт | SPA | React 18, Recharts, axios |
| Шлюз | Reverse proxy + auth_request | nginx |
| Сервіси | 8× FastAPI | Python 3.12, gunicorn + UvicornWorker |
| Сховище | Реляційна БД | PostgreSQL 15 + Alembic міграції |
| Спостережуваність | Логи + метрики | структуроване JSON-логування |

## Карта мікросервісів

```
                         ┌──────────────────────┐
                         │   Frontend (React)   │
                         └──────────┬───────────┘
                                    │  /api/v1/*
                         ┌──────────▼───────────┐
                         │    nginx gateway     │
                         │  (auth_request JWT)  │
                         └──────────┬───────────┘
       ┌──────────┬─────────┬──────┴────┬──────────┬──────────┬─────────┐
       ▼          ▼         ▼           ▼          ▼          ▼         ▼
   auth    project   financial  eco-impact  multi-crit  scenario  comparison
                                                                  + report
                                    │
                         ┌──────────▼───────────┐
                         │   PostgreSQL + JSONB │
                         └──────────────────────┘
```

## Відповідальність сервісів

- **auth-service** — реєстрація, логін, RS256 JWT, RBAC (`analyst`, `manager`,
  `admin`).
- **project-service** — CRUD проєктів і заходів, workflow затвердження
  (`pending → approved/rejected`).
- **financial-service** — NPV, IRR (Brent), BCR, simple/discounted payback,
  LCCA з порічною деталізацією.
- **eco-impact-service** — CO₂ reduction (IPCC emission factors), carbon
  footprint, averted damage (грн/рік), вартість тонни CO₂.
- **multi-criteria-service** — AHP (головний власний вектор, CR<0.1), TOPSIS
  (Hwang-Yoon), комбінований AHP→TOPSIS пайплайн.
- **scenario-service** — what-if, sensitivity з tornado-даними,
  break-even-пошук за expected_savings / initial_investment / discount_rate /
  lifetime_years.
- **comparison-service** — консенсусний ранжир, Pareto-фронт (NPV↔CO₂),
  детектор суперечливих заходів.
- **report-service** — PDF (ReportLab) та Excel (openpyxl) з секціями
  Financial / Eco / Ranking / AHP / TOPSIS / Sensitivity.

## Потік запиту

1. Клієнт шле `Authorization: Bearer <JWT>` на `/api/v1/<service>/...`.
2. nginx робить `auth_request` до `auth-service/internal/verify`, який
   перевіряє підпис RS256 і повертає `X-User-Id`, `X-User-Role`.
3. Запит проксиіться у внутрішню мережу до відповідного сервісу з уже
   валідованими заголовками ідентичності.
4. Сервіс виконує бізнес-логіку, пише результат у JSONB-таблицю результатів
   (за потреби) і відповідає у форматі `{data, error, meta}`.
5. axios-інтерцептор на фронтенді розгортає обгортку й передає `data` далі
   (бінарні blob-и проходять без змін — див. `frontend/src/api/index.js`).

## Моделі даних

`db/models.py` — єдине джерело істини для схеми БД. Всі сервіси імпортують
SQLAlchemy-моделі з цього модуля (без дублікатів).

Таблиці результатів (`financial_results`, `ahp_results`, `topsis_results`,
`eco_results`, `scenario_results`, `comparison_results`) використовують
`JSONB` для `input_data`/`result_data` — це дозволяє калькуляторам
еволюціонувати без змін схеми БД; поле `version` уможливлює безпечну
міграцію формату.

## Безпека

- RS256 JWT підписується приватним ключем у `keys/jwt_private.pem`;
  гейтвей і сервіси перевіряють підпис публічним ключем
  `keys/jwt_public.pem` (завантажуються з env `JWT_PUBLIC_KEY_PATH`).
- bcrypt — для хешування паролів.
- Docker-образи стартують під non-root UID 1001.
- rate-limit (slowapi) ставиться на login і register у auth-service.
- Circuit breaker (`eco_common.circuit_breaker`) захищає cross-service
  виклики в report-service.

## Якість і деплой

- `ruff check` + `ruff format` — лінт і форматування (конфіг у
  `pyproject.toml`).
- `pyright` — статична перевірка типів (basic mode, CI — warnings-only).
- `pytest` + `pytest-cov` — юніт-тести мікросервісів (58+ тестів).
- Alembic round-trip (up/down/up) виконується в CI проти реального Postgres.
- Docker multi-stage образи; `docker-compose.yml` піднімає повний стек
  локально.
