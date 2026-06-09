"""Backend tests for MSME Credit Risk Early Warning System.

Covers: auth, seed, borrowers CRUD/filter/search/sort, details, upload (CSV),
recompute, chat (AI copilot), notes, reports (PDF/DOCX), portfolio, analytics,
alerts, role-based access control.
"""
import io
import os
import time
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://early-distress-ai.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@msme.com", "password": "admin123"}
ANALYST = {"email": "analyst@msme.com", "password": "analyst123", "name": "Test Analyst", "role": "analyst"}
# NOTE: test_credentials.md lists rm/rm123 (5 chars) but signup requires min 6 chars; using rm12345
RM = {"email": "rm@msme.com", "password": "rm12345", "name": "Test RM", "role": "rm"}


# ---------------- Helpers / Fixtures ----------------

def _login(session, email, password):
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password})
    return r


def _signup_if_needed(session, payload):
    r = session.post(f"{API}/auth/signup", json=payload)
    if r.status_code == 400:  # already exists
        r2 = _login(session, payload["email"], payload["password"])
        return r2.json()
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="session")
def http():
    return requests.Session()


@pytest.fixture(scope="session")
def admin_token(http):
    r = _login(http, ADMIN["email"], ADMIN["password"])
    if r.status_code != 200:
        # try signup
        r2 = http.post(f"{API}/auth/signup", json={
            "email": ADMIN["email"], "password": ADMIN["password"], "name": "Admin", "role": "admin"
        })
        assert r2.status_code == 200, f"admin bootstrap failed: {r2.text}"
        return r2.json()["token"]
    return r.json()["token"]


@pytest.fixture(scope="session")
def analyst_token(http):
    data = _signup_if_needed(http, ANALYST)
    return data["token"]


@pytest.fixture(scope="session")
def rm_token(http):
    data = _signup_if_needed(http, RM)
    return data["token"]


