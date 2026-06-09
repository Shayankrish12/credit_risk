"""AI Copilot specialized for Recovery Workflow."""
import os
from typing import List
from emergentintegrations.llm.chat import LlmChat, UserMessage


EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


def build_recovery_context(case: dict, borrower: dict, financials: dict, timeline: list, ratios: dict) -> str:
    """Build context for recovery strategy AI. Focus on actionable recovery steps."""

    timeline_summary = "\n".join([
        f"- [{e.get('at','')[:10]}] {e.get('type','').replace('_',' ').upper()}: {e.get('content','')}"
        for e in timeline[:15]
    ]) or "No timeline events yet."

    ratio_summary = ""
    if ratios:
        ratio_summary = "\n".join([
            f"- {r['label']}: {r['value']}{r.get('suffix','')} ({r['status'].upper()}, benchmark {r['benchmark']})"
            for r in ratios.values()
        ])

    sales = financials.get("sales", [])
    bank = financials.get("bank", [])
    reps = financials.get("repayments", [])
    pnl = financials.get("pnl", [])

    recent_pnl = ""
    if pnl:
        latest = sorted(pnl, key=lambda x: x.get("period", ""))[-1]
        recent_pnl = (f"Latest P&L ({latest.get('period','')}): "
                      f"Revenue ₹{latest.get('revenue',0):,.0f}, "
                      f"EBITDA ₹{latest.get('ebitda',0):,.0f}, "
                      f"Net Profit ₹{latest.get('net_profit',0):,.0f}, "
                      f"Interest ₹{latest.get('interest_expense',0):,.0f}")

    bounced = sum(1 for r in reps if r.get("status") == "bounced")
    delayed = sum(1 for r in reps if r.get("status") == "delayed")

    avg_recent_bank = sum(b.get("balance", 0) for b in bank[-3:]) / max(len(bank[-3:]), 1)
    avg_recent_sales = sum(s.get("amount", 0) for s in sales[-3:]) / max(len(sales[-3:]), 1)

    return f"""You are a SENIOR CREDIT RECOVERY SPECIALIST advising on an active recovery case. Be PRACTICAL, SPECIFIC, and ACTION-ORIENTED. Use the borrower's actual financials. Suggest concrete recovery strategies (restructure, settle, escalate, secure collateral, etc.) with reasoning grounded in the numbers.

ACTIVE RECOVERY CASE
- Borrower: {case.get('borrower_name','')}
- Status: {case.get('status','').upper()}
- Priority: {case.get('priority','').upper()}
- Assigned to: {case.get('assigned_to_name') or 'Unassigned'}
- Deadline: {case.get('deadline') or 'Not set'}
- Current next action: {case.get('next_action','none')}
- Opened: {case.get('opened_at','')[:10]} ({'auto-opened on critical risk' if case.get('auto_created') else 'manual'})

BORROWER PROFILE
- Sector: {borrower.get('sector','')}
- Location: {borrower.get('location','')}
- Loan: ₹{borrower.get('loan_amount',0):,.0f} ({borrower.get('loan_type','')})
- Outstanding: ₹{borrower.get('outstanding_amount',0):,.0f}
- Risk Score: {borrower.get('risk_score',0):.1f}/100 ({borrower.get('risk_category','').upper()})
- Contact: {borrower.get('contact_person','')} ({borrower.get('contact_phone','')})

FINANCIAL SNAPSHOT
- Avg recent monthly sales: ₹{avg_recent_sales:,.0f}
- Avg recent bank balance: ₹{avg_recent_bank:,.0f}
- Repayment history: {bounced} bounced, {delayed} delayed (of {len(reps)} cycles)
{recent_pnl}

KEY FINANCIAL RATIOS
{ratio_summary or '(Balance sheet / P&L not uploaded)'}

CASE TIMELINE (most recent first)
{timeline_summary}

When answering:
1. Be CONCRETE about rupee amounts, tenure, and timing
2. Suggest realistic outcomes (e.g., "restructure to 18 months at 10% rate cuts EMI from X to Y")
3. Reference specific signals from the data
4. Recommend escalation only when truly warranted
5. Keep responses under 250 words unless asked for detail"""


async def recovery_ai(context: str, session_id: str, message: str) -> str:
    if not EMERGENT_KEY:
        return _fallback_recovery(message)
    try:
        chat = LlmChat(api_key=EMERGENT_KEY, session_id=session_id, system_message=context).with_model("anthropic", "claude-sonnet-4-6")
        response = await chat.send_message(UserMessage(text=message))
        return str(response)
    except Exception as e:
        return f"{_fallback_recovery(message)}\n\n_(AI service unavailable: {str(e)[:100]})_"


def _fallback_recovery(message: str) -> str:
    msg = message.lower()
    if any(k in msg for k in ["restructure", "reschedule", "tenure"]):
        return ("Restructure options to consider:\n"
                "1. Extend tenure by 12-18 months — reduces monthly EMI burden\n"
                "2. Convert to moratorium for 3-6 months if cash is genuinely seasonal\n"
                "3. Step-up structure: 50% EMI for first 6 months, full thereafter\n"
                "Compute the new DSCR with proposed terms — only viable if it lands above 1.25.")
    if any(k in msg for k in ["settle", "settlement", "otc", "one time"]):
        return ("One-Time Settlement (OTS) framework:\n"
                "- Typical OTS = 60-80% of outstanding for distressed accounts\n"
                "- Settle only if recovery via normal channels is <50% likely\n"
                "- Insist on lump-sum or 3-installment max\n"
                "- Get NOC and PDC for the settled amount")
    if any(k in msg for k in ["collateral", "security", "additional"]):
        return ("Secure additional comfort:\n"
                "- Personal guarantee from promoter (if not already)\n"
                "- Pledge of FD / mutual funds\n"
                "- Additional property mortgage\n"
                "- Hypothecation of receivables or inventory\n"
                "Get a valuation report before accepting any new collateral.")
    if any(k in msg for k in ["next", "action", "step", "do"]):
        return ("Recommended next steps (in order):\n"
                "1. Schedule a face-to-face meeting within 48 hours\n"
                "2. Request latest 3-month bank statements + GST returns\n"
                "3. Get a written cash flow forecast for next 6 months\n"
                "4. Reassess collateral value\n"
                "5. Document everything in the timeline above")
    return ("I can help plan recovery actions. Try asking:\n"
            "- What's the best restructure option for this borrower?\n"
            "- Should we consider a one-time settlement?\n"
            "- What additional collateral makes sense here?\n"
            "- What are the next 3 concrete steps for this case?\n"
            "- Is this borrower likely to recover, or should we escalate?")
