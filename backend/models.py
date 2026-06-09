"""Pydantic models for MSME Credit Risk System."""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime, timezone
import uuid


def gen_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# -------- USER --------
class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str
    role: Literal["admin", "analyst", "rm"] = "analyst"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
    created_at: str


# -------- BORROWER --------
class BorrowerCreate(BaseModel):
    business_name: str
    sector: str
    location: str
    loan_amount: float
    loan_type: str
    sanction_date: str
    outstanding_amount: float
    gst_number: Optional[str] = ""
    contact_person: Optional[str] = ""
    contact_phone: Optional[str] = ""


class BorrowerUpdate(BaseModel):
    business_name: Optional[str] = None
    sector: Optional[str] = None
    location: Optional[str] = None
    loan_amount: Optional[float] = None
    loan_type: Optional[str] = None
    sanction_date: Optional[str] = None
    outstanding_amount: Optional[float] = None
    gst_number: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None


class Borrower(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=gen_id)
    business_name: str
    sector: str
    location: str
    loan_amount: float
    loan_type: str
    sanction_date: str
    outstanding_amount: float
    gst_number: Optional[str] = ""
    contact_person: Optional[str] = ""
    contact_phone: Optional[str] = ""
    risk_score: float = 0.0
    risk_category: str = "low"
    created_by: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


# -------- FINANCIAL DATA --------
class SalesEntry(BaseModel):
    month: str  # YYYY-MM
    amount: float


class BankBalanceEntry(BaseModel):
    month: str
    balance: float
    avg_balance: float = 0.0


class RepaymentEntry(BaseModel):
    due_date: str
    paid_date: Optional[str] = None
    amount: float
    status: Literal["paid", "delayed", "bounced", "pending"]
    days_delayed: int = 0


# -------- WARNING SIGNAL --------
class WarningSignal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=gen_id)
    borrower_id: str
    signal_type: str  # sales_decline, cash_flow_stress, emi_delay, cheque_bounce, negative_news, high_leverage, gst_mismatch, low_bank_balance, revenue_volatility
    severity: Literal["low", "medium", "high", "critical"]
    explanation: str
    suggested_action: str
    detected_at: str = Field(default_factory=now_iso)


# -------- ALERT --------
class Alert(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=gen_id)
    borrower_id: str
    borrower_name: str = ""
    alert_type: str
    message: str
    severity: Literal["low", "medium", "high", "critical"]
    is_read: bool = False
    created_at: str = Field(default_factory=now_iso)


# -------- ANALYST NOTE --------
class AnalystNoteCreate(BaseModel):
    borrower_id: str
    content: str


class AnalystNote(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=gen_id)
    borrower_id: str
    content: str
    created_by: str
    created_by_name: Optional[str] = ""
    created_at: str = Field(default_factory=now_iso)


# -------- CHAT --------
class ChatMessageIn(BaseModel):
    borrower_id: str
    message: str
    session_id: Optional[str] = None


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=gen_id)
    borrower_id: str
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: str = Field(default_factory=now_iso)



# -------- RECOVERY CASE --------
class RecoveryCaseCreate(BaseModel):
    borrower_id: str
    deadline: Optional[str] = None  # YYYY-MM-DD
    next_action: Optional[str] = ""
    priority: Literal["low", "medium", "high"] = "high"
    assigned_to: Optional[str] = None


class RecoveryCaseUpdate(BaseModel):
    status: Optional[Literal["open", "in_progress", "resolved", "escalated"]] = None
    deadline: Optional[str] = None
    next_action: Optional[str] = None
    priority: Optional[Literal["low", "medium", "high"]] = None
    assigned_to: Optional[str] = None


class RecoveryTimelineEvent(BaseModel):
    type: Literal["note", "status_change", "action_update", "contact", "system"]
    content: str


class RecoveryCase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=gen_id)
    borrower_id: str
    borrower_name: str
    status: Literal["open", "in_progress", "resolved", "escalated"] = "open"
    priority: Literal["low", "medium", "high"] = "high"
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = ""
    deadline: Optional[str] = None
    next_action: Optional[str] = ""
    opened_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
    resolved_at: Optional[str] = None
    auto_created: bool = False


# -------- AUDIT LOG --------
class AuditLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=gen_id)
    user_id: str
    user_name: str = ""
    user_role: str = ""
    action: str  # create, update, delete, upload, recompute, export, login
    resource: str  # borrower, note, recovery, user, alert
    resource_id: Optional[str] = ""
    resource_name: Optional[str] = ""
    details: Optional[str] = ""


# -------- BALANCE SHEET / P&L --------
class BalanceSheetEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=gen_id)
    borrower_id: str
    period: str  # e.g., "2025-Q4" or "2025-03"
    current_assets: float = 0
    inventory: float = 0
    cash: float = 0
    receivables: float = 0
    fixed_assets: float = 0
    other_assets: float = 0
    current_liabilities: float = 0
    short_term_debt: float = 0
    long_term_debt: float = 0
    other_liabilities: float = 0
    equity: float = 0
    created_at: str = Field(default_factory=now_iso)


class PnLEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=gen_id)
    borrower_id: str
    period: str
    revenue: float = 0
    cogs: float = 0
    gross_profit: float = 0
    operating_expenses: float = 0
    ebitda: float = 0
    depreciation: float = 0
    ebit: float = 0
    interest_expense: float = 0
    pbt: float = 0
    tax: float = 0
    net_profit: float = 0
    created_at: str = Field(default_factory=now_iso)

    at: str = Field(default_factory=now_iso)
