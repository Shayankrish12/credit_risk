"""Sample data generator for seeding the MSME Credit Risk system."""
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict


SECTORS = ["Textile", "Manufacturing", "Trading", "Retail", "Services",
           "Restaurant", "Construction", "Agriculture", "Transport", "IT Services"]

LOCATIONS = ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Pune", "Hyderabad",
             "Ahmedabad", "Kolkata", "Jaipur", "Surat"]

LOAN_TYPES = ["Working Capital", "Term Loan", "Cash Credit", "MSME Loan", "Equipment Finance"]

BUSINESSES = [
    ("Sharma Textiles Pvt Ltd", "Textile"),
    ("Verma Auto Components", "Manufacturing"),
    ("Patel Trading Co", "Trading"),
    ("Krishna Retail Mart", "Retail"),
    ("Mehta Consulting Services", "Services"),
    ("Singh Restaurants Ltd", "Restaurant"),
    ("Reddy Construction Co", "Construction"),
    ("Iyer Agro Industries", "Agriculture"),
    ("Khan Logistics", "Transport"),
    ("Nair Software Solutions", "IT Services"),
    ("Gupta Fabrics", "Textile"),
    ("Bose Engineering Works", "Manufacturing"),
]

FIRST_NAMES = ["Rajesh", "Priya", "Amit", "Sneha", "Vikram", "Anjali", "Suresh", "Kavita", "Rohit", "Meera"]
LAST_NAMES = ["Sharma", "Verma", "Patel", "Krishna", "Mehta", "Singh", "Reddy", "Iyer", "Khan", "Nair"]


def _months_back(n: int) -> List[str]:
    today = datetime.now(timezone.utc).replace(day=1)
    months = []
    for i in range(n - 1, -1, -1):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        months.append(f"{y:04d}-{m:02d}")
    return months


def generate_borrower_data(seed: int, business: tuple) -> Dict:
    random.seed(seed)
    name, sector = business
    loan_amount = random.choice([500000, 1000000, 1500000, 2500000, 5000000, 7500000, 10000000])
    outstanding = round(loan_amount * random.uniform(0.45, 0.95), 2)
    sanction_days = random.randint(180, 1800)
    sanction_date = (datetime.now(timezone.utc) - timedelta(days=sanction_days)).date().isoformat()

    risk_profile = random.choice(["healthy", "healthy", "stressed", "distressed"])

    months = _months_back(12)
    base_sales = random.randint(800000, 3500000)
    sales = []
    bank = []
    for i, m in enumerate(months):
        if risk_profile == "healthy":
            sale = base_sales * random.uniform(0.92, 1.08)
            bal = base_sales * random.uniform(0.25, 0.45)
        elif risk_profile == "stressed":
            decay = 1 - (i / 22) if i >= 6 else 1
            sale = base_sales * decay * random.uniform(0.85, 1.05)
            bal = base_sales * decay * random.uniform(0.15, 0.30)
        else:  # distressed
            decay = 1 - (i / 14) if i >= 4 else 1
            sale = base_sales * decay * random.uniform(0.6, 0.95)
            bal = base_sales * decay * random.uniform(0.05, 0.20)
        sales.append({"month": m, "amount": round(max(sale, 50000), 2)})
        bank.append({"month": m, "balance": round(max(bal, 10000), 2), "avg_balance": round(max(bal, 10000), 2)})

    # Repayments - 12 months
    repayments = []
    monthly_emi = round(outstanding * 0.025, 2)
    for i, m in enumerate(months):
        due = f"{m}-05"
        if risk_profile == "healthy":
            status = "paid" if random.random() > 0.05 else "delayed"
        elif risk_profile == "stressed":
            r = random.random()
            status = "paid" if r > 0.4 else ("delayed" if r > 0.15 else "bounced")
        else:
            r = random.random()
            status = "paid" if r > 0.6 else ("delayed" if r > 0.25 else "bounced")
        days_delayed = 0 if status == "paid" else (random.randint(3, 20) if status == "delayed" else random.randint(15, 45))
        paid_date = None
        if status == "paid":
            paid_date = f"{m}-{random.randint(2,5):02d}"
        elif status == "delayed":
            paid_date = f"{m}-{min(28, 5 + days_delayed):02d}"
        repayments.append({
            "due_date": due,
            "paid_date": paid_date,
            "amount": monthly_emi,
            "status": status,
            "days_delayed": days_delayed,
        })

    contact_person = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    gst = f"{random.randint(10,37):02d}AAACS{random.randint(1000,9999)}{random.choice('ABCDEFGH')}1Z{random.randint(1,9)}"

    return {
        "business_name": name,
        "sector": sector,
        "location": random.choice(LOCATIONS),
        "loan_amount": loan_amount,
        "loan_type": random.choice(LOAN_TYPES),
        "sanction_date": sanction_date,
        "outstanding_amount": outstanding,
        "gst_number": gst,
        "contact_person": contact_person,
        "contact_phone": f"+91-{random.randint(7000000000, 9999999999)}",
        "sales": sales,
        "bank": bank,
        "repayments": repayments,
        "news_sentiment": -0.4 if risk_profile == "distressed" else (-0.15 if risk_profile == "stressed" else 0.1),
    }


