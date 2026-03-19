import logging
from typing import List
from schemas import FinancialInput, FinancialResult, YearlyDetail

logger = logging.getLogger(__name__)


def calculate_npv(cash_flows: List[float], discount_rate: float) -> float:
    """
    NPV = сума [ CF_t / (1 + r)^t ] для t від 0 до N
    cash_flows[0] = початкова інвестиція (від'ємна), дисконтується як t=0
    """
    npv = 0.0
    for t, cf in enumerate(cash_flows):
        npv += cf / ((1 + discount_rate) ** t)
    return round(npv, 2)


def calculate_irr(cash_flows: List[float]) -> float:
    """
    IRR — ставка при якій NPV = 0.
    Метод бісекції: шукаємо r між 0% і 1000%.
    Повертає IRR у відсотках або -1.0 якщо IRR не існує.
    """
    # Перевіряємо чи є зміна знаку (умова існування IRR)
    if all(cf >= 0 for cf in cash_flows) or all(cf <= 0 for cf in cash_flows):
        logger.debug("IRR does not exist: all cash flows have the same sign")
        return -1.0

    low, high = 0.0, 10.0  # від 0% до 1000%

    # Перевіряємо чи bracketed — NPV(low) та NPV(high) мають різні знаки
    npv_low = sum(cf / ((1 + low) ** t) for t, cf in enumerate(cash_flows))
    npv_high = sum(cf / ((1 + high) ** t) for t, cf in enumerate(cash_flows))

    if npv_low * npv_high > 0:
        # IRR поза діапазоном 0–1000% або не існує
        logger.debug("IRR not in range [0%%, 1000%%]: NPV(0)=%.2f, NPV(1000%%)=%.2f",
                     npv_low, npv_high)
        return -1.0

    for _ in range(1000):  # максимум 1000 ітерацій
        mid = (low + high) / 2
        npv_mid = sum(cf / ((1 + mid) ** t) for t, cf in enumerate(cash_flows))

        if abs(npv_mid) < 0.01:  # точність до 1 копійки
            return round(mid * 100, 2)  # повертаємо у відсотках

        # Оновлюємо межі бісекції на основі знаку npv_low
        if npv_low * npv_mid < 0:
            high = mid
        else:
            low = mid
            npv_low = npv_mid  # кешуємо npv_low щоб не рахувати знову

    return round(mid * 100, 2)


def calculate_bcr(expected_savings: float, operational_cost: float,
                  initial_investment: float, lifetime_years: int,
                  discount_rate: float) -> float:
    """
    BCR = PV(валові вигоди) / PV(повні витрати)
    Вигоди = дисконтовані річні заощадження (gross savings)
    Витрати = початкова інвестиція + PV(операційних витрат)
    """
    pv_savings = sum(
        expected_savings / ((1 + discount_rate) ** t)
        for t in range(1, lifetime_years + 1)
    )
    pv_opex = sum(
        operational_cost / ((1 + discount_rate) ** t)
        for t in range(1, lifetime_years + 1)
    )
    total_cost = initial_investment + pv_opex
    if total_cost == 0:
        return 0.0
    return round(pv_savings / total_cost, 3)


def calculate_simple_payback(annual_net_cash_flow: float,
                             initial_investment: float) -> float:
    """
    Простий Payback = Інвестиції / Річний чистий грошовий потік
    Повертає -1.0 якщо проект не окупається.
    """
    if annual_net_cash_flow <= 0:
        return -1.0  # не окупається
    return round(initial_investment / annual_net_cash_flow, 2)


def calculate_discounted_payback(cash_flows: List[float],
                                 discount_rate: float) -> float:
    """
    Дисконтований Payback — момент коли кумулятивний дисконтований CF стає >= 0.
    Повертає дробовий рік через лінійну інтерполяцію.
    Повертає -1.0 якщо не окупається за термін.
    """
    cumulative = 0.0
    prev_cumulative = 0.0

    for t, cf in enumerate(cash_flows):
        cumulative += cf / ((1 + discount_rate) ** t)
        if cumulative >= 0 and t > 0:
            # Лінійна інтерполяція: знаходимо точний дробовий рік окупності
            fraction = -prev_cumulative / (cumulative - prev_cumulative)
            return round(float(t - 1 + fraction), 2)
        prev_cumulative = cumulative

    return -1.0  # не окупається за термін


def calculate_lcca(initial_investment: float, operational_cost: float,
                   lifetime_years: int, discount_rate: float) -> float:
    """
    LCCA = Початкові інвестиції + PV(операційних витрат за весь термін)
    """
    pv_operational = sum(
        operational_cost / ((1 + discount_rate) ** t)
        for t in range(1, lifetime_years + 1)
    )
    return round(initial_investment + pv_operational, 2)


def build_yearly_details(annual_cf: float, initial_investment: float,
                         lifetime_years: int,
                         discount_rate: float) -> List[YearlyDetail]:
    """Будуємо деталізацію по кожному року"""
    details = []
    cumulative_cf = -initial_investment
    cumulative_disc = -initial_investment

    for year in range(1, lifetime_years + 1):
        discounted = annual_cf / ((1 + discount_rate) ** year)
        cumulative_cf += annual_cf
        cumulative_disc += discounted

        details.append(YearlyDetail(
            year=year,
            cash_flow=round(annual_cf, 2),
            discounted_cash_flow=round(discounted, 2),
            cumulative_cash_flow=round(cumulative_cf, 2),
            cumulative_discounted=round(cumulative_disc, 2)
        ))
    return details


def analyze_measure(data: FinancialInput) -> FinancialResult:
    """Головна функція — рахує всі показники для одного заходу"""

    # Річний чистий грошовий потік
    annual_net_cf = data.expected_savings - data.operational_cost

    # Масив грошових потоків: [0-й рік = -інвестиція, 1..N = річний CF]
    cash_flows = [-data.initial_investment] + [
        annual_net_cf for _ in range(data.lifetime_years)
    ]

    npv = calculate_npv(cash_flows, data.discount_rate)
    irr = calculate_irr(cash_flows)
    bcr = calculate_bcr(
        data.expected_savings,
        data.operational_cost,
        data.initial_investment,
        data.lifetime_years,
        data.discount_rate
    )
    simple_pb = calculate_simple_payback(annual_net_cf, data.initial_investment)
    disc_pb = calculate_discounted_payback(cash_flows, data.discount_rate)
    lcca = calculate_lcca(
        data.initial_investment,
        data.operational_cost,
        data.lifetime_years,
        data.discount_rate
    )
    yearly = build_yearly_details(
        annual_net_cf,
        data.initial_investment,
        data.lifetime_years,
        data.discount_rate
    )

    logger.info(
        "Financial analysis for '%s': NPV=%.2f, IRR=%.2f%%, BCR=%.3f, Payback=%.2f yr",
        data.name, npv, irr, bcr, simple_pb
    )

    return FinancialResult(
        name=data.name,
        npv=npv,
        irr=irr,
        bcr=bcr,
        simple_payback=simple_pb,
        discounted_payback=disc_pb,
        lcca=lcca,
        yearly_details=yearly
    )
