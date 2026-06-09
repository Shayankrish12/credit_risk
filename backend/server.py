"""MSME Credit Risk Early Warning System - FastAPI backend."""
import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import Response
from pydantic import BaseModel
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from models import (
    UserSignup, UserLogin, UserOut,
    BorrowerCreate, BorrowerUpdate, Borrower,
    WarningSignal, Alert, AnalystNoteCreate, AnalystNote,
    ChatMessageIn, ChatMessage,
    RecoveryCaseCreate, RecoveryCaseUpdate, RecoveryCase, RecoveryTimelineEvent,
    AuditLog,
    gen_id, now_iso,
)
from auth import hash_password, verify_password, create_token, get_current_user, require_role
from risk_engine import compute_risk, alerts_from_signals
from sample_data import generate_all_borrowers
from file_parser import (parse_csv_xlsx, parse_pdf_text, parse_sales_data,
                         parse_bank_data, parse_repayment_data, analyze_news_sentiment,
                         parse_balance_sheet, parse_pnl, TEMPLATES)
from report_generator import build_pdf, build_docx
from ai_copilot import build_borrower_context, ai_chat
from recovery_ai import build_recovery_context, recovery_ai
from financials import compute_ratios, ratio_risk_factors
from sample_data import generate_bs_pnl


# MongoDB
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="MSME Credit Risk Early Warning System")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ---------------- HEALTH ----------------
@api.get("/")
async def root():
    return {"status": "ok", "service": "MSME Credit Risk Early Warning System"}


# ---------------- AUTH ----------------
@api.post("/auth/signup")
async def signup(payload: UserSignup):
    existing = await db.users.find_one({"email": payload.email}, {"_id": 0})
    if existing:
        raise HTTPException(400, "Email already registered")
    user_id = gen_id()
    doc = {
        "id": user_id,
        "email": payload.email,
        "name": payload.name,
        "role": payload.role,
        "password_hash": hash_password(payload.password),
        "created_at": now_iso(),
    }
    await db.users.insert_one(doc.copy())
    token = create_token(user_id, payload.email, payload.role)
    return {
        "token": token,
        "user": {"id": user_id, "email": payload.email, "name": payload.name, "role": payload.role, "created_at": doc["created_at"]},
    }


@api.post("/auth/login")
async def login(payload: UserLogin):
    user = await db.users.find_one({"email": payload.email}, {"_id": 0})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = create_token(user["id"], user["email"], user["role"])
    return {
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"], "created_at": user["created_at"]},
    }


