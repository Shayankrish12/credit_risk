"""Rule-based risk scoring engine for MSME borrowers."""
from typing import List, Dict, Tuple
from statistics import mean, stdev


SECTOR_RISK = {
    "Textile": 15, "Manufacturing": 10, "Trading": 12, "Retail": 14,
    "Services": 8, "Restaurant": 18, "Construction": 20, "Agriculture": 16,
    "Transport": 13, "IT Services": 6, "Healthcare": 7, "Education": 9,
}


def _pct_change(series: List[float]) -> List[float]:
    out = []
    for i in range(1, len(series)):
        prev = series[i - 1]
        if prev == 0:
            out.append(0)
        else:
            out.append((series[i] - prev) / abs(prev) * 100)
    return out


def compute_risk(
    borrower: dict,
    sales: List[dict],
    bank: List[dict],
    repayments: List[dict],
    news_sentiment: float = 0.0,  # -1..1, negative is bad
) -> Tuple[float, str, List[dict], List[dict]]:
    """Returns (score 0-100, category, contributing_factors, warning_signals)."""
    score = 0.0
    factors: List[dict] = []
    signals: List[dict] = []

    sales_sorted = sorted(sales, key=lambda x: x.get("month", ""))
    bank_sorted = sorted(bank, key=lambda x: x.get("month", ""))
    sales_amounts = [s["amount"] for s in sales_sorted]
    bank_amounts = [b["balance"] for b in bank_sorted]

    # 1. Declining monthly sales (last 3 vs prior 3)
    if len(sales_amounts) >= 6:
        recent = mean(sales_amounts[-3:])
        prior = mean(sales_amounts[-6:-3])
        if prior > 0:
            change = (recent - prior) / prior * 100
            if change < -20:
                pts = 15
                score += pts
                factors.append({"factor": "Sales decline", "impact": pts, "detail": f"Sales dropped {abs(change):.1f}% in last 3 months"})
                signals.append({"signal_type": "sales_decline", "severity": "high",
                                "explanation": f"Recent quarter sales dropped {abs(change):.1f}% compared to prior quarter",
                                "suggested_action": "Review business operations and demand pipeline with borrower"})
            elif change < -10:
                pts = 8
                score += pts
                factors.append({"factor": "Sales decline", "impact": pts, "detail": f"Moderate sales decline ({abs(change):.1f}%)"})
                signals.append({"signal_type": "sales_decline", "severity": "medium",
                                "explanation": f"Sales declined {abs(change):.1f}% over recent quarter",
                                "suggested_action": "Monitor monthly sales closely"})

    # 2. Revenue volatility
    if len(sales_amounts) >= 6:
        if mean(sales_amounts) > 0:
            cv = stdev(sales_amounts) / mean(sales_amounts) * 100
            if cv > 35:
                pts = 8
                score += pts
                factors.append({"factor": "Revenue volatility", "impact": pts, "detail": f"CV {cv:.1f}%"})
                signals.append({"signal_type": "revenue_volatility", "severity": "medium",
                                "explanation": f"High revenue volatility (coefficient of variation {cv:.1f}%)",
                                "suggested_action": "Request explanation of seasonal/order-based fluctuations"})

    # 3. Sudden revenue drop (any month-over-month > 30% drop)
    pct = _pct_change(sales_amounts)
    if any(p < -30 for p in pct):
        pts = 10
        score += pts
        factors.append({"factor": "Sudden revenue drop", "impact": pts, "detail": "Month-over-month drop > 30% detected"})

    # 4. Bounced payments & EMI delays
    bounced = sum(1 for r in repayments if r.get("status") == "bounced")
    delayed = sum(1 for r in repayments if r.get("status") == "delayed")
    total = max(len(repayments), 1)
    if bounced > 0:
        pts = min(20, bounced * 6)
        score += pts
        factors.append({"factor": "Bounced payments", "impact": pts, "detail": f"{bounced} bounce(s)"})
        signals.append({"signal_type": "cheque_bounce", "severity": "high" if bounced >= 2 else "medium",
                        "explanation": f"{bounced} bounced payment(s) detected in repayment history",
                        "suggested_action": "Contact borrower to understand cash flow strain"})
    delay_rate = delayed / total
    if delay_rate > 0.3:
        pts = 12
        score += pts
        factors.append({"factor": "EMI delays", "impact": pts, "detail": f"{delayed}/{total} delayed"})
        signals.append({"signal_type": "emi_delay", "severity": "high",
                        "explanation": f"{delayed} out of {total} EMIs delayed",
                        "suggested_action": "Schedule meeting to renegotiate repayment terms if needed"})
    elif delay_rate > 0.15:
        pts = 6
        score += pts
        factors.append({"factor": "EMI delays", "impact": pts, "detail": f"{delayed} delayed"})
        signals.append({"signal_type": "emi_delay", "severity": "medium",
                        "explanation": f"{delayed} EMI delays in recent months",
                        "suggested_action": "Monitor repayment cycle"})

    # 5. Falling cash balance
    if len(bank_amounts) >= 4:
        recent_cash = mean(bank_amounts[-3:])
        prior_cash = mean(bank_amounts[:-3]) if len(bank_amounts) > 3 else mean(bank_amounts)
        if prior_cash > 0:
            change = (recent_cash - prior_cash) / prior_cash * 100
            if change < -25:
                pts = 12
                score += pts
                factors.append({"factor": "Cash balance decline", "impact": pts, "detail": f"Cash down {abs(change):.1f}%"})
                signals.append({"signal_type": "cash_flow_stress", "severity": "high",
                                "explanation": f"Average bank balance dropped {abs(change):.1f}% recently",
                                "suggested_action": "Request liquidity plan from borrower"})

    # 6. Low bank balance vs EMI obligation
    avg_recent_bal = mean(bank_amounts[-3:]) if len(bank_amounts) >= 3 else (mean(bank_amounts) if bank_amounts else 0)
    outstanding = borrower.get("outstanding_amount", 0)
    monthly_emi_est = outstanding * 0.025  # rough estimate
    if bank_amounts and monthly_emi_est > 0 and avg_recent_bal < monthly_emi_est * 1.5:
        pts = 10
        score += pts
        factors.append({"factor": "Low bank balance", "impact": pts, "detail": "Insufficient cushion vs EMI"})
        signals.append({"signal_type": "low_bank_balance", "severity": "high",
                        "explanation": "Average bank balance is less than 1.5x estimated monthly EMI",
                        "suggested_action": "Verify additional collateral or co-borrower"})

    # 7. Negative cash flow months
    neg_months = sum(1 for b in bank_amounts if b < 0)
    if neg_months > 0:
        pts = min(8, neg_months * 3)
        score += pts
        factors.append({"factor": "Negative cash months", "impact": pts, "detail": f"{neg_months} month(s)"})

    # 8. Sector risk
    sector_pts = SECTOR_RISK.get(borrower.get("sector", ""), 10)
    score += sector_pts
    factors.append({"factor": "Sector risk", "impact": sector_pts, "detail": f"{borrower.get('sector','Unknown')} sector"})

    # 9. High leverage (outstanding/loan ratio still high)
    loan_amt = borrower.get("loan_amount", 0)
    if loan_amt > 0:
        utilization = outstanding / loan_amt
        if utilization > 0.85:
            pts = 8
            score += pts
            factors.append({"factor": "High leverage", "impact": pts, "detail": f"{utilization*100:.1f}% utilized"})
            signals.append({"signal_type": "high_leverage", "severity": "medium",
                            "explanation": f"Loan utilization at {utilization*100:.1f}%",
                            "suggested_action": "Assess additional credit capacity carefully"})

    # 10. Negative news sentiment
    if news_sentiment < -0.3:
        pts = 8
        score += pts
        factors.append({"factor": "Negative news", "impact": pts, "detail": f"Sentiment {news_sentiment:.2f}"})
        signals.append({"signal_type": "negative_news", "severity": "medium",
                        "explanation": "Adverse news sentiment detected for borrower/sector",
                        "suggested_action": "Conduct due-diligence call"})

    # 11. GST/sales mismatch (placeholder - >25% diff between sales and reported GST if any)
    # Computed separately if GST data uploaded; placeholder factor.

    # Clamp
    score = min(100.0, round(score, 1))

    if score < 25:
        category = "low"
    elif score < 50:
        category = "moderate"
    elif score < 75:
        category = "high"
    else:
        category = "critical"

    factors.sort(key=lambda x: x["impact"], reverse=True)
    return score, category, factors, signals


def alerts_from_signals(borrower: dict, score: float, signals: List[dict]) -> List[dict]:
    """Generate alerts based on rules."""
    alerts = []
    if score >= 75:
        alerts.append({"alert_type": "risk_threshold", "severity": "critical",
                       "message": f"Risk score reached {score:.0f} (Critical)"})
    elif score >= 50:
        alerts.append({"alert_type": "risk_threshold", "severity": "high",
                       "message": f"Risk score elevated to {score:.0f} (High)"})

    for s in signals:
        if s["severity"] in ("high", "critical"):
            alerts.append({"alert_type": s["signal_type"], "severity": s["severity"],
                           "message": s["explanation"]})
    return alerts
