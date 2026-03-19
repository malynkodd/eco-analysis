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
- [Структура проєкту](#структура-проєкту)

---

## Архітектура

```
┌─────────────────────────────────────────────────────────┐
│                   Browser (React 19)                    │
│          http://localhost  (port 80 via Nginx)          │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Nginx API Gateway                     │
│   Rate limiting · Security headers · Reverse proxy      │
└──┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬─────┘
   │      │      │      │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
 auth  project  fin   eco   multi  scen  comp  report
 :8000  :8000  :8000 :8000  :8000 :8000 :8000  :8000
                         │
                ┌────────▼────────┐
                │  PostgreSQL 15  │
                │ (auth + project)│
                └─────────────────┘
```

---

## Мікросервіси

| Сервіс | Контейнер | Опис | Swagger |
|--------|-----------|------|---------|
| **auth-service** | `eco_auth` | JWT автентифікація, реєстрація, управління ролями | `/api/auth/docs` |
| **project-service** | `eco_project` | CRUD проєктів та заходів, workflow затвердження | `/api/projects/docs` |
| **financial-service** | `eco_financial` | NPV, IRR, BCR, Payback, LCCA | `/api/financial/docs` |
| **eco-impact-service** | `eco_impact` | Вуглецевий слід CO₂, відвернений збиток, 5 видів палива | `/api/eco/docs` |
| **multi-criteria-service** | `eco_multicriteria` | AHP (шкала Сааті, перевірка CR) + TOPSIS | `/api/multicriteria/docs` |
| **scenario-service** | `eco_scenario` | What-if аналіз, чутливість (tornado), Break-even | `/api/scenario/docs` |
| **comparison-service** | `eco_comparison` | Консенсусний рейтинг, Pareto-фронт, виявлення конфліктів | `/api/comparison/docs` |
| **report-service** | `eco_report` | PDF (6 графіків + кирилиця) + Excel (5 аркушів) | `/api/reports/docs` |

---

## Технологічний стек

| Шар | Технології |
|-----|-----------|
| **Frontend** | React 19, React Router 6, Recharts 3, Axios |
| **Backend** | FastAPI, Pydantic v2, SQLAlchemy 2, Python 3.11 |
| **База даних** | PostgreSQL 15 |
| **Автентифікація** | JWT (python-jose), bcrypt (passlib) |
| **Звіти** | ReportLab (PDF), openpyxl (Excel), matplotlib |
| **Алгоритми** | NumPy (AHP/TOPSIS), власна бісекція (IRR/Break-even) |
| **Інфраструктура** | Docker Compose, Nginx (rate limiting, security headers) |

---

## Швидкий старт

### Вимоги
- Docker 24+ та Docker Compose v2
- Мінімум 4 GB RAM

### 1. Клонуй репозиторій
```bash
git clone https://github.com/malynkodd/eco-analysis.git
cd eco-analysis
```

### 2. Налаштуй середовище
```bash
cp .env.example .env
```

Вміст `.env` (можна залишити як є для локальної розробки):
```env
POSTGRES_USER=ecouser
POSTGRES_PASSWORD=ecopassword
POSTGRES_DB=ecodb
SECRET_KEY=your-super-secret-key-change-in-production
DATABASE_URL=postgresql://ecouser:ecopassword@postgres:5432/ecodb
```

### 3. Запусти всі сервіси
```bash
docker compose up --build
```

Перший білд займає 3–5 хвилин. Для повного скиду бази даних:
```bash
docker compose down -v && docker compose up --build
```

### 4. Відкрий додаток

| URL | Опис |
|-----|------|
| **http://localhost** | Основний веб-інтерфейс |
| http://localhost/api/auth/docs | Swagger — Auth |
| http://localhost/api/projects/docs | Swagger — Projects |
| http://localhost/api/financial/docs | Swagger — Financial |
| http://localhost/api/eco/docs | Swagger — Eco Impact |
| http://localhost/api/multicriteria/docs | Swagger — Multi-Criteria |
| http://localhost/api/scenario/docs | Swagger — Scenario |
| http://localhost/api/comparison/docs | Swagger — Comparison |
| http://localhost/api/reports/docs | Swagger — Reports |

---

## Доступи за замовчуванням

| Логін | Пароль | Роль |
|-------|--------|------|
| `admin` | `admin123` | Admin — повний доступ + управління користувачами |

Акаунт адміна створюється автоматично при першому запуску.  
Нові користувачі реєструються з роллю **Analyst**.  
Адмін підвищує до **Manager** через панель `/admin`.

---

## Ролі користувачів

| Роль | Може | Не може |
|------|------|---------|
| **Analyst** | Створювати проєкти, додавати заходи, запускати аналіз, завантажувати PDF/Excel | Бачити чужі проєкти, затверджувати |
| **Manager** | Бачити ВСІ проєкти, затверджувати/відхиляти з коментарем, переглядати звіти | Створювати проєкти, запускати аналіз |
| **Admin** | Все що може Analyst і Manager + управління користувачами через `/admin` | Змінювати власну роль |

---

## Функціонал

### 💰 Фінансовий аналіз
- **NPV** — чиста приведена вартість з налаштовуваною ставкою дисконтування
- **IRR** — внутрішня норма дохідності (метод бісекції, діапазон 0–1000%)
- **BCR** — Benefit-Cost Ratio (PV вигод / PV витрат)
- **Простий Payback** — інвестиції ÷ річний чистий грошовий потік
- **Дисконтований Payback** — інтерпольований рік коли кумулятивний DCF ≥ 0
- **LCCA** — аналіз вартості життєвого циклу
- Таблиця грошових потоків по роках з графіком кумулятивного DCF

### 🎯 Багатокритеріальний аналіз
- **AHP** — метод аналізу ієрархій (шкала Сааті 1–9, метод власного вектору, перевірка CR < 0.1)
- **TOPSIS** — евклідова нормалізація, відстані до ідеалу/анти-ідеалу, коефіцієнт близькості
- Спільний workflow AHP+TOPSIS, виявлення розбіжностей, radar chart, експорт CSV

### 📈 Сценарне моделювання
- **What-if** — варіація інвестицій, заощаджень, витрат, ставки дисконтування, терміну ±20%
- **Sensitivity** — tornado chart впливу параметрів на NPV (налаштовуваний %)
- **Break-even** — мінімальна економія / максимальні інвестиції / максимальна ставка дисконтування / мінімальний термін при NPV = 0

### 🌿 Екологічний ефект
- Зменшення CO₂ для 5 видів палива:
  - Електроенергія: 0.37 кг CO₂/кВт·год
  - Природний газ: 2.04 кг CO₂/м³
  - Вугілля: 2.86 кг CO₂/кг
  - Дизель: 2.68 кг CO₂/л
  - Мазут: 3.15 кг CO₂/кг
- Відвернений економічний збиток (грн/тонна CO₂)
- Монетизація вуглецевого сліду

### 📊 Порівняння та рейтинг
- Консенсусний рейтинг по NPV, IRR, BCR, Payback, CO₂, AHP, TOPSIS
- Виявлення Pareto-оптимальних заходів (NPV vs CO₂)
- Виявлення суперечливих заходів (висока варіація рангів між методами)

### 📄 Звіти
- **PDF**: 6 вбудованих графіків (NPV bar, IRR+BCR, кумулятивний DCF line, CO₂ bar, radar, consensus ranking), повна підтримка кирилиці через шрифти DejaVu
- **Excel**: 5 аркушів — Summary, Financial Analysis, Environmental Impact, Sensitivity Analysis, AHP & TOPSIS — з вбудованим bar chart

### ✅ Workflow затвердження
- Аналітик створює проєкт → статус: **Pending**
- Менеджер переглядає та **затверджує** або **відхиляє** (з опційним коментарем)
- Відхилені проєкти показують коментар менеджера аналітику

---

## Структура проєкту

```
eco-analysis/
├── docker-compose.yml              # 10 сервісів + healthchecks
├── .env.example                    # Шаблон змінних середовища
├── nginx/
│   └── nginx.conf                  # Reverse proxy, rate limiting, security headers
├── services/
│   ├── auth-service/               # FastAPI · PostgreSQL · JWT · bcrypt
│   ├── project-service/            # FastAPI · PostgreSQL · RBAC · approval workflow
│   ├── financial-service/          # FastAPI · NPV · IRR · BCR · Payback · LCCA
│   ├── eco-impact-service/         # FastAPI · CO₂ · відвернений збиток
│   ├── multi-criteria-service/     # FastAPI · NumPy · AHP · TOPSIS
│   ├── scenario-service/           # FastAPI · What-if · Sensitivity · Break-even
│   ├── comparison-service/         # FastAPI · Консенсус · Pareto · Конфлікти
│   └── report-service/             # FastAPI · ReportLab · openpyxl · matplotlib
└── frontend/
    └── src/
        ├── api/index.js            # Всі API виклики (axios + auth interceptor)
        ├── context/AuthContext.jsx # JWT, isAnalyst/isManager/isAdmin прапори
        ├── pages/
        │   ├── LoginPage.jsx
        │   ├── RegisterPage.jsx    # Реєстрація тільки як Analyst
        │   ├── DashboardPage.jsx   # Список проєктів + workflow затвердження
        │   ├── ProjectPage.jsx     # CRUD заходів
        │   ├── AnalysisPage.jsx    # Вкладки: фінанси · еко · порівняння · графіки
        │   ├── ScenarioPage.jsx    # What-if · Sensitivity · Break-even
        │   ├── MultiCriteriaPage.jsx # AHP матриця + TOPSIS + radar
        │   └── AdminPage.jsx       # Управління користувачами, призначення ролей
        └── components/
            ├── Navbar.jsx          # Навігація з урахуванням ролі
            ├── TornadoMini.jsx     # Компонент tornado chart
            └── ErrorBoundary.jsx
```
