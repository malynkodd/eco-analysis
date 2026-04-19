# Алгоритмічна специфікація

Цей документ фіксує математичну базу кожного калькулятора. Посилання на
першоджерела — в коментарях у коді.

## 1. Фінансовий аналіз (financial-service)

### 1.1 NPV — Net Present Value

$$\mathrm{NPV} = -I_0 + \sum_{t=1}^{N} \frac{S - C}{(1+r)^t}$$

- `I_0` — капітальні витрати
- `S` — річна економія, `C` — операційні витрати
- `r` — ставка дисконтування, `N` — термін служби (роки)

### 1.2 IRR — Internal Rate of Return

Розв'язок $\mathrm{NPV}(r) = 0$ методом Брента на інтервалі `[-0.999, 10.0]`.
Brent — суперсет методу бісекції (гарантована збіжність + суперлінійна
швидкість на практиці). Реалізація: `scipy.optimize.brentq`. Якщо на кінцях
інтервалу NPV не змінює знак, повертається `{value: null, converged: false}`.

### 1.3 BCR — Benefit/Cost Ratio

$$\mathrm{BCR} = \frac{\sum_{t=1}^{N} \frac{S_t}{(1+r)^t}}{I_0 + \sum_{t=1}^{N} \frac{C_t}{(1+r)^t}}$$

### 1.4 Payback

- Simple: $T_s = \min \{ t : \sum_{i=1}^{t} (S_i - C_i) \ge I_0 \}$
- Discounted: те саме, але з коефіцієнтом $1/(1+r)^i$.

### 1.5 LCCA — Life-Cycle Cost Analysis

$$\mathrm{LCCA} = I_0 + \sum_{t=1}^{N} \frac{C_t}{(1+r)^t}$$

## 2. Екологічний ефект (eco-impact-service)

### 2.1 Скорочення CO₂

$$\Delta \mathrm{CO}_2 = Q \cdot k_{\mathrm{fuel}} \cdot 10^{-3}\ \mathrm{[т/рік]}$$

де `Q` — скорочення річного споживання, `k_fuel` — питомий коефіцієнт
емісії (IPCC, Мінприроди України):

| Паливо | k (кг CO₂ / одиницю) |
|--------|----------------------|
| Природний газ | 2.04 / м³ |
| Електроенергія | 0.37 / кВт·год |
| Вугілля | 2.86 / кг |
| Дизель | 2.68 / л |
| Мазут | 3.15 / кг |

### 2.2 Carbon Footprint

$$\mathrm{CF} = \Delta \mathrm{CO}_2 \cdot \mathrm{GWP}_{\mathrm{CO}_2}$$

де $\mathrm{GWP}_{\mathrm{CO}_2} = 1.0$.

### 2.3 Відвернений екологічний збиток

$$D = \Delta \mathrm{CO}_2 \cdot k_D\ \mathrm{[грн/рік]}$$

`k_D` — коефіцієнт збитку (грн/т CO₂), задається користувачем.

## 3. Багатокритеріальний вибір

### 3.1 AHP (multi-criteria-service/ahp.py)

Вхід: квадратна матриця парних порівнянь `M` розміру `n×n`, значення зі
шкали Саати $\{1/9, \ldots, 1, \ldots, 9\}$, діагональ = 1, $M_{ij} M_{ji} = 1$.

Алгоритм:

1. Обчислити власні пари `np.linalg.eig(M)`.
2. Обрати домінантну дійсну власну пару $(\lambda_{\max}, v)$.
3. Ваги: нормалізація `|v|` до $\sum w_i = 1$.
4. Consistency Index: $CI = (\lambda_{\max} - n)/(n-1)$.
5. Consistency Ratio: $CR = CI/RI(n)$ (таблиця RI із Saaty 1980).
6. Якщо $CR \ge 0.1$ — попередження про суперечливість.
7. Оцінки альтернатив: векторна нормалізація колонок → інверсія cost-колонок
   → зважена сума.

### 3.2 TOPSIS (multi-criteria-service/topsis.py)

Класичний Hwang–Yoon (1981):

1. Нормалізація: $r_{ij} = x_{ij} / \sqrt{\sum_k x_{kj}^2}$.
2. Зважене: $v_{ij} = w_j r_{ij}$.
3. Ідеал/анти-ідеал: $A^* = \max_i v_{ij}$ (для benefit), $\min_i$ (для cost);
   $A^-$ — навпаки.
4. Евклідові відстані: $d^*_i = \|v_i - A^*\|_2$, $d^-_i = \|v_i - A^-\|_2$.
5. Коефіцієнт близькості: $C_i = d^-_i / (d^*_i + d^-_i)$. Ранжування за
   спаданням $C_i$.

## 4. Сценарний аналіз (scenario-service)

### 4.1 What-if

Для кожної зміни параметра — перерахунок NPV на модифікованому `BaseScenario`
і звіт про абсолютну та відносну зміну.

### 4.2 Sensitivity (tornado)

Для кожного параметра $p \in \{I_0, C, S, r, N\}$ варіюється в діапазоні
$\pm k\%$ (за замовчуванням 20%, дозволено 10–50% за ТЗ). Будуються точки
$(\pm k\%, \mathrm{NPV})$, обчислюється:

- `impact_absolute` — амплітуда коливання NPV
- `impact_percent` — те саме у відсотках від $|\mathrm{NPV}_{\mathrm{base}}|$

Результати сортуються за спаданням — це дані для tornado-діаграми.

### 4.3 Break-even

Чисельний пошук порогових значень `expected_savings`,
`initial_investment`, `discount_rate`, `lifetime_years`, за яких
`NPV = 0`. Використовується Brent/бісекція на монотонному інтервалі;
повертається `None`, якщо перетин не існує у прийнятному діапазоні.

## 5. Консенсусне ранжування (comparison-service)

Кожному заходу присвоюються ранги за окремими метриками (NPV, IRR, BCR,
Payback, CO₂, опціонально AHP, TOPSIS). Консенсусний бал — середнє рангів;
фінальне місце — сортування за зростанням цього середнього.

Pareto-фронт: захід `x` є Pareto-оптимальним, якщо не існує `y` такого, що
$\mathrm{NPV}_y \ge \mathrm{NPV}_x$ і $\mathrm{CO}_{2,y} \ge \mathrm{CO}_{2,x}$ з
принаймні однією строгою нерівністю.

Суперечливі заходи — ті, у яких розкид між найгіршим і найкращим рангом
перевищує половину множини альтернатив (відсортоване жорстке
протистояння метрик).

## Посилання

- Saaty T.L. *The Analytic Hierarchy Process*. McGraw-Hill, 1980.
- Hwang C.L., Yoon K. *Multiple Attribute Decision Making: Methods and
  Applications*. Springer, 1981.
- IPCC Guidelines for National Greenhouse Gas Inventories, Vol. 2 (Energy).
- Brent R.P. *Algorithms for Minimization Without Derivatives*. Prentice-Hall,
  1973.
