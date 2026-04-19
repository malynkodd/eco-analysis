# API-специфікація

Усі ендпоінти живуть під префіксом `/api/v1/<service>/...` і повертають
обгортку:

```json
{
  "data": { ... },
  "error": null,
  "meta": { "request_id": "...", "duration_ms": 12.4 }
}
```

На помилці:

```json
{
  "data": null,
  "error": { "code": "VALIDATION_ERROR", "message": "...", "details": {...} },
  "meta": { "request_id": "...", "duration_ms": 3.1 }
}
```

Повну OpenAPI-схему кожний сервіс публікує на `/docs` (Swagger UI) та
`/openapi.json` (машиночитне джерело).

## Аутентифікація

Усі ендпоінти (крім `login`, `register`, `healthz`) вимагають
`Authorization: Bearer <JWT>`.

| Метод | Шлях | Роль | Опис |
|-------|------|------|------|
| POST | `/api/v1/auth/register` | — | Реєстрація (завжди роль `analyst`) |
| POST | `/api/v1/auth/login` | — | OAuth2 password flow → JWT |
| GET  | `/api/v1/auth/me` | auth | Поточний користувач |
| GET  | `/api/v1/auth/users` | admin | Список користувачів |
| PATCH | `/api/v1/auth/users/{id}/role` | admin | Зміна ролі |

## Проєкти і заходи

| Метод | Шлях | Роль |
|-------|------|------|
| GET | `/api/v1/projects/` | auth |
| POST | `/api/v1/projects/` | analyst |
| GET | `/api/v1/projects/{id}` | auth |
| DELETE | `/api/v1/projects/{id}` | owner/admin |
| POST | `/api/v1/projects/{id}/measures` | analyst |
| DELETE | `/api/v1/projects/{id}/measures/{mid}` | owner |
| PATCH | `/api/v1/projects/{id}/status` | manager/admin |
| PATCH | `/api/v1/projects/{id}/approve` | manager/admin |
| PATCH | `/api/v1/projects/{id}/reject` | manager/admin |

## Фінансовий аналіз

| Метод | Шлях | Тіло |
|-------|------|------|
| POST | `/api/v1/financial/analyze` | `MeasureInput` |
| POST | `/api/v1/financial/analyze/portfolio` | `PortfolioInput` |

Повертає NPV, IRR (як `{value, converged, iterations}`), BCR, simple/
discounted payback, LCCA, `yearly_details[]`.

## Екологічний ефект

| Метод | Шлях |
|-------|------|
| POST | `/api/v1/eco/analyze` |
| POST | `/api/v1/eco/analyze/portfolio` |

## Багатокритеріальний вибір

| Метод | Шлях | Опис |
|-------|------|------|
| POST | `/api/v1/multicriteria/ahp` | AHP з валідацією матриці Саати |
| POST | `/api/v1/multicriteria/topsis` | TOPSIS |
| POST | `/api/v1/multicriteria/combined` | AHP→TOPSIS у єдиному виклику |

## Сценарний аналіз

| Метод | Шлях |
|-------|------|
| POST | `/api/v1/scenario/whatif` |
| POST | `/api/v1/scenario/sensitivity` |
| POST | `/api/v1/scenario/breakeven` |

## Порівняння

| Метод | Шлях |
|-------|------|
| POST | `/api/v1/comparison/compare` |

Тіло — список заходів з полями `npv`, `irr`, `bcr`, `simple_payback`,
`co2_reduction`, опційно `ahp_score`, `topsis_score`. Відповідь — зведена
таблиця рангів, Pareto-фронт, детектор суперечностей.

## Звіти

| Метод | Шлях | Відповідь |
|-------|------|-----------|
| POST | `/api/v1/reports/generate` | `application/pdf` |
| POST | `/api/v1/reports/generate/excel` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |

Тіло — `ReportInput` з секціями Financial / Eco / Ranking + опційними
`ahp_data`, `topsis_data`, `sensitivity_data`.

## Коди помилок

| Код | HTTP | Опис |
|-----|------|------|
| `VALIDATION_ERROR` | 422 | Вхід не пройшов Pydantic-валідацію |
| `AUTHENTICATION_ERROR` | 401 | Немає / невалідний JWT |
| `AUTHORIZATION_ERROR` | 403 | Недостатньо прав |
| `NOT_FOUND` | 404 | Ресурс відсутній |
| `CONFLICT` | 409 | Порушення унікальності / стану |
| `UPSTREAM_ERROR` | 502 | Downstream сервіс недоступний (circuit breaker) |
| `INTERNAL_ERROR` | 500 | Невідома помилка |