def generate_bs_pnl(seed: int, business: tuple, loan_amount: float, outstanding: float, sales_data: List[Dict]) -> tuple:
    """Generate 4 quarters of Balance Sheet and P&L data for a borrower.
    Profile derived from existing sales decay pattern."""
    random.seed(seed + 1000)
    name, sector = business

    # Use existing sales to anchor numbers
    if sales_data:
        recent_sales = [s["amount"] for s in sales_data[-3:]]
        prior_sales = [s["amount"] for s in sales_data[:3]] if len(sales_data) >= 3 else recent_sales
        quarterly_revenue = sum(recent_sales)
        prior_revenue = sum(prior_sales)
    else:
        quarterly_revenue = random.uniform(2000000, 8000000)
        prior_revenue = quarterly_revenue

    # Detect health from sales trend
    health = "healthy"
    if quarterly_revenue < prior_revenue * 0.7:
        health = "distressed"
    elif quarterly_revenue < prior_revenue * 0.9:
        health = "stressed"

    # Margins by health
    margin_profile = {
        "healthy": {"gm": 0.32, "om": 0.18, "nm": 0.10},
        "stressed": {"gm": 0.22, "om": 0.08, "nm": 0.02},
        "distressed": {"gm": 0.15, "om": -0.03, "nm": -0.08},
    }[health]

    # Generate 4 quarters
    today = datetime.now(timezone.utc).replace(day=1)
    quarters = []
    for q in range(4, 0, -1):
        y = today.year
        m = today.month - (q - 1) * 3
        while m <= 0:
            m += 12
            y -= 1
        quarter_num = (m - 1) // 3 + 1
        quarters.append(f"{y:04d}-Q{quarter_num}")

    bs_list = []
    pnl_list = []
    for i, period in enumerate(quarters):
        # Trend factor: older quarters were healthier (for stressed/distressed)
        if health == "distressed":
            trend = 1.0 + (3 - i) * 0.15  # older quarters had more revenue
        elif health == "stressed":
            trend = 1.0 + (3 - i) * 0.07
        else:
            trend = 1.0 + (3 - i) * (-0.02)  # healthy: slight growth recently

        rev = quarterly_revenue * trend * random.uniform(0.95, 1.05)
        gm_pct = margin_profile["gm"] * random.uniform(0.9, 1.1)
        om_pct = margin_profile["om"] * random.uniform(0.85, 1.15)
        nm_pct = margin_profile["nm"] * random.uniform(0.85, 1.15)

        cogs = rev * (1 - gm_pct)
        gross_profit = rev - cogs
        opex = gross_profit - rev * om_pct - rev * 0.04  # 4% depreciation baseline
        ebitda = gross_profit - opex
        depreciation = rev * 0.04
        ebit = ebitda - depreciation
        interest = outstanding * 0.025  # quarterly interest
        pbt = ebit - interest
        tax = max(0, pbt * 0.25)
        net_profit = pbt - tax
        # If net_profit % doesn't match target, adjust opex
        target_np = rev * nm_pct
        if abs(net_profit - target_np) > rev * 0.05:
            diff = (net_profit - target_np)
            opex += diff
            ebitda = gross_profit - opex
            ebit = ebitda - depreciation
            pbt = ebit - interest
            tax = max(0, pbt * 0.25)
            net_profit = pbt - tax

        pnl_list.append({
            "period": period,
            "revenue": round(rev, 2),
            "cogs": round(cogs, 2),
            "gross_profit": round(gross_profit, 2),
            "operating_expenses": round(opex, 2),
            "ebitda": round(ebitda, 2),
            "depreciation": round(depreciation, 2),
            "ebit": round(ebit, 2),
            "interest_expense": round(interest, 2),
            "pbt": round(pbt, 2),
            "tax": round(tax, 2),
            "net_profit": round(net_profit, 2),
        })

        # Balance sheet — anchored to revenue scale
        cash = rev * (0.08 if health == "healthy" else 0.04 if health == "stressed" else 0.015) * random.uniform(0.8, 1.2)
        receivables = rev * 0.25 * random.uniform(0.85, 1.15)
        inventory = cogs * 0.20 * random.uniform(0.85, 1.15)
        other_ca = rev * 0.03
        current_assets = cash + receivables + inventory + other_ca
        fixed_assets = loan_amount * 0.7 * random.uniform(0.85, 1.0)
        other_assets = rev * 0.04
        payables = cogs * 0.15
        short_term_debt = outstanding * 0.3
        long_term_debt = outstanding * 0.7 * trend  # older = more debt
        other_liab = rev * 0.02
        current_liabilities = payables + short_term_debt + other_liab * 0.5
        total_assets = current_assets + fixed_assets + other_assets
        total_liab_ex_equity = current_liabilities + long_term_debt + other_liab * 0.5
        equity = max(total_assets - total_liab_ex_equity, rev * 0.1)

        bs_list.append({
            "period": period,
            "current_assets": round(current_assets, 2),
            "inventory": round(inventory, 2),
            "cash": round(cash, 2),
            "receivables": round(receivables, 2),
            "fixed_assets": round(fixed_assets, 2),
            "other_assets": round(other_assets, 2),
            "current_liabilities": round(current_liabilities, 2),
            "short_term_debt": round(short_term_debt, 2),
            "long_term_debt": round(long_term_debt, 2),
            "other_liabilities": round(other_liab, 2),
            "equity": round(equity, 2),
        })

    return bs_list, pnl_list


def generate_all_borrowers() -> List[Dict]:
    return [generate_borrower_data(i, BUSINESSES[i]) for i in range(len(BUSINESSES))]
