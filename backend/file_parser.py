"""File parsing helpers for CSV/XLSX/PDF uploads."""
import io
import re
from typing import List, Dict
import pandas as pd
from pypdf import PdfReader


def parse_csv_xlsx(content: bytes, filename: str) -> pd.DataFrame:
    name = filename.lower()
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(content))
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(content))
    raise ValueError("Unsupported file format")


def parse_pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    text = ""
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"
    return text


def _find_col(df: pd.DataFrame, candidates: List[str]):
    for col in df.columns:
        if any(c.lower() in str(col).lower() for c in candidates):
            return col
    return None


def parse_sales_data(df: pd.DataFrame) -> List[Dict]:
    month_col = _find_col(df, ["month", "date", "period"])
    amt_col = _find_col(df, ["amount", "sales", "revenue", "value"])
    if not month_col or not amt_col:
        return []
    out = []
    for _, row in df.iterrows():
        try:
            m = str(row[month_col])
            if len(m) >= 7:
                m = m[:7]
            amt = float(row[amt_col])
            out.append({"month": m, "amount": amt})
        except Exception:
            continue
    return out


def parse_bank_data(df: pd.DataFrame) -> List[Dict]:
    month_col = _find_col(df, ["month", "date", "period"])
    bal_col = _find_col(df, ["balance", "closing", "amount"])
    if not month_col or not bal_col:
        return []
    out = []
    for _, row in df.iterrows():
        try:
            m = str(row[month_col])
            if len(m) >= 7:
                m = m[:7]
            bal = float(row[bal_col])
            out.append({"month": m, "balance": bal, "avg_balance": bal})
        except Exception:
            continue
    return out


def parse_repayment_data(df: pd.DataFrame) -> List[Dict]:
    due_col = _find_col(df, ["due", "date"])
    amt_col = _find_col(df, ["amount", "emi", "value"])
    status_col = _find_col(df, ["status"])
    if not due_col or not amt_col:
        return []
    out = []
    for _, row in df.iterrows():
        try:
            due = str(row[due_col])[:10]
            amt = float(row[amt_col])
            status = str(row[status_col]).lower() if status_col else "paid"
            if status not in ("paid", "delayed", "bounced", "pending"):
                status = "paid"
            out.append({"due_date": due, "paid_date": None, "amount": amt, "status": status, "days_delayed": 0})
        except Exception:
            continue
    return out


BS_FIELDS = ["current_assets", "inventory", "cash", "receivables", "fixed_assets",
             "other_assets", "current_liabilities", "short_term_debt", "long_term_debt",
             "other_liabilities", "equity"]

PNL_FIELDS = ["revenue", "cogs", "gross_profit", "operating_expenses", "ebitda",
              "depreciation", "ebit", "interest_expense", "pbt", "tax", "net_profit"]


def parse_balance_sheet(df: pd.DataFrame) -> List[Dict]:
    period_col = _find_col(df, ["period", "quarter", "month", "date"])
    if not period_col:
        return []
    out = []
    cols_map = {f: _find_col(df, [f, f.replace("_", " ")]) for f in BS_FIELDS}
    for _, row in df.iterrows():
        try:
            entry = {"period": str(row[period_col]).strip()[:10]}
            for f, col in cols_map.items():
                if col:
                    try:
                        entry[f] = float(row[col])
                    except Exception:
                        entry[f] = 0
                else:
                    entry[f] = 0
            out.append(entry)
        except Exception:
            continue
    return out


def parse_pnl(df: pd.DataFrame) -> List[Dict]:
    period_col = _find_col(df, ["period", "quarter", "month", "date"])
    if not period_col:
        return []
    out = []
    cols_map = {f: _find_col(df, [f, f.replace("_", " ")]) for f in PNL_FIELDS}
    for _, row in df.iterrows():
        try:
            entry = {"period": str(row[period_col]).strip()[:10]}
            for f, col in cols_map.items():
                if col:
                    try:
                        entry[f] = float(row[col])
                    except Exception:
                        entry[f] = 0
                else:
                    entry[f] = 0
            # Compute derived fields if missing
            if not entry.get("gross_profit"):
                entry["gross_profit"] = entry.get("revenue", 0) - entry.get("cogs", 0)
            if not entry.get("ebitda"):
                entry["ebitda"] = entry["gross_profit"] - entry.get("operating_expenses", 0)
            if not entry.get("ebit"):
                entry["ebit"] = entry["ebitda"] - entry.get("depreciation", 0)
            if not entry.get("pbt"):
                entry["pbt"] = entry["ebit"] - entry.get("interest_expense", 0)
            if not entry.get("net_profit"):
                entry["net_profit"] = entry["pbt"] - entry.get("tax", 0)
            out.append(entry)
        except Exception:
            continue
    return out


# CSV template strings for downloadable templates
TEMPLATES = {
    "sales": "month,amount\n2024-01,1200000\n2024-02,1150000\n2024-03,1300000\n",
    "bank": "month,balance\n2024-01,450000\n2024-02,320000\n2024-03,280000\n",
    "repayment": "due_date,amount,status\n2024-01-05,25000,paid\n2024-02-05,25000,delayed\n2024-03-05,25000,bounced\n",
    "balance_sheet": "period,current_assets,inventory,cash,receivables,fixed_assets,other_assets,current_liabilities,short_term_debt,long_term_debt,other_liabilities,equity\n2024-Q1,3500000,800000,400000,1200000,5500000,300000,2200000,800000,3500000,200000,3000000\n2024-Q2,3700000,850000,420000,1250000,5400000,300000,2300000,850000,3400000,200000,3200000\n",
    "pnl": "period,revenue,cogs,gross_profit,operating_expenses,ebitda,depreciation,ebit,interest_expense,pbt,tax,net_profit\n2024-Q1,4500000,2800000,1700000,900000,800000,150000,650000,180000,470000,120000,350000\n2024-Q2,4800000,3000000,1800000,950000,850000,150000,700000,180000,520000,130000,390000\n",
    "borrowers_bulk": "business_name,sector,location,loan_amount,loan_type,sanction_date,outstanding_amount,gst_number,contact_person,contact_phone\nABC Manufacturing,Manufacturing,Mumbai,5000000,Working Capital,2024-06-15,3500000,27AAACS1234A1Z5,Rajesh Kumar,+91-9876543210\nXYZ Trading,Trading,Delhi,2500000,Cash Credit,2024-03-10,1800000,07AAACS5678B2Z9,Priya Sharma,+91-9988776655\n",
}


def analyze_news_sentiment(text: str) -> float:
    """Very simple keyword-based sentiment for news text. -1..1"""
    text_l = text.lower()
    negative = ["loss", "default", "fraud", "investigation", "lawsuit", "shut", "closed",
                "decline", "drop", "crisis", "bankruptcy", "raid", "irregular", "scam",
                "complaint", "penalty", "fine", "downgrade"]
    positive = ["profit", "growth", "expand", "award", "milestone", "record", "strong",
                "increase", "partnership", "investment", "upgrade", "success"]
    n = sum(1 for w in negative if w in text_l)
    p = sum(1 for w in positive if w in text_l)
    if n + p == 0:
        return 0.0
    return round((p - n) / (n + p), 2)
