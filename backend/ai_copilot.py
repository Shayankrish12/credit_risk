"""AI Analyst Copilot using Emergent LLM integration with rule-based fallback."""
import os
from typing import List
from emergentintegrations.llm.chat import LlmChat, UserMessage


EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


def build_borrower_context(borrower: dict, sales: list, bank: list, repayments: list,
                            signals: list, factors: list) -> str:
    sales_sorted = sorted(sales, key=lambda x: x.get("month", ""))[-12:]
    bank_sorted = sorted(bank, key=lambda x: x.get("month", ""))[-12:]
    sales_str = ", ".join([f"{s['month']}: INR {s['amount']:,.0f}" for s in sales_sorted])
    bank_str = ", ".join([f"{b['month']}: INR {b['balance']:,.0f}" for b in bank_sorted])

    bounced = sum(1 for r in repayments if r.get("status") == "bounced")
    delayed = sum(1 for r in repayments if r.get("status") == "delayed")
    paid = sum(1 for r in repayments if r.get("status") == "paid")

    sig_summary = "\n".join([
        f"- [{s.get('severity','').upper()}] {s.get('signal_type','').replace('_',' ').title()}: {s.get('explanation','')}"
        for s in signals
    ]) or "No active warning signals."

    factor_summary = "\n".join([
        f"- {f.get('factor','')} (+{f.get('impact',0)}): {f.get('detail','')}"
        for f in factors[:8]
    ]) or "No major factors."

    return f"""You are a credit risk analyst assistant. Use ONLY the borrower data below to answer.

BORROWER PROFILE:
- Business: {borrower.get('business_name','')}
- Sector: {borrower.get('sector','')}
- Location: {borrower.get('location','')}
- Loan Type: {borrower.get('loan_type','')}
- Loan Amount: INR {borrower.get('loan_amount',0):,.0f}
- Outstanding: INR {borrower.get('outstanding_amount',0):,.0f}
- Sanction Date: {borrower.get('sanction_date','')}
- Risk Score: {borrower.get('risk_score',0):.1f}/100 ({borrower.get('risk_category','').upper()})

MONTHLY SALES (last 12 months): {sales_str}

BANK BALANCES (last 12 months): {bank_str}

REPAYMENT HISTORY: {paid} paid, {delayed} delayed, {bounced} bounced (of {len(repayments)} total cycles)

WARNING SIGNALS:
{sig_summary}

TOP RISK FACTORS:
{factor_summary}

Provide concise, professional, data-grounded answers. Use specific numbers from the data. Format key points with bullets when appropriate. Be objective and avoid making up information not in the data above."""


async def ai_chat(borrower_ctx: str, session_id: str, user_message: str) -> str:
    """Call Claude Sonnet via emergentintegrations; fallback to rule-based response on failure."""
    if not EMERGENT_KEY:
        return rule_based_response(user_message, borrower_ctx)
    try:
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=session_id,
            system_message=borrower_ctx,
        ).with_model("anthropic", "claude-sonnet-4-6")
        response = await chat.send_message(UserMessage(text=user_message))
        return str(response)
    except Exception as e:
        return f"{rule_based_response(user_message, borrower_ctx)}\n\n_(Note: AI service temporarily unavailable, using rule-based response. Error: {str(e)[:120]})_"


def rule_based_response(message: str, context: str) -> str:
    """Fallback rule-based response engine."""
    msg = message.lower()
    if any(k in msg for k in ["why", "high risk", "risky", "concern"]):
        return ("Based on the borrower's data:\n"
                "- Review the WARNING SIGNALS section above for active red flags\n"
                "- The TOP RISK FACTORS show the largest contributors to the score\n"
                "- Key drivers usually are: declining sales, repayment irregularity, low bank balance vs EMI, and sector risk.\n\n"
                "Recommend deep-dive into the highest-severity signals first.")
    if any(k in msg for k in ["cash flow", "bank balance", "liquidity"]):
        return ("Cash flow summary: refer to the BANK BALANCES timeline. Compare the last 3 months average against the prior period — a >25% drop is a strong stress signal.\n"
                "Action: request live bank statements and a 90-day liquidity forecast from the borrower.")
    if any(k in msg for k in ["warning", "signal", "alert"]):
        return "See the WARNING SIGNALS list in the context. High-severity items are: cheque bounces, EMI delays >15%, sales decline >20%, and low bank balance vs EMI obligation. Each requires direct borrower contact."
    if any(k in msg for k in ["monitoring note", "credit note", "report"]):
        return ("Suggested credit monitoring note structure:\n"
                "1) Borrower overview\n2) Financial trend (sales, bank balance, repayment)\n"
                "3) Risk score with top drivers\n4) Warning signals\n5) Recommended action\n"
                "Use the 'Generate Report' button to export PDF/DOCX.")
    if any(k in msg for k in ["follow up", "questions", "ask borrower"]):
        return ("Suggested follow-up questions:\n"
                "- Reason for recent sales decline / volatility?\n"
                "- Top 3 customers and their payment cycles?\n"
                "- Any pending tax / GST disputes?\n"
                "- Are EMI delays one-off or systemic?\n"
                "- Status of any pledged collateral?\n"
                "- Plans to refinance or restructure?")
    if any(k in msg for k in ["sector", "industry"]):
        return ("Sector benchmark: compare borrower's sales volatility and cash retention to the sector norm. Higher-risk sectors (Construction, Restaurant, Textile) warrant tighter monitoring even at moderate scores.")
    return ("I can help analyze this borrower's data. Try asking:\n"
            "- Why is this borrower high risk?\n"
            "- Summarize last 6 months cash flow\n"
            "- What are the top warning signals?\n"
            "- Generate a credit monitoring note outline\n"
            "- Suggest follow-up questions for borrower")
