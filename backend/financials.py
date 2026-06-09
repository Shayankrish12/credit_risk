"""Financial ratio computation and balance sheet / P&L analysis."""
from typing import Dict, List, Optional


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    if b is None or b == 0:
        return default
    return a / b


def compute_ratios(balance_sheet: dict, pnl: dict) -> Dict[str, dict]:
    """Compute 10 standard financial ratios from a balance sheet and P&L pair.
    Each ratio returns: {value, healthy (bool), status (good/warning/bad), benchmark, description}.
    """
    bs = balance_sheet or {}
    pl = pnl or {}

    current_assets = float(bs.get("current_assets", 0))
    inventory = float(bs.get("inventory", 0))
    current_liabilities = float(bs.get("current_liabilities", 0))
    total_debt = float(bs.get("short_term_debt", 0)) + float(bs.get("long_term_debt", 0))
    equity = float(bs.get("equity", 0))
    working_capital = current_assets - current_liabilities

    revenue = float(pl.get("revenue", 0))
    gross_profit = float(pl.get("gross_profit", revenue - float(pl.get("cogs", 0))))
    ebitda = float(pl.get("ebitda", 0))
    ebit = float(pl.get("ebit", 0))
    interest = float(pl.get("interest_expense", 0))
    net_profit = float(pl.get("net_profit", 0))
    # principal estimate: assume 8% annual amortization of total debt for DSCR
    principal_payment = total_debt * 0.08

    ratios = {}

    # Liquidity
    cr = safe_div(current_assets, current_liabilities)
    ratios["current_ratio"] = _grade(cr, [(1.5, "good"), (1.0, "warning")], "bad",
        label="Current Ratio", benchmark="≥ 1.5", description="Ability to cover short-term liabilities")

    qr = safe_div(current_assets - inventory, current_liabilities)
    ratios["quick_ratio"] = _grade(qr, [(1.0, "good"), (0.7, "warning")], "bad",
        label="Quick Ratio", benchmark="≥ 1.0", description="Liquid assets vs short-term debts")

    # Leverage
    de = safe_div(total_debt, equity)
    ratios["debt_to_equity"] = _grade_low(de, [(2.0, "good"), (3.0, "warning")], "bad",
        label="Debt to Equity", benchmark="≤ 2.0", description="Leverage relative to owner capital")

    ic = safe_div(ebit, interest)
    ratios["interest_coverage"] = _grade(ic, [(3.0, "good"), (1.5, "warning")], "bad",
        label="Interest Coverage", benchmark="≥ 3.0", description="Operating income vs interest cost")

    dscr = safe_div(ebitda, interest + principal_payment)
    ratios["dscr"] = _grade(dscr, [(1.25, "good"), (1.0, "warning")], "bad",
        label="DSCR", benchmark="≥ 1.25", description="Debt service coverage ratio")

    # Profitability
    gm = safe_div(gross_profit, revenue) * 100
    ratios["gross_margin"] = _grade(gm, [(25.0, "good"), (12.0, "warning")], "bad",
        label="Gross Margin", benchmark="≥ 25%", description="Revenue retained after COGS", suffix="%")

    nm = safe_div(net_profit, revenue) * 100
    ratios["net_margin"] = _grade(nm, [(8.0, "good"), (3.0, "warning")], "bad",
        label="Net Margin", benchmark="≥ 8%", description="Bottom-line profitability", suffix="%")

    em = safe_div(ebitda, revenue) * 100
    ratios["ebitda_margin"] = _grade(em, [(15.0, "good"), (8.0, "warning")], "bad",
        label="EBITDA Margin", benchmark="≥ 15%", description="Operating profitability", suffix="%")

    roe = safe_div(net_profit, equity) * 100
    ratios["roe"] = _grade(roe, [(12.0, "good"), (6.0, "warning")], "bad",
        label="Return on Equity", benchmark="≥ 12%", description="Return per rupee of equity", suffix="%")

    # Efficiency
    wct = safe_div(revenue, max(working_capital, 1))
    ratios["working_capital_turnover"] = _grade(wct, [(4.0, "good"), (2.0, "warning")], "bad",
        label="WC Turnover", benchmark="≥ 4×", description="Sales per ₹1 of working capital", suffix="×")

    return ratios


