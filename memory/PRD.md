# MSME Credit Risk Early Warning System — PRD

## Original Problem Statement
Build a deployment-ready full-stack platform that helps banks, NBFCs, credit analysts, and lenders detect early distress signals in MSME borrowers before default.

## Tech Stack
- Backend: FastAPI + MongoDB (Motor)
- Frontend: React + Tailwind + shadcn/ui + Recharts + Phosphor Icons
- LLM: Claude Sonnet 4.6 via `emergentintegrations` (EMERGENT_LLM_KEY)
- Auth: JWT + bcrypt
- File parsing: pandas, openpyxl, pypdf
- Reports: reportlab (PDF), python-docx (DOCX)

## User Personas
- **Admin** — manages users, all borrowers, audit log, can delete
- **Credit Analyst** — adds/updates borrowers, uploads data, generates reports, AI copilot, manages recovery cases
- **Relationship Manager** — view-only borrowers, runs recovery cases assigned to them

## Implementation Timeline

### Phase 1 / MVP (2026-02)
- JWT auth, RBAC, borrower CRUD, file upload, risk engine, warning signals, AI Copilot, PDF/DOCX reports, portfolio dashboard, alerts. **29/29 tests passed.**

### Phase 2 / Workflow & Compliance (2026-02)
- Recovery Workflow (auto-opens on Critical), borrower edit dialog, bulk CSV import, in-app notification bell, audit log, mobile responsive. **54/55 tests passed.**

### Phase 3 / Financial Intelligence (2026-02)
- **Balance Sheet + P&L upload** (CSV/XLSX) — new file types in upload module
- **10 Financial Ratios** computed automatically: Current Ratio, Quick Ratio, Debt-to-Equity, Interest Coverage, DSCR, Gross/Net/EBITDA Margins, ROE, WC Turnover — each with health status (good/warning/bad), benchmark, value
- **Ratio-based risk factors** — DSCR<1.25, IC<1.5, CR<1, D/E>3, negative net margin auto-add to risk score
- **BS / P&L tab** on borrower detail with ratio cards + quarterly tables
- **Recovery AI Copilot** (Claude Sonnet 4.6) — strategy advisor inside each recovery case, knows the borrower's full financials + case timeline; gives specific restructure/settlement/collateral recommendations with rupee figures and tables
- **Downloadable CSV templates** for all 6 upload types (sales, bank, repayment, balance_sheet, pnl, borrowers_bulk)
- **Auto-seeded sample BS+PnL** (4 quarters per borrower) via `/api/seed-financials`
- **84/84 backend tests passed** (30 new + 54 regression).

## Backlog (P1)
- 404 on /financials when borrower missing (currently 200 with empty payload)
- Role-gate /seed-financials to admin/analyst
- Per-case rate limit on recovery copilot
- Split server.py into routers (now ~975 lines)

## Backlog (P2)
- Financial Trajectory Forecast (deferred per user decision — extrapolation, not ML)
- SLA tracking & overdue dashboards for recovery
- Multi-tenant separation
- Webhooks for downstream systems
- Email/Slack alert delivery

## Deployment
- Env: `/app/backend/.env` and `/app/frontend/.env`
- Supervisor-managed: backend (8001, /api prefix), frontend (3000)
- MongoDB collections: users, borrowers, sales_data, bank_balances, repayments, balance_sheets, pnl_statements, warning_signals, alerts, analyst_notes, chat_messages, recovery_cases, recovery_timeline, recovery_chat, audit_logs, risk_history, uploaded_files
- EMERGENT_LLM_KEY required for AI Copilot (fallback works without)