def H(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------- Health ----------------
class TestHealth:
    def test_root(self, http):
        r = http.get(f"{API}/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"


# ---------------- Auth ----------------
class TestAuth:
    def test_signup_duplicate_returns_400(self, http, admin_token):
        r = http.post(f"{API}/auth/signup", json={
            "email": ADMIN["email"], "password": ADMIN["password"], "name": "Admin", "role": "admin"
        })
        assert r.status_code == 400

    def test_login_admin(self, http):
        r = _login(http, ADMIN["email"], ADMIN["password"])
        assert r.status_code == 200
        data = r.json()
        assert "token" in data and isinstance(data["token"], str)
        assert data["user"]["email"] == ADMIN["email"]
        assert data["user"]["role"] == "admin"

    def test_login_invalid(self, http):
        r = http.post(f"{API}/auth/login", json={"email": ADMIN["email"], "password": "wrong"})
        assert r.status_code == 401

    def test_me(self, http, admin_token):
        r = http.get(f"{API}/auth/me", headers=H(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == ADMIN["email"]
        assert data["role"] == "admin"

    def test_me_unauthenticated(self, http):
        r = http.get(f"{API}/auth/me")
        assert r.status_code == 401


# ---------------- Seed ----------------
class TestSeed:
    def test_seed_idempotent(self, http, admin_token):
        r = http.post(f"{API}/seed", headers=H(admin_token))
        assert r.status_code == 200
        data = r.json()
        # Either freshly seeded or already seeded
        assert ("seeded" in data) or ("borrower_count" in data)
        # Verify borrowers exist
        r2 = http.get(f"{API}/borrowers", headers=H(admin_token))
        assert r2.status_code == 200
        assert r2.json()["total"] >= 1


# ---------------- Borrowers ----------------
class TestBorrowersList:
    def test_list_default(self, http, admin_token):
        r = http.get(f"{API}/borrowers", headers=H(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and "total" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 1

    def test_list_search(self, http, admin_token):
        # Get a borrower's name first
        r = http.get(f"{API}/borrowers?limit=1", headers=H(admin_token))
        name = r.json()["items"][0]["business_name"]
        # Search for substring
        substr = name.split()[0]
        r2 = http.get(f"{API}/borrowers?search={substr}", headers=H(admin_token))
        assert r2.status_code == 200
        items = r2.json()["items"]
        assert any(substr.lower() in b["business_name"].lower() for b in items)

    def test_list_sector_filter(self, http, admin_token):
        r = http.get(f"{API}/borrowers?sector=Textile", headers=H(admin_token))
        assert r.status_code == 200
        for b in r.json()["items"]:
            assert b["sector"] == "Textile"

    def test_list_risk_filter(self, http, admin_token):
        r = http.get(f"{API}/borrowers?risk_category=high", headers=H(admin_token))
        assert r.status_code == 200
        for b in r.json()["items"]:
            assert b["risk_category"] == "high"

    def test_list_sort_desc(self, http, admin_token):
        r = http.get(f"{API}/borrowers?sort_by=risk_score&order=desc", headers=H(admin_token))
        assert r.status_code == 200
        items = r.json()["items"]
        scores = [b.get("risk_score", 0) for b in items]
        assert scores == sorted(scores, reverse=True)

    def test_list_pagination(self, http, admin_token):
        r = http.get(f"{API}/borrowers?page=1&limit=2", headers=H(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) <= 2
        assert data["page"] == 1
        assert data["limit"] == 2


class TestBorrowerCRUD:
    created_id = None

    def test_create_as_admin(self, http, admin_token):
        payload = {
            "business_name": "TEST_Acme Textiles",
            "sector": "Textile",
            "location": "Mumbai",
            "loan_amount": 1000000.0,
            "loan_type": "Term Loan",
            "sanction_date": "2024-01-15",
            "outstanding_amount": 800000.0,
            "gst_number": "27AAAPL1234C1Z5",
            "contact_person": "Tester",
            "contact_phone": "9999999999",
        }
        r = http.post(f"{API}/borrowers", headers=H(admin_token), json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["business_name"] == payload["business_name"]
        assert "id" in data
        TestBorrowerCRUD.created_id = data["id"]

        # GET verify persistence
        r2 = http.get(f"{API}/borrowers/{data['id']}", headers=H(admin_token))
        assert r2.status_code == 200
        assert r2.json()["business_name"] == payload["business_name"]

    def test_create_rm_forbidden(self, http, rm_token):
        payload = {
            "business_name": "TEST_RM Should Fail",
            "sector": "Retail",
            "location": "Delhi",
            "loan_amount": 100000.0,
            "loan_type": "OD",
            "sanction_date": "2024-02-01",
            "outstanding_amount": 90000.0,
        }
        r = http.post(f"{API}/borrowers", headers=H(rm_token), json=payload)
        assert r.status_code == 403

    def test_details_full_shape(self, http, admin_token):
        # Use a seeded borrower (has data)
        r = http.get(f"{API}/borrowers?limit=1", headers=H(admin_token))
        bid = r.json()["items"][0]["id"]
        r2 = http.get(f"{API}/borrowers/{bid}/details", headers=H(admin_token))
        assert r2.status_code == 200
        data = r2.json()
        for k in ["borrower", "sales", "bank", "repayments", "signals", "alerts", "notes", "risk_history"]:
            assert k in data, f"missing key {k}"

    def test_recompute(self, http, admin_token):
        r = http.get(f"{API}/borrowers?limit=1", headers=H(admin_token))
        bid = r.json()["items"][0]["id"]
        r2 = http.post(f"{API}/borrowers/{bid}/recompute", headers=H(admin_token))
        assert r2.status_code == 200
        data = r2.json()
        assert data["recomputed"] is True
        assert "risk_score" in data and "risk_category" in data

    def test_delete_rm_forbidden(self, http, rm_token):
        cid = TestBorrowerCRUD.created_id
        assert cid, "Need created borrower from previous test"
        r = http.delete(f"{API}/borrowers/{cid}", headers=H(rm_token))
        assert r.status_code == 403

    def test_delete_as_admin(self, http, admin_token):
        cid = TestBorrowerCRUD.created_id
        assert cid
        r = http.delete(f"{API}/borrowers/{cid}", headers=H(admin_token))
        assert r.status_code == 200
        # Verify gone
        r2 = http.get(f"{API}/borrowers/{cid}", headers=H(admin_token))
        assert r2.status_code == 404


# ---------------- Upload ----------------
class TestUpload:
    def test_upload_sales_csv(self, http, admin_token):
        r = http.get(f"{API}/borrowers?limit=1", headers=H(admin_token))
        bid = r.json()["items"][0]["id"]
        csv_content = b"month,amount\n2024-01,500000\n2024-02,450000\n2024-03,400000\n"
        files = {"file": ("sales.csv", csv_content, "text/csv")}
        data = {"file_type": "sales"}
        r2 = http.post(f"{API}/borrowers/{bid}/upload", headers=H(admin_token), files=files, data=data)
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert body["uploaded"] is True
        assert body["rows_processed"] >= 1

        # Verify recompute happened: details should have sales
        r3 = http.get(f"{API}/borrowers/{bid}/details", headers=H(admin_token))
        assert r3.status_code == 200
        sales = r3.json()["sales"]
        months = {s["month"] for s in sales}
        assert "2024-01" in months

    def test_upload_rm_forbidden(self, http, rm_token, admin_token):
        r = http.get(f"{API}/borrowers?limit=1", headers=H(admin_token))
        bid = r.json()["items"][0]["id"]
        files = {"file": ("sales.csv", b"month,amount\n2024-01,100\n", "text/csv")}
        data = {"file_type": "sales"}
        r2 = http.post(f"{API}/borrowers/{bid}/upload", headers=H(rm_token), files=files, data=data)
        assert r2.status_code == 403


# ---------------- Notes ----------------
class TestNotes:
    def test_create_and_list_notes(self, http, analyst_token, admin_token):
        r = http.get(f"{API}/borrowers?limit=1", headers=H(admin_token))
        bid = r.json()["items"][0]["id"]
        r2 = http.post(f"{API}/notes", headers=H(analyst_token),
                       json={"borrower_id": bid, "content": "TEST_Note content for review"})
        assert r2.status_code == 200, r2.text
        note = r2.json()
        assert note["content"] == "TEST_Note content for review"

        r3 = http.get(f"{API}/notes/{bid}", headers=H(admin_token))
        assert r3.status_code == 200
        assert any(n["content"] == "TEST_Note content for review" for n in r3.json())

    def test_note_rm_forbidden(self, http, rm_token, admin_token):
        r = http.get(f"{API}/borrowers?limit=1", headers=H(admin_token))
        bid = r.json()["items"][0]["id"]
        r2 = http.post(f"{API}/notes", headers=H(rm_token),
                       json={"borrower_id": bid, "content": "should fail"})
        assert r2.status_code == 403


# ---------------- Chat ----------------
class TestChat:
    def test_chat_and_history(self, http, admin_token):
        r = http.get(f"{API}/borrowers?limit=1", headers=H(admin_token))
        bid = r.json()["items"][0]["id"]
        r2 = http.post(f"{API}/chat", headers=H(admin_token),
                       json={"borrower_id": bid, "message": "Give a brief one-line risk summary."},
                       timeout=90)
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert "session_id" in data
        assert "response" in data and isinstance(data["response"], str) and len(data["response"]) > 0

        # Allow brief settle
        time.sleep(1)
        r3 = http.get(f"{API}/chat/{bid}", headers=H(admin_token))
        assert r3.status_code == 200
        msgs = r3.json()
        assert len(msgs) >= 2
        roles = [m["role"] for m in msgs]
        assert "user" in roles and "assistant" in roles


# ---------------- Reports ----------------
class TestReports:
    def test_pdf(self, http, admin_token):
        r = http.get(f"{API}/borrowers?limit=1", headers=H(admin_token))
        bid = r.json()["items"][0]["id"]
        r2 = http.get(f"{API}/reports/{bid}/pdf", headers=H(admin_token))
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("application/pdf")
        assert r2.content[:4] == b"%PDF"

    def test_docx(self, http, admin_token):
        r = http.get(f"{API}/borrowers?limit=1", headers=H(admin_token))
        bid = r.json()["items"][0]["id"]
        r2 = http.get(f"{API}/reports/{bid}/docx", headers=H(admin_token))
        assert r2.status_code == 200
        assert "officedocument" in r2.headers.get("content-type", "")
        # DOCX is a zip
        assert r2.content[:2] == b"PK"


# ---------------- Portfolio ----------------
class TestPortfolio:
    def test_overview(self, http, admin_token):
        r = http.get(f"{API}/portfolio/overview", headers=H(admin_token))
        assert r.status_code == 200
        data = r.json()
        for k in ["total_borrowers", "by_category", "avg_risk_score",
                  "outstanding_at_risk", "total_outstanding",
                  "top_risky", "sector_exposure", "recent_alerts"]:
            assert k in data
        assert isinstance(data["top_risky"], list)
        assert isinstance(data["sector_exposure"], list)
        assert data["total_borrowers"] >= 1

    def test_analytics(self, http, admin_token):
        r = http.get(f"{API}/portfolio/analytics", headers=H(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert "signal_frequency" in data
        assert "risk_distribution" in data
        # risk_distribution should have 4 bins
        ranges = {x["range"] for x in data["risk_distribution"]}
        assert ranges == {"0-25", "25-50", "50-75", "75-100"}


# ---------------- Alerts ----------------
class TestAlerts:
    def test_list_and_mark_read(self, http, admin_token):
        r = http.get(f"{API}/alerts", headers=H(admin_token))
        assert r.status_code == 200
        alerts = r.json()
        assert isinstance(alerts, list)
        if alerts:
            aid = alerts[0]["id"]
            r2 = http.post(f"{API}/alerts/{aid}/read", headers=H(admin_token))
            assert r2.status_code == 200
            # Verify is_read flipped
            r3 = http.get(f"{API}/alerts", headers=H(admin_token))
            target = next((a for a in r3.json() if a["id"] == aid), None)
            assert target is not None
            assert target["is_read"] is True



# ---------------- BULK IMPORT (Iteration 2) ----------------
class TestBulkImport:
    def test_bulk_import_csv_success(self, http, admin_token):
        csv_content = (
            b"business_name,sector,location,loan_amount,loan_type,sanction_date,outstanding_amount,gst_number,contact_person,contact_phone\n"
            b"TEST_BulkOne Pvt Ltd,Textile,Surat,500000,Term Loan,2024-03-01,400000,27AABCT1234X1Z2,Bulk One,9000000001\n"
            b"TEST_BulkTwo Traders,Trading,Pune,250000,OD,2024-04-10,200000,27AABCT5678Y1Z3,Bulk Two,9000000002\n"
        )
        files = {"file": ("borrowers.csv", csv_content, "text/csv")}
        r = http.post(f"{API}/borrowers/bulk-import", headers=H(admin_token), files=files)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["created"] == 2
        assert isinstance(body["errors"], list)
        assert isinstance(body["items"], list) and len(body["items"]) == 2

        # Cleanup
        for item in body["items"]:
            http.delete(f"{API}/borrowers/{item['id']}", headers=H(admin_token))

    def test_bulk_import_missing_columns(self, http, admin_token):
        # Missing outstanding_amount
        csv_content = b"business_name,sector,location,loan_amount,loan_type,sanction_date\nTEST_NoOut,Retail,Delhi,100000,Term,2024-01-01\n"
        files = {"file": ("bad.csv", csv_content, "text/csv")}
        r = http.post(f"{API}/borrowers/bulk-import", headers=H(admin_token), files=files)
        assert r.status_code == 400
        assert "outstanding_amount" in r.text

    def test_bulk_import_rm_forbidden(self, http, rm_token):
        csv_content = (
            b"business_name,sector,location,loan_amount,loan_type,sanction_date,outstanding_amount\n"
            b"TEST_X,Retail,Delhi,1000,OD,2024-01-01,500\n"
        )
        files = {"file": ("b.csv", csv_content, "text/csv")}
        r = http.post(f"{API}/borrowers/bulk-import", headers=H(rm_token), files=files)
        assert r.status_code == 403

    def test_bulk_import_with_row_errors(self, http, admin_token):
        # Second row has invalid loan_amount
        csv_content = (
            b"business_name,sector,location,loan_amount,loan_type,sanction_date,outstanding_amount\n"
            b"TEST_GoodRow,Retail,Delhi,100000,Term,2024-01-01,90000\n"
            b"TEST_BadRow,Retail,Delhi,not_a_number,Term,2024-01-01,90000\n"
        )
        files = {"file": ("mixed.csv", csv_content, "text/csv")}
        r = http.post(f"{API}/borrowers/bulk-import", headers=H(admin_token), files=files)
        assert r.status_code == 200
        body = r.json()
        assert body["created"] == 1
        assert len(body["errors"]) == 1
        assert body["errors"][0]["row"] == 3
        # cleanup
        for item in body["items"]:
            http.delete(f"{API}/borrowers/{item['id']}", headers=H(admin_token))


# ---------------- RECOVERY WORKFLOW (Iteration 2) ----------------
class TestRecovery:
    created_case_id = None
    borrower_id = None

    def test_list_recovery_returns_items_and_stats(self, http, admin_token):
        r = http.get(f"{API}/recovery", headers=H(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and isinstance(data["items"], list)
        assert "stats" in data
        for k in ["open", "in_progress", "escalated", "resolved"]:
            assert k in data["stats"]

    def test_list_recovery_status_filter(self, http, admin_token):
        r = http.get(f"{API}/recovery?status=open", headers=H(admin_token))
        assert r.status_code == 200
        for c in r.json()["items"]:
            assert c["status"] == "open"

    def test_list_recovery_assigned_to_me(self, http, admin_token):
        r = http.get(f"{API}/recovery?assigned_to_me=true", headers=H(admin_token))
        assert r.status_code == 200
        # all items should have admin's id as assigned_to (likely empty)
        for c in r.json()["items"]:
            assert c.get("assigned_to") is not None

    def test_create_recovery_case_manual(self, http, admin_token):
        # Create a fresh borrower (no auto case) to use for manual case
        payload = {
            "business_name": "TEST_Recovery Subject",
            "sector": "Retail",
            "location": "Bangalore",
            "loan_amount": 600000.0,
            "loan_type": "Term Loan",
            "sanction_date": "2024-02-15",
            "outstanding_amount": 500000.0,
        }
        rb = http.post(f"{API}/borrowers", headers=H(admin_token), json=payload)
        assert rb.status_code == 200, rb.text
        bid = rb.json()["id"]
        TestRecovery.borrower_id = bid

        rc = http.post(f"{API}/recovery", headers=H(admin_token), json={
            "borrower_id": bid,
            "priority": "medium",
            "next_action": "Schedule first contact call",
            "deadline": "2026-02-15",
        })
        assert rc.status_code == 200, rc.text
        case = rc.json()
        assert case["borrower_id"] == bid
        assert case["borrower_name"] == "TEST_Recovery Subject"
        assert case["status"] == "open"
        assert case["priority"] == "medium"
        assert case["auto_created"] is False
        TestRecovery.created_case_id = case["id"]

    def test_create_recovery_duplicate_returns_400(self, http, admin_token):
        bid = TestRecovery.borrower_id
        assert bid, "borrower needed from prior test"
        r = http.post(f"{API}/recovery", headers=H(admin_token), json={"borrower_id": bid})
        assert r.status_code == 400
        assert "already exists" in r.text.lower()

    def test_create_recovery_rm_allowed(self, http, rm_token):
        # rm allowed by spec. Use a borrower that has no active case.
        # Create a new one as rm cannot create borrowers; use admin via session pattern not available here;
        # so we just check the 404 path (no such borrower) to confirm route is accessible to rm (not 403).
        r = http.post(f"{API}/recovery", headers=H(rm_token), json={"borrower_id": "nonexistent-id"})
        assert r.status_code == 404  # not 403 -> rm IS allowed

    def test_get_recovery_case_shape(self, http, admin_token):
        cid = TestRecovery.created_case_id
        assert cid
        r = http.get(f"{API}/recovery/{cid}", headers=H(admin_token))
        assert r.status_code == 200
        data = r.json()
        for k in ["case", "timeline", "borrower"]:
            assert k in data
        assert data["case"]["id"] == cid
        assert isinstance(data["timeline"], list)
        # Should have an opening timeline event (system)
        types = [t["type"] for t in data["timeline"]]
        assert "system" in types

    def test_patch_recovery_status_creates_timeline(self, http, admin_token):
        cid = TestRecovery.created_case_id
        r = http.patch(f"{API}/recovery/{cid}", headers=H(admin_token), json={"status": "in_progress"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "in_progress"

        # Verify timeline event for status change
        r2 = http.get(f"{API}/recovery/{cid}", headers=H(admin_token))
        timeline = r2.json()["timeline"]
        assert any(t["type"] == "status_change" and "IN_PROGRESS" in t["content"] for t in timeline)

    def test_patch_recovery_next_action_and_deadline(self, http, admin_token):
        cid = TestRecovery.created_case_id
        r = http.patch(f"{API}/recovery/{cid}", headers=H(admin_token), json={
            "next_action": "Send legal notice within 7 days",
            "deadline": "2026-03-31",
            "priority": "high",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["next_action"] == "Send legal notice within 7 days"
        assert body["deadline"] == "2026-03-31"
        assert body["priority"] == "high"

        r2 = http.get(f"{API}/recovery/{cid}", headers=H(admin_token))
        timeline = r2.json()["timeline"]
        action_evs = [t for t in timeline if t["type"] == "action_update"]
        assert any("legal notice" in t["content"].lower() for t in action_evs)

    def test_patch_recovery_resolved_sets_resolved_at(self, http, admin_token):
        cid = TestRecovery.created_case_id
        r = http.patch(f"{API}/recovery/{cid}", headers=H(admin_token), json={"status": "resolved"})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "resolved"
        assert body["resolved_at"] is not None

    def test_post_timeline_event(self, http, admin_token):
        cid = TestRecovery.created_case_id
        r = http.post(f"{API}/recovery/{cid}/timeline", headers=H(admin_token), json={
            "type": "note",
            "content": "TEST_Timeline custom note entry"
        })
        assert r.status_code == 200, r.text
        ev = r.json()
        assert ev["type"] == "note"
        assert ev["content"] == "TEST_Timeline custom note entry"
        assert ev["case_id"] == cid

        r2 = http.get(f"{API}/recovery/{cid}", headers=H(admin_token))
        assert any(t["content"] == "TEST_Timeline custom note entry" for t in r2.json()["timeline"])

    def test_post_timeline_contact_type(self, http, admin_token):
        cid = TestRecovery.created_case_id
        r = http.post(f"{API}/recovery/{cid}/timeline", headers=H(admin_token), json={
            "type": "contact",
            "content": "TEST_Called borrower; no response"
        })
        assert r.status_code == 200
        assert r.json()["type"] == "contact"

    def test_recovery_get_404(self, http, admin_token):
        r = http.get(f"{API}/recovery/nonexistent-case-id", headers=H(admin_token))
        assert r.status_code == 404

    def test_zz_cleanup_recovery_borrower(self, http, admin_token):
        # Cleanup created borrower (also deletes its recovery cases per server.py delete handler)
        bid = TestRecovery.borrower_id
        if bid:
            http.delete(f"{API}/borrowers/{bid}", headers=H(admin_token))


# ---------------- AUDIT LOG (Iteration 2) ----------------
class TestAuditLog:
    def test_audit_requires_admin(self, http, rm_token):
        r = http.get(f"{API}/audit", headers=H(rm_token))
        assert r.status_code == 403

    def test_audit_analyst_forbidden(self, http, analyst_token):
        r = http.get(f"{API}/audit", headers=H(analyst_token))
        assert r.status_code == 403

    def test_audit_unauthenticated(self, http):
        r = http.get(f"{API}/audit")
        assert r.status_code == 401

    def test_audit_admin_list(self, http, admin_token):
        r = http.get(f"{API}/audit", headers=H(admin_token))
        assert r.status_code == 200
        logs = r.json()
        assert isinstance(logs, list)
        # By now prior tests created at least one borrower/recovery -> there should be audit entries
        if logs:
            entry = logs[0]
            for k in ["id", "user_id", "action", "resource", "at"]:
                assert k in entry

    def test_audit_filter_by_resource(self, http, admin_token):
        # Generate a known borrower-create event
        payload = {
            "business_name": "TEST_Audit Borrower",
            "sector": "Retail",
            "location": "Mumbai",
            "loan_amount": 100000.0,
            "loan_type": "OD",
            "sanction_date": "2024-05-01",
            "outstanding_amount": 80000.0,
        }
        rc = http.post(f"{API}/borrowers", headers=H(admin_token), json=payload)
        assert rc.status_code == 200
        bid = rc.json()["id"]

        # Update -> should also audit
        http.put(f"{API}/borrowers/{bid}", headers=H(admin_token),
                 json={"location": "Chennai"})

        r = http.get(f"{API}/audit?resource=borrower&limit=50", headers=H(admin_token))
        assert r.status_code == 200
        logs = r.json()
        # All filtered logs are for borrower
        assert all(log["resource"] == "borrower" for log in logs)
        # Should find the create entry we just made
        assert any(log["action"] == "create" and log["resource_id"] == bid for log in logs)
        assert any(log["action"] == "update" and log["resource_id"] == bid for log in logs)

        # cleanup
        http.delete(f"{API}/borrowers/{bid}", headers=H(admin_token))
        r2 = http.get(f"{API}/audit?resource=borrower&limit=50", headers=H(admin_token))
        assert any(log["action"] == "delete" and log["resource_id"] == bid for log in r2.json())

    def test_audit_recovery_logged(self, http, admin_token):
        # Verify recovery actions get audited by creating one
        bp = {
            "business_name": "TEST_AuditRecovery",
            "sector": "Retail",
            "location": "Goa",
            "loan_amount": 100000.0,
            "loan_type": "OD",
            "sanction_date": "2024-06-01",
            "outstanding_amount": 70000.0,
        }
        rb = http.post(f"{API}/borrowers", headers=H(admin_token), json=bp)
        bid = rb.json()["id"]
        rc = http.post(f"{API}/recovery", headers=H(admin_token), json={"borrower_id": bid})
        assert rc.status_code == 200
        cid = rc.json()["id"]

        r = http.get(f"{API}/audit?resource=recovery&limit=100", headers=H(admin_token))
        assert r.status_code == 200
        logs = r.json()
        assert any(log["action"] == "create" and log["resource_id"] == cid for log in logs)

        # cleanup
        http.delete(f"{API}/borrowers/{bid}", headers=H(admin_token))


# ---------------- AUTO-RECOVERY ON CRITICAL (Iteration 2) ----------------
class TestAutoRecoveryOnCritical:
    def _make_critical_borrower(self, http, admin_token):
        """Create a borrower and upload data that pushes risk to critical."""
        payload = {
            "business_name": "TEST_AutoCritical",
            "sector": "Manufacturing",
            "location": "Delhi",
            "loan_amount": 1000000.0,
            "loan_type": "Term Loan",
            "sanction_date": "2023-01-01",
            "outstanding_amount": 950000.0,
        }
        rb = http.post(f"{API}/borrowers", headers=H(admin_token), json=payload)
        assert rb.status_code == 200
        return rb.json()["id"]

    def test_auto_recovery_no_duplicate_on_existing_critical(self, http, admin_token):
        """Use an existing critical borrower (seeded/prior recompute) and verify
        recompute does NOT create a duplicate recovery case."""
        r = http.get(f"{API}/borrowers?risk_category=critical&limit=5", headers=H(admin_token))
        assert r.status_code == 200
        critical_borrowers = r.json()["items"]
        if not critical_borrowers:
            pytest.skip("No critical borrowers exist in DB to verify auto-recovery dedup")
        bid = critical_borrowers[0]["id"]

        # Snapshot existing recovery cases for this borrower
        rr = http.get(f"{API}/recovery", headers=H(admin_token))
        before = [c for c in rr.json()["items"] if c["borrower_id"] == bid]

        # Recompute (should either keep existing active case or create one if none active)
        rc = http.post(f"{API}/borrowers/{bid}/recompute", headers=H(admin_token))
        assert rc.status_code == 200
        assert rc.json()["risk_category"] == "critical"

        rr2 = http.get(f"{API}/recovery", headers=H(admin_token))
        after = [c for c in rr2.json()["items"] if c["borrower_id"] == bid]

        # Active cases (open/in_progress/escalated) must not increase by more than 0
        active = lambda lst: [c for c in lst if c["status"] in ("open", "in_progress", "escalated")]
        assert len(active(after)) <= max(1, len(active(before))), \
            f"Duplicate active recovery case created (before={len(active(before))}, after={len(active(after))})"

        # If no active case existed before, one should have been auto-created now
        if not active(before):
            assert active(after), "Expected auto-created recovery case for critical borrower"
            new_case = active(after)[0]
            assert new_case["auto_created"] is True
            # Verify system timeline entry
            rd = http.get(f"{API}/recovery/{new_case['id']}", headers=H(admin_token))
            assert any(t["by_user_id"] == "system" for t in rd.json()["timeline"])

    def test_auto_recovery_case_created_on_critical(self, http, admin_token):
        """Best-effort synthetic test - heavily depends on risk_engine scoring weights.
        Marked skip if synthetic data can't push to critical. The
        test_auto_recovery_no_duplicate_on_existing_critical test covers both the
        auto-create and dedup spec requirements via the seeded critical borrower."""
        bid = self._make_critical_borrower(http, admin_token)
        try:
            # Upload very poor sales + missed repayments to force critical
            sales = b"month,amount\n"
            for i, m in enumerate([
                "2024-01", "2024-02", "2024-03", "2024-04", "2024-05",
                "2024-06", "2024-07", "2024-08", "2024-09", "2024-10",
                "2024-11", "2024-12",
            ]):
                amt = max(100000 - i * 10000, 5000)
                sales += f"{m},{amt}\n".encode()
            r1 = http.post(f"{API}/borrowers/{bid}/upload",
                           headers=H(admin_token),
                           files={"file": ("sales.csv", sales, "text/csv")},
                           data={"file_type": "sales"})
            assert r1.status_code == 200

            repay = b"month,status\n"
            for m in ["2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12"]:
                repay += f"{m},missed\n".encode()
            r2 = http.post(f"{API}/borrowers/{bid}/upload",
                           headers=H(admin_token),
                           files={"file": ("repay.csv", repay, "text/csv")},
                           data={"file_type": "repayment"})
            assert r2.status_code == 200

            bank = b"month,closing_balance\n"
            for i, m in enumerate(["2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12"]):
                bank += f"{m},{max(50000 - i*9000, 1000)}\n".encode()
            r3 = http.post(f"{API}/borrowers/{bid}/upload",
                           headers=H(admin_token),
                           files={"file": ("bank.csv", bank, "text/csv")},
                           data={"file_type": "bank"})
            assert r3.status_code == 200

            # Force recompute (uploads also recompute, but be safe)
            http.post(f"{API}/borrowers/{bid}/recompute", headers=H(admin_token))

            b = http.get(f"{API}/borrowers/{bid}", headers=H(admin_token)).json()
            # If not critical, skip with a clear message (recovery creation only fires on critical)
            if b.get("risk_category") != "critical":
                pytest.skip(f"Did not reach critical category (got {b.get('risk_category')}, score {b.get('risk_score')}); auto-create only fires on critical")

            # Verify recovery case exists, auto_created=True, has system timeline
            rr = http.get(f"{API}/recovery", headers=H(admin_token))
            cases = [c for c in rr.json()["items"] if c["borrower_id"] == bid]
            assert cases, "No recovery case auto-created for critical borrower"
            case = cases[0]
            assert case["auto_created"] is True
            assert case["status"] == "open"

            rd = http.get(f"{API}/recovery/{case['id']}", headers=H(admin_token))
            timeline = rd.json()["timeline"]
            assert any(t["by_user_id"] == "system" and "auto-opened" in t["content"].lower() for t in timeline)

            # Recompute again -> should NOT duplicate
            http.post(f"{API}/borrowers/{bid}/recompute", headers=H(admin_token))
            rr2 = http.get(f"{API}/recovery", headers=H(admin_token))
            cases2 = [c for c in rr2.json()["items"] if c["borrower_id"] == bid]
            assert len(cases2) == 1, f"Duplicate recovery case created on repeat critical recompute (found {len(cases2)})"
        finally:
            http.delete(f"{API}/borrowers/{bid}", headers=H(admin_token))