def _grade(value: float, thresholds: list, fallback: str, label: str, benchmark: str, description: str, suffix: str = "") -> dict:
    """thresholds = [(min_value, status), ...] sorted descending. Higher is better."""
    status = fallback
    for thr, st in thresholds:
        if value >= thr:
            status = st
            break
    return {"label": label, "value": round(value, 2), "status": status, "benchmark": benchmark, "description": description, "suffix": suffix}


def _grade_low(value: float, thresholds: list, fallback: str, label: str, benchmark: str, description: str, suffix: str = "") -> dict:
    """For ratios where LOWER is better (e.g., D/E)."""
    status = fallback
    for thr, st in thresholds:
        if value <= thr:
            status = st
            break
    return {"label": label, "value": round(value, 2), "status": status, "benchmark": benchmark, "description": description, "suffix": suffix}


def ratio_risk_factors(ratios: dict) -> tuple:
    """Convert ratio analysis into risk engine factors and warning signals.
    Returns (factors_list, signals_list, total_points)."""
    factors = []
    signals = []
    total = 0

    if "dscr" in ratios:
        v = ratios["dscr"]["value"]
        if v < 1.0:
            pts = 12
            total += pts
            factors.append({"factor": "DSCR critical", "impact": pts, "detail": f"DSCR {v} (< 1.0 — cannot service debt)"})
            signals.append({"signal_type": "low_dscr", "severity": "critical",
                "explanation": f"Debt Service Coverage Ratio at {v}, below 1.0 — operating cash insufficient to cover debt service",
                "suggested_action": "Restructure repayment terms immediately; consider extending tenure"})
        elif v < 1.25:
            pts = 8
            total += pts
            factors.append({"factor": "Weak DSCR", "impact": pts, "detail": f"DSCR {v} (< 1.25)"})
            signals.append({"signal_type": "low_dscr", "severity": "high",
                "explanation": f"DSCR {v} below safe threshold of 1.25",
                "suggested_action": "Request cash flow forecast for next 6 months"})

    if "interest_coverage" in ratios:
        v = ratios["interest_coverage"]["value"]
        if v < 1.5:
            pts = 10
            total += pts
            factors.append({"factor": "Low interest coverage", "impact": pts, "detail": f"EBIT/Interest = {v}"})
            signals.append({"signal_type": "low_interest_coverage", "severity": "high",
                "explanation": f"Interest coverage at {v}× — barely covering interest from operations",
                "suggested_action": "Verify ability to absorb any rate increase"})

    if "current_ratio" in ratios:
        v = ratios["current_ratio"]["value"]
        if v < 1.0:
            pts = 8
            total += pts
            factors.append({"factor": "Liquidity crunch", "impact": pts, "detail": f"Current ratio {v} (< 1.0)"})
            signals.append({"signal_type": "liquidity_crunch", "severity": "high",
                "explanation": f"Current ratio at {v} — short-term liabilities exceed current assets",
                "suggested_action": "Assess immediate working capital needs"})

    if "debt_to_equity" in ratios:
        v = ratios["debt_to_equity"]["value"]
        if v > 3.0:
            pts = 10
            total += pts
            factors.append({"factor": "Over-leveraged", "impact": pts, "detail": f"D/E ratio {v} (> 3.0)"})
            signals.append({"signal_type": "over_leverage", "severity": "high",
                "explanation": f"Debt-to-Equity at {v} — heavily reliant on borrowed funds",
                "suggested_action": "Discuss equity infusion or debt reduction plan"})
        elif v > 2.0:
            pts = 5
            total += pts
            factors.append({"factor": "Elevated leverage", "impact": pts, "detail": f"D/E ratio {v}"})

    if "net_margin" in ratios:
        v = ratios["net_margin"]["value"]
        if v < 0:
            pts = 8
            total += pts
            factors.append({"factor": "Operating losses", "impact": pts, "detail": f"Net margin {v}%"})
            signals.append({"signal_type": "operating_loss", "severity": "high",
                "explanation": f"Net margin negative at {v}% — business is loss-making",
                "suggested_action": "Review cost structure and pricing strategy with borrower"})

    return factors, signals, total