@api.get("/auth/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    if not u:
        raise HTTPException(404, "User not found")
    return UserOut(**u)


@api.get("/auth/users")
async def list_users(user: dict = Depends(require_role("admin"))):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return users


# ---------------- SEED ----------------
@api.post("/seed")
async def seed_data(user: dict = Depends(get_current_user)):
    """Idempotent seed: only seeds if borrowers collection is empty."""
    existing = await db.borrowers.count_documents({})
    if existing > 0:
        return {"seeded": False, "borrower_count": existing, "message": "Data already seeded"}

    borrowers_data = generate_all_borrowers()
    seeded_ids = []
    for b in borrowers_data:
        borrower_id = gen_id()
        sales = b.pop("sales")
        bank = b.pop("bank")
        repayments = b.pop("repayments")
        news_sent = b.pop("news_sentiment", 0.0)

        # Compute risk
        score, category, factors, signals = compute_risk(b, sales, bank, repayments, news_sent)

        borrower_doc = {
            "id": borrower_id,
            **b,
            "risk_score": score,
            "risk_category": category,
            "created_by": user["id"],
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "news_sentiment": news_sent,
            "risk_factors": factors,
        }
        await db.borrowers.insert_one(borrower_doc.copy())

        # Store financial data
        for s in sales:
            await db.sales_data.insert_one({"id": gen_id(), "borrower_id": borrower_id, **s})
        for bk in bank:
            await db.bank_balances.insert_one({"id": gen_id(), "borrower_id": borrower_id, **bk})
        for r in repayments:
            await db.repayments.insert_one({"id": gen_id(), "borrower_id": borrower_id, **r})

        # Store signals
        for s in signals:
            await db.warning_signals.insert_one({
                "id": gen_id(), "borrower_id": borrower_id, **s, "detected_at": now_iso()
            })

        # Store risk history
        await db.risk_history.insert_one({
            "id": gen_id(), "borrower_id": borrower_id, "score": score, "category": category, "recorded_at": now_iso()
        })

        # Generate alerts
        for a in alerts_from_signals(b, score, signals):
            await db.alerts.insert_one({
                "id": gen_id(), "borrower_id": borrower_id, "borrower_name": b["business_name"],
                "is_read": False, "created_at": now_iso(), **a
            })

        seeded_ids.append(borrower_id)

    return {"seeded": True, "count": len(seeded_ids)}


# ---------------- BORROWERS ----------------
@api.get("/borrowers")
async def list_borrowers(
    search: Optional[str] = None,
    sector: Optional[str] = None,
    risk_category: Optional[str] = None,
    sort_by: str = "risk_score",
    order: str = "desc",
    page: int = 1,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    query = {}
    if search:
        query["business_name"] = {"$regex": search, "$options": "i"}
    if sector:
        query["sector"] = sector
    if risk_category:
        query["risk_category"] = risk_category

    sort_dir = -1 if order == "desc" else 1
    skip = max(0, (page - 1) * limit)
    total = await db.borrowers.count_documents(query)
    items = await db.borrowers.find(query, {"_id": 0, "risk_factors": 0}).sort(sort_by, sort_dir).skip(skip).limit(limit).to_list(limit)
    return {"items": items, "total": total, "page": page, "limit": limit}


@api.post("/borrowers", response_model=Borrower)
async def create_borrower(payload: BorrowerCreate, user: dict = Depends(require_role("admin", "analyst"))):
    borrower = Borrower(**payload.model_dump(), created_by=user["id"])
    doc = borrower.model_dump()
    await db.borrowers.insert_one(doc.copy())
    await _recompute_and_persist(borrower.id)
    updated_b = await db.borrowers.find_one({"id": borrower.id}, {"_id": 0})
    await log_audit(user, "create", "borrower", borrower.id, borrower.business_name)
    return Borrower(**updated_b)


@api.post("/borrowers/bulk-import")
async def bulk_import_borrowers(
    file: UploadFile = File(...),
    user: dict = Depends(require_role("admin", "analyst")),
):
    """Bulk-create borrowers from a CSV/XLSX file. Required columns: business_name, sector, location, loan_amount, loan_type, sanction_date, outstanding_amount. Optional: gst_number, contact_person, contact_phone."""
    content = await file.read()
    try:
        df = parse_csv_xlsx(content, file.filename or "upload.csv")
    except Exception as e:
        raise HTTPException(400, f"Could not parse file: {e}")

    required = ["business_name", "sector", "location", "loan_amount", "loan_type", "sanction_date", "outstanding_amount"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise HTTPException(400, f"Missing required columns: {', '.join(missing)}")

    created = []
    errors = []
    for idx, row in df.iterrows():
        try:
            payload = BorrowerCreate(
                business_name=str(row["business_name"]).strip(),
                sector=str(row["sector"]).strip(),
                location=str(row["location"]).strip(),
                loan_amount=float(row["loan_amount"]),
                loan_type=str(row["loan_type"]).strip(),
                sanction_date=str(row["sanction_date"])[:10],
                outstanding_amount=float(row["outstanding_amount"]),
                gst_number=str(row.get("gst_number", "") or ""),
                contact_person=str(row.get("contact_person", "") or ""),
                contact_phone=str(row.get("contact_phone", "") or ""),
            )
            borrower = Borrower(**payload.model_dump(), created_by=user["id"])
            await db.borrowers.insert_one(borrower.model_dump().copy())
            await _recompute_and_persist(borrower.id)
            created.append({"id": borrower.id, "business_name": borrower.business_name})
        except Exception as e:
            errors.append({"row": int(idx) + 2, "error": str(e)[:200]})

    await log_audit(user, "bulk_import", "borrower", "", "", f"Created {len(created)}, errors {len(errors)}")
    return {"created": len(created), "errors": errors, "items": created}


@api.get("/borrowers/{borrower_id}")
async def get_borrower(borrower_id: str, user: dict = Depends(get_current_user)):
    b = await db.borrowers.find_one({"id": borrower_id}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Borrower not found")
    return b


@api.put("/borrowers/{borrower_id}", response_model=Borrower)
async def update_borrower(borrower_id: str, payload: BorrowerUpdate, user: dict = Depends(require_role("admin", "analyst"))):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updates["updated_at"] = now_iso()
    result = await db.borrowers.update_one({"id": borrower_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(404, "Borrower not found")

    # Recompute risk if any risk-relevant field changed
    RISK_FIELDS = {"loan_amount", "outstanding_amount", "sector"}
    if RISK_FIELDS & updates.keys():
        await _recompute_and_persist(borrower_id)

    b = await db.borrowers.find_one({"id": borrower_id}, {"_id": 0, "risk_factors": 0})
    await log_audit(user, "update", "borrower", borrower_id, b.get("business_name", ""), f"Updated fields: {', '.join(updates.keys())}")
    return Borrower(**b)


@api.delete("/borrowers/{borrower_id}")
async def delete_borrower(borrower_id: str, user: dict = Depends(require_role("admin"))):
    b = await db.borrowers.find_one({"id": borrower_id}, {"_id": 0})
    result = await db.borrowers.delete_one({"id": borrower_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Borrower not found")
    await db.sales_data.delete_many({"borrower_id": borrower_id})
    await db.bank_balances.delete_many({"borrower_id": borrower_id})
    await db.repayments.delete_many({"borrower_id": borrower_id})
    await db.warning_signals.delete_many({"borrower_id": borrower_id})
    await db.alerts.delete_many({"borrower_id": borrower_id})
    await db.analyst_notes.delete_many({"borrower_id": borrower_id})
    await db.chat_messages.delete_many({"borrower_id": borrower_id})
    await db.risk_history.delete_many({"borrower_id": borrower_id})
    await db.recovery_cases.delete_many({"borrower_id": borrower_id})
    await log_audit(user, "delete", "borrower", borrower_id, b.get("business_name", "") if b else "")
    return {"deleted": True}


@api.get("/borrowers/{borrower_id}/details")
async def borrower_details(borrower_id: str, user: dict = Depends(get_current_user)):
    b = await db.borrowers.find_one({"id": borrower_id}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Borrower not found")
    sales = await db.sales_data.find({"borrower_id": borrower_id}, {"_id": 0}).sort("month", 1).to_list(100)
    bank = await db.bank_balances.find({"borrower_id": borrower_id}, {"_id": 0}).sort("month", 1).to_list(100)
    reps = await db.repayments.find({"borrower_id": borrower_id}, {"_id": 0}).sort("due_date", 1).to_list(100)
    signals = await db.warning_signals.find({"borrower_id": borrower_id}, {"_id": 0}).sort("detected_at", -1).to_list(100)
    alerts = await db.alerts.find({"borrower_id": borrower_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    notes = await db.analyst_notes.find({"borrower_id": borrower_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    history = await db.risk_history.find({"borrower_id": borrower_id}, {"_id": 0}).sort("recorded_at", 1).to_list(100)
    return {
        "borrower": b, "sales": sales, "bank": bank, "repayments": reps,
        "signals": signals, "alerts": alerts, "notes": notes, "risk_history": history,
    }


# ---------------- UPLOAD ----------------
@api.post("/borrowers/{borrower_id}/upload")
async def upload_file(
    borrower_id: str,
    file_type: str = Form(...),  # sales, bank, repayment, news, financial
    file: UploadFile = File(...),
    user: dict = Depends(require_role("admin", "analyst")),
):
    b = await db.borrowers.find_one({"id": borrower_id}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Borrower not found")

    content = await file.read()
    filename = file.filename or "upload"
    inserted = 0

    if file_type == "news":
        if filename.lower().endswith(".pdf"):
            text = parse_pdf_text(content)
        else:
            text = content.decode("utf-8", errors="ignore")
        sentiment = analyze_news_sentiment(text)
        await db.borrowers.update_one({"id": borrower_id}, {"$set": {"news_sentiment": sentiment}})
        await db.uploaded_files.insert_one({
            "id": gen_id(), "borrower_id": borrower_id, "filename": filename,
            "file_type": file_type, "uploaded_by": user["id"], "created_at": now_iso(),
            "extra": {"sentiment": sentiment}
        })
        inserted = 1
    else:
        try:
            df = parse_csv_xlsx(content, filename)
        except Exception as e:
            raise HTTPException(400, f"Could not parse file: {e}")

        if file_type == "sales":
            rows = parse_sales_data(df)
            for r in rows:
                await db.sales_data.update_one(
                    {"borrower_id": borrower_id, "month": r["month"]},
                    {"$set": {"id": gen_id(), "borrower_id": borrower_id, **r}},
                    upsert=True,
                )
                inserted += 1
        elif file_type == "bank":
            rows = parse_bank_data(df)
            for r in rows:
                await db.bank_balances.update_one(
                    {"borrower_id": borrower_id, "month": r["month"]},
                    {"$set": {"id": gen_id(), "borrower_id": borrower_id, **r}},
                    upsert=True,
                )
                inserted += 1
        elif file_type == "repayment":
            rows = parse_repayment_data(df)
            for r in rows:
                await db.repayments.update_one(
                    {"borrower_id": borrower_id, "due_date": r["due_date"]},
                    {"$set": {"id": gen_id(), "borrower_id": borrower_id, **r}},
                    upsert=True,
                )
                inserted += 1
        elif file_type == "balance_sheet":
            rows = parse_balance_sheet(df)
            for r in rows:
                await db.balance_sheets.update_one(
                    {"borrower_id": borrower_id, "period": r["period"]},
                    {"$set": {"id": gen_id(), "borrower_id": borrower_id, **r}},
                    upsert=True,
                )
                inserted += 1
        elif file_type == "pnl":
            rows = parse_pnl(df)
            for r in rows:
                await db.pnl_statements.update_one(
                    {"borrower_id": borrower_id, "period": r["period"]},
                    {"$set": {"id": gen_id(), "borrower_id": borrower_id, **r}},
                    upsert=True,
                )
                inserted += 1
        else:
            raise HTTPException(400, f"Unsupported file_type: {file_type}")

        await db.uploaded_files.insert_one({
            "id": gen_id(), "borrower_id": borrower_id, "filename": filename,
            "file_type": file_type, "uploaded_by": user["id"], "created_at": now_iso(),
            "extra": {"rows": inserted}
        })

    # Recompute risk after upload
    await _recompute_and_persist(borrower_id)
    await log_audit(user, "upload", "borrower", borrower_id, b.get("business_name", ""), f"file_type={file_type}, rows={inserted}")
    return {"uploaded": True, "rows_processed": inserted}


# ---------------- AUDIT LOG ----------------
async def log_audit(user: dict, action: str, resource: str, resource_id: str = "", resource_name: str = "", details: str = ""):
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    await db.audit_logs.insert_one({
        "id": gen_id(),
        "user_id": user["id"],
        "user_name": u.get("name", "") if u else user.get("email", ""),
        "user_role": user.get("role", ""),
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
        "resource_name": resource_name,
        "details": details,
        "at": now_iso(),
    })


# ---------------- RISK RECOMPUTE ----------------
async def _recompute_and_persist(borrower_id: str):
    b = await db.borrowers.find_one({"id": borrower_id}, {"_id": 0})
    if not b:
        return
    prev_category = b.get("risk_category", "low")
    sales = await db.sales_data.find({"borrower_id": borrower_id}, {"_id": 0}).to_list(200)
    bank = await db.bank_balances.find({"borrower_id": borrower_id}, {"_id": 0}).to_list(200)
    reps = await db.repayments.find({"borrower_id": borrower_id}, {"_id": 0}).to_list(200)
    news_sent = b.get("news_sentiment", 0.0)

    score, category, factors, signals = compute_risk(b, sales, bank, reps, news_sent)

    # Add ratio-based factors if balance sheet + P&L available
    latest_bs = await db.balance_sheets.find_one({"borrower_id": borrower_id}, {"_id": 0}, sort=[("period", -1)])
    latest_pnl = await db.pnl_statements.find_one({"borrower_id": borrower_id}, {"_id": 0}, sort=[("period", -1)])
    if latest_bs and latest_pnl:
        ratios = compute_ratios(latest_bs, latest_pnl)
        r_factors, r_signals, r_pts = ratio_risk_factors(ratios)
        factors.extend(r_factors)
        signals.extend(r_signals)
        score = min(100.0, round(score + r_pts, 1))
        # Re-categorize after ratio additions
        if score < 25:
            category = "low"
        elif score < 50:
            category = "moderate"
        elif score < 75:
            category = "high"
        else:
            category = "critical"
        factors.sort(key=lambda x: x["impact"], reverse=True)

    await db.borrowers.update_one(
        {"id": borrower_id},
        {"$set": {"risk_score": score, "risk_category": category, "risk_factors": factors, "updated_at": now_iso()}},
    )
    # Replace signals
    await db.warning_signals.delete_many({"borrower_id": borrower_id})
    for s in signals:
        await db.warning_signals.insert_one({
            "id": gen_id(), "borrower_id": borrower_id, **s, "detected_at": now_iso()
        })
    # Append risk history
    await db.risk_history.insert_one({
        "id": gen_id(), "borrower_id": borrower_id, "score": score, "category": category, "recorded_at": now_iso()
    })
    # Generate fresh alerts
    for a in alerts_from_signals(b, score, signals):
        await db.alerts.insert_one({
            "id": gen_id(), "borrower_id": borrower_id, "borrower_name": b["business_name"],
            "is_read": False, "created_at": now_iso(), **a
        })

    # Auto-create recovery case when borrower hits critical
    if category == "critical":
        existing = await db.recovery_cases.find_one(
            {"borrower_id": borrower_id, "status": {"$in": ["open", "in_progress", "escalated"]}},
            {"_id": 0}
        )
        if not existing:
            case = {
                "id": gen_id(),
                "borrower_id": borrower_id,
                "borrower_name": b["business_name"],
                "status": "open",
                "priority": "high",
                "assigned_to": None,
                "assigned_to_name": "",
                "deadline": None,
                "next_action": "Initial outreach: schedule borrower call within 48 hours",
                "opened_at": now_iso(),
                "updated_at": now_iso(),
                "resolved_at": None,
                "auto_created": True,
            }
            await db.recovery_cases.insert_one(case.copy())
            await db.recovery_timeline.insert_one({
                "id": gen_id(),
                "case_id": case["id"],
                "type": "system",
                "content": f"Recovery case auto-opened — risk escalated from {prev_category.upper()} to CRITICAL (score {score:.1f})",
                "by_user_id": "system",
                "by_user_name": "System",
                "at": now_iso(),
            })


@api.post("/borrowers/{borrower_id}/recompute")
async def recompute_risk(borrower_id: str, user: dict = Depends(get_current_user)):
    await _recompute_and_persist(borrower_id)
    b = await db.borrowers.find_one({"id": borrower_id}, {"_id": 0})
    return {"recomputed": True, "risk_score": b["risk_score"], "risk_category": b["risk_category"]}


# ---------------- ALERTS ----------------
@api.get("/alerts")
async def list_alerts(unread_only: bool = False, user: dict = Depends(get_current_user)):
    q = {"is_read": False} if unread_only else {}
    alerts = await db.alerts.find(q, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    return alerts


@api.post("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str, user: dict = Depends(get_current_user)):
    await db.alerts.update_one({"id": alert_id}, {"$set": {"is_read": True}})
    return {"updated": True}


# ---------------- NOTES ----------------
@api.post("/notes", response_model=AnalystNote)
async def create_note(payload: AnalystNoteCreate, user: dict = Depends(require_role("admin", "analyst"))):
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    note = AnalystNote(borrower_id=payload.borrower_id, content=payload.content,
                       created_by=user["id"], created_by_name=u.get("name", "") if u else "")
    await db.analyst_notes.insert_one(note.model_dump())
    b = await db.borrowers.find_one({"id": payload.borrower_id}, {"_id": 0})
    await log_audit(user, "create", "note", note.id, b.get("business_name", "") if b else "")
    return note


@api.get("/notes/{borrower_id}")
async def list_notes(borrower_id: str, user: dict = Depends(get_current_user)):
    notes = await db.analyst_notes.find({"borrower_id": borrower_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return notes


# ---------------- CHAT / AI COPILOT ----------------
@api.post("/chat")
async def chat(payload: ChatMessageIn, user: dict = Depends(get_current_user)):
    b = await db.borrowers.find_one({"id": payload.borrower_id}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Borrower not found")

    sales = await db.sales_data.find({"borrower_id": payload.borrower_id}, {"_id": 0}).to_list(200)
    bank = await db.bank_balances.find({"borrower_id": payload.borrower_id}, {"_id": 0}).to_list(200)
    reps = await db.repayments.find({"borrower_id": payload.borrower_id}, {"_id": 0}).to_list(200)
    signals = await db.warning_signals.find({"borrower_id": payload.borrower_id}, {"_id": 0}).to_list(100)
    factors = b.get("risk_factors", [])

    ctx = build_borrower_context(b, sales, bank, reps, signals, factors)
    session_id = payload.session_id or f"{user['id']}-{payload.borrower_id}"

    # Save user message
    user_msg = {
        "id": gen_id(), "borrower_id": payload.borrower_id, "session_id": session_id,
        "role": "user", "content": payload.message, "created_at": now_iso(),
    }
    await db.chat_messages.insert_one(user_msg.copy())

    # Get AI response
    response_text = await ai_chat(ctx, session_id, payload.message)

    # Save assistant message
    bot_msg = {
        "id": gen_id(), "borrower_id": payload.borrower_id, "session_id": session_id,
        "role": "assistant", "content": response_text, "created_at": now_iso(),
    }
    await db.chat_messages.insert_one(bot_msg.copy())

    return {"session_id": session_id, "response": response_text}


@api.get("/chat/{borrower_id}")
async def chat_history(borrower_id: str, session_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {"borrower_id": borrower_id}
    if session_id:
        q["session_id"] = session_id
    msgs = await db.chat_messages.find(q, {"_id": 0}).sort("created_at", 1).to_list(500)
    return msgs


# ---------------- REPORTS ----------------
@api.get("/reports/{borrower_id}/pdf")
async def export_pdf(borrower_id: str, user: dict = Depends(get_current_user)):
    b = await db.borrowers.find_one({"id": borrower_id}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Borrower not found")
    sales = await db.sales_data.find({"borrower_id": borrower_id}, {"_id": 0}).sort("month", 1).to_list(200)
    bank = await db.bank_balances.find({"borrower_id": borrower_id}, {"_id": 0}).sort("month", 1).to_list(200)
    reps = await db.repayments.find({"borrower_id": borrower_id}, {"_id": 0}).sort("due_date", 1).to_list(200)
    signals = await db.warning_signals.find({"borrower_id": borrower_id}, {"_id": 0}).to_list(100)
    notes = await db.analyst_notes.find({"borrower_id": borrower_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    factors = b.get("risk_factors", [])

    pdf_bytes = build_pdf(b, factors, signals, notes, sales, bank, reps)
    safe_name = b["business_name"].replace(" ", "_").replace("/", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_credit_note.pdf"'},
    )


@api.get("/reports/{borrower_id}/docx")
async def export_docx(borrower_id: str, user: dict = Depends(get_current_user)):
    b = await db.borrowers.find_one({"id": borrower_id}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Borrower not found")
    sales = await db.sales_data.find({"borrower_id": borrower_id}, {"_id": 0}).sort("month", 1).to_list(200)
    bank = await db.bank_balances.find({"borrower_id": borrower_id}, {"_id": 0}).sort("month", 1).to_list(200)
    reps = await db.repayments.find({"borrower_id": borrower_id}, {"_id": 0}).sort("due_date", 1).to_list(200)
    signals = await db.warning_signals.find({"borrower_id": borrower_id}, {"_id": 0}).to_list(100)
    notes = await db.analyst_notes.find({"borrower_id": borrower_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    factors = b.get("risk_factors", [])

    docx_bytes = build_docx(b, factors, signals, notes, sales, bank, reps)
    safe_name = b["business_name"].replace(" ", "_").replace("/", "_")
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_credit_note.docx"'},
    )


# ---------------- PORTFOLIO ----------------
@api.get("/portfolio/overview")
async def portfolio_overview(user: dict = Depends(get_current_user)):
    total = await db.borrowers.count_documents({})
    by_cat = {}
    for cat in ["low", "moderate", "high", "critical"]:
        by_cat[cat] = await db.borrowers.count_documents({"risk_category": cat})

    cursor = db.borrowers.find({}, {"_id": 0, "risk_factors": 0}).limit(2000)
    all_borrowers = await cursor.to_list(2000)
    avg_score = sum(b.get("risk_score", 0) for b in all_borrowers) / total if total else 0
    outstanding_at_risk = sum(b.get("outstanding_amount", 0) for b in all_borrowers if b.get("risk_category") in ("high", "critical"))
    total_outstanding = sum(b.get("outstanding_amount", 0) for b in all_borrowers)

    top_risky = sorted(all_borrowers, key=lambda x: x.get("risk_score", 0), reverse=True)[:5]

    # Sector exposure
    sector_map = {}
    for b in all_borrowers:
        sec = b.get("sector", "Other")
        sector_map.setdefault(sec, {"sector": sec, "count": 0, "outstanding": 0, "avg_risk": 0, "_risks": []})
        sector_map[sec]["count"] += 1
        sector_map[sec]["outstanding"] += b.get("outstanding_amount", 0)
        sector_map[sec]["_risks"].append(b.get("risk_score", 0))
    sector_exposure = []
    for s in sector_map.values():
        s["avg_risk"] = round(sum(s["_risks"]) / len(s["_risks"]), 1) if s["_risks"] else 0
        del s["_risks"]
        sector_exposure.append(s)

    recent_alerts = await db.alerts.find({}, {"_id": 0}).sort("created_at", -1).limit(10).to_list(10)

    return {
        "total_borrowers": total,
        "by_category": by_cat,
        "avg_risk_score": round(avg_score, 1),
        "outstanding_at_risk": outstanding_at_risk,
        "total_outstanding": total_outstanding,
        "top_risky": top_risky,
        "sector_exposure": sector_exposure,
        "recent_alerts": recent_alerts,
    }


@api.get("/portfolio/analytics")
async def portfolio_analytics(user: dict = Depends(get_current_user)):
    # Signal frequency
    pipeline = [
        {"$group": {"_id": "$signal_type", "count": {"$sum": 1}}},
        {"$project": {"_id": 0, "signal_type": "$_id", "count": 1}},
        {"$sort": {"count": -1}},
    ]
    signal_freq = await db.warning_signals.aggregate(pipeline).to_list(50)

    # Risk distribution
    all_borrowers = await db.borrowers.find({}, {"_id": 0, "risk_factors": 0}).to_list(1000)
    bins = {"0-25": 0, "25-50": 0, "50-75": 0, "75-100": 0}
    for b in all_borrowers:
        s = b.get("risk_score", 0)
        if s < 25:
            bins["0-25"] += 1
        elif s < 50:
            bins["25-50"] += 1
        elif s < 75:
            bins["50-75"] += 1
        else:
            bins["75-100"] += 1
    risk_dist = [{"range": k, "count": v} for k, v in bins.items()]

    return {"signal_frequency": signal_freq, "risk_distribution": risk_dist}


# ---------------- RECOVERY WORKFLOW ----------------
@api.get("/recovery")
async def list_recovery_cases(
    status: Optional[str] = None,
    assigned_to_me: bool = False,
    user: dict = Depends(get_current_user),
):
    q = {}
    if status:
        q["status"] = status
    if assigned_to_me:
        q["assigned_to"] = user["id"]
    cases = await db.recovery_cases.find(q, {"_id": 0}).sort("opened_at", -1).to_list(500)

    stats = {
        "open": await db.recovery_cases.count_documents({"status": "open"}),
        "in_progress": await db.recovery_cases.count_documents({"status": "in_progress"}),
        "escalated": await db.recovery_cases.count_documents({"status": "escalated"}),
        "resolved": await db.recovery_cases.count_documents({"status": "resolved"}),
    }
    return {"items": cases, "stats": stats}


@api.post("/recovery", response_model=RecoveryCase)
async def create_recovery_case(payload: RecoveryCaseCreate, user: dict = Depends(require_role("admin", "analyst", "rm"))):
    b = await db.borrowers.find_one({"id": payload.borrower_id}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Borrower not found")
    existing = await db.recovery_cases.find_one(
        {"borrower_id": payload.borrower_id, "status": {"$in": ["open", "in_progress", "escalated"]}},
        {"_id": 0}
    )
    if existing:
        raise HTTPException(400, "An active recovery case already exists for this borrower")

    assigned_name = ""
    if payload.assigned_to:
        u = await db.users.find_one({"id": payload.assigned_to}, {"_id": 0})
        assigned_name = u.get("name", "") if u else ""

    case = RecoveryCase(
        borrower_id=payload.borrower_id,
        borrower_name=b["business_name"],
        priority=payload.priority,
        deadline=payload.deadline,
        next_action=payload.next_action or "",
        assigned_to=payload.assigned_to,
        assigned_to_name=assigned_name,
        auto_created=False,
    )
    await db.recovery_cases.insert_one(case.model_dump().copy())
    await db.recovery_timeline.insert_one({
        "id": gen_id(), "case_id": case.id, "type": "system",
        "content": f"Case opened manually by {user.get('email','')}",
        "by_user_id": user["id"], "by_user_name": user.get("email", ""), "at": now_iso(),
    })
    await log_audit(user, "create", "recovery", case.id, case.borrower_name)
    return case


@api.get("/recovery/{case_id}")
async def get_recovery_case(case_id: str, user: dict = Depends(get_current_user)):
    case = await db.recovery_cases.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(404, "Case not found")
    timeline = await db.recovery_timeline.find({"case_id": case_id}, {"_id": 0}).sort("at", -1).to_list(500)
    borrower = await db.borrowers.find_one({"id": case["borrower_id"]}, {"_id": 0})
    return {"case": case, "timeline": timeline, "borrower": borrower}


@api.patch("/recovery/{case_id}")
async def update_recovery_case(case_id: str, payload: RecoveryCaseUpdate, user: dict = Depends(require_role("admin", "analyst", "rm"))):
    existing = await db.recovery_cases.find_one({"id": case_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Case not found")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    timeline_events = []

    if "status" in updates and updates["status"] != existing.get("status"):
        timeline_events.append({"type": "status_change", "content": f"Status: {existing.get('status','').upper()} → {updates['status'].upper()}"})
        if updates["status"] == "resolved":
            updates["resolved_at"] = now_iso()

    if "assigned_to" in updates and updates["assigned_to"] != existing.get("assigned_to"):
        u = await db.users.find_one({"id": updates["assigned_to"]}, {"_id": 0}) if updates["assigned_to"] else None
        updates["assigned_to_name"] = u.get("name", "") if u else ""
        timeline_events.append({"type": "system", "content": f"Assigned to {updates['assigned_to_name'] or 'unassigned'}"})

    if "next_action" in updates and updates["next_action"] != existing.get("next_action"):
        timeline_events.append({"type": "action_update", "content": f"Next action: {updates['next_action']}"})

    if "deadline" in updates and updates["deadline"] != existing.get("deadline"):
        timeline_events.append({"type": "system", "content": f"Deadline set: {updates['deadline']}"})

    updates["updated_at"] = now_iso()
    await db.recovery_cases.update_one({"id": case_id}, {"$set": updates})

    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    for ev in timeline_events:
        await db.recovery_timeline.insert_one({
            "id": gen_id(), "case_id": case_id, **ev,
            "by_user_id": user["id"], "by_user_name": u.get("name", "") if u else "",
            "at": now_iso(),
        })

    await log_audit(user, "update", "recovery", case_id, existing.get("borrower_name", ""), f"Updated: {', '.join(k for k in updates.keys() if k != 'updated_at')}")
    case = await db.recovery_cases.find_one({"id": case_id}, {"_id": 0})
    return case


@api.post("/recovery/{case_id}/timeline")
async def add_timeline_event(case_id: str, payload: RecoveryTimelineEvent, user: dict = Depends(require_role("admin", "analyst", "rm"))):
    case = await db.recovery_cases.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(404, "Case not found")
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    event = {
        "id": gen_id(), "case_id": case_id,
        "type": payload.type, "content": payload.content,
        "by_user_id": user["id"], "by_user_name": u.get("name", "") if u else "",
        "at": now_iso(),
    }
    await db.recovery_timeline.insert_one(event.copy())
    await db.recovery_cases.update_one({"id": case_id}, {"$set": {"updated_at": now_iso()}})
    return event


# ---------------- AUDIT LOG VIEW ----------------
@api.get("/audit")
async def list_audit_logs(
    limit: int = 200,
    resource: Optional[str] = None,
    user: dict = Depends(require_role("admin")),
):
    q = {}
    if resource:
        q["resource"] = resource
    logs = await db.audit_logs.find(q, {"_id": 0}).sort("at", -1).limit(limit).to_list(limit)
    return logs


# ---------------- FINANCIALS (Balance Sheet / P&L / Ratios) ----------------
@api.get("/borrowers/{borrower_id}/financials")
async def get_financials(borrower_id: str, user: dict = Depends(get_current_user)):
    bs_list = await db.balance_sheets.find({"borrower_id": borrower_id}, {"_id": 0}).sort("period", 1).to_list(50)
    pnl_list = await db.pnl_statements.find({"borrower_id": borrower_id}, {"_id": 0}).sort("period", 1).to_list(50)
    ratios = {}
    if bs_list and pnl_list:
        ratios = compute_ratios(bs_list[-1], pnl_list[-1])
    return {"balance_sheets": bs_list, "pnl": pnl_list, "ratios": ratios,
            "latest_period": (bs_list[-1]["period"] if bs_list else None)}


# ---------------- TEMPLATES (downloadable CSVs) ----------------
@api.get("/templates/{template_type}")
async def download_template(template_type: str, user: dict = Depends(get_current_user)):
    csv_content = TEMPLATES.get(template_type)
    if not csv_content:
        raise HTTPException(404, f"Template '{template_type}' not found. Available: {', '.join(TEMPLATES.keys())}")
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{template_type}_template.csv"'},
    )


# ---------------- RECOVERY AI COPILOT ----------------
class RecoveryChatIn(BaseModel):
    message: str

@api.post("/recovery/{case_id}/copilot")
async def recovery_copilot(case_id: str, payload: RecoveryChatIn, user: dict = Depends(get_current_user)):
    case = await db.recovery_cases.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(404, "Case not found")
    borrower = await db.borrowers.find_one({"id": case["borrower_id"]}, {"_id": 0})
    if not borrower:
        raise HTTPException(404, "Borrower not found")

    sales = await db.sales_data.find({"borrower_id": case["borrower_id"]}, {"_id": 0}).to_list(200)
    bank = await db.bank_balances.find({"borrower_id": case["borrower_id"]}, {"_id": 0}).to_list(200)
    reps = await db.repayments.find({"borrower_id": case["borrower_id"]}, {"_id": 0}).to_list(200)
    pnl = await db.pnl_statements.find({"borrower_id": case["borrower_id"]}, {"_id": 0}).to_list(20)
    bs = await db.balance_sheets.find_one({"borrower_id": case["borrower_id"]}, {"_id": 0}, sort=[("period", -1)])
    latest_pnl = await db.pnl_statements.find_one({"borrower_id": case["borrower_id"]}, {"_id": 0}, sort=[("period", -1)])
    timeline = await db.recovery_timeline.find({"case_id": case_id}, {"_id": 0}).sort("at", -1).to_list(50)

    ratios = compute_ratios(bs, latest_pnl) if (bs and latest_pnl) else {}
    financials = {"sales": sales, "bank": bank, "repayments": reps, "pnl": pnl}

    ctx = build_recovery_context(case, borrower, financials, timeline, ratios)
    session_id = f"recovery-{case_id}-{user['id']}"

    # Save user message
    user_msg = {
        "id": gen_id(), "case_id": case_id, "role": "user",
        "content": payload.message, "by_user_id": user["id"],
        "created_at": now_iso(),
    }
    await db.recovery_chat.insert_one(user_msg.copy())

    response_text = await recovery_ai(ctx, session_id, payload.message)
    bot_msg = {
        "id": gen_id(), "case_id": case_id, "role": "assistant",
        "content": response_text, "by_user_id": "ai",
        "created_at": now_iso(),
    }
    await db.recovery_chat.insert_one(bot_msg.copy())
    return {"response": response_text}


@api.get("/recovery/{case_id}/copilot")
async def recovery_copilot_history(case_id: str, user: dict = Depends(get_current_user)):
    msgs = await db.recovery_chat.find({"case_id": case_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
    return msgs


# ---------------- SEED FINANCIALS ----------------
@api.post("/seed-financials")
async def seed_financials(user: dict = Depends(get_current_user)):
    """Generate balance sheet + P&L data for any borrowers missing it. Idempotent."""
    from sample_data import BUSINESSES
    borrowers = await db.borrowers.find({}, {"_id": 0}).to_list(200)
    created = 0
    for idx, b in enumerate(borrowers):
        existing = await db.balance_sheets.count_documents({"borrower_id": b["id"]})
        if existing > 0:
            continue
        sales = await db.sales_data.find({"borrower_id": b["id"]}, {"_id": 0}).sort("month", 1).to_list(200)
        # Find business tuple by name; default to (name, sector) for added borrowers
        business = next((bx for bx in BUSINESSES if bx[0] == b["business_name"]), (b["business_name"], b.get("sector", "Services")))
        bs_list, pnl_list = generate_bs_pnl(seed=hash(b["id"]) % 10000, business=business,
                                            loan_amount=b.get("loan_amount", 1000000),
                                            outstanding=b.get("outstanding_amount", 500000),
                                            sales_data=sales)
        for bs in bs_list:
            await db.balance_sheets.insert_one({"id": gen_id(), "borrower_id": b["id"], **bs, "created_at": now_iso()})
        for pl in pnl_list:
            await db.pnl_statements.insert_one({"id": gen_id(), "borrower_id": b["id"], **pl, "created_at": now_iso()})
        await _recompute_and_persist(b["id"])
        created += 1
    return {"seeded": created, "total_borrowers": len(borrowers)}


# ---------------- META ----------------
@api.get("/meta/sectors")
async def list_sectors(user: dict = Depends(get_current_user)):
    return ["Textile", "Manufacturing", "Trading", "Retail", "Services",
            "Restaurant", "Construction", "Agriculture", "Transport", "IT Services",
            "Healthcare", "Education"]


# Register
app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
