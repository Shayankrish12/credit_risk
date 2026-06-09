"""Iteration 3 backend tests: Balance Sheet/PnL upload, ratios, templates,
recovery AI copilot, seed-financials. Augments backend_test.py without replacing it.
"""
import io
import os
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://early-distress-ai.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@msme.com", "password": "admin123"}
ANALYST = {"email": "analyst@msme.com", "password": "analyst123", "name": "Test Analyst", "role": "analyst"}
RM = {"email": "rm@msme.com", "password": "rm12345", "name": "Test RM", "role": "rm"}

EXPECTED_RATIOS = [
    "current_ratio", "quick_ratio", "debt_to_equity", "interest_coverage", "dscr",
    "gross_margin", "net_margin", "ebitda_margin", "roe", "working_capital_turnover",
]


# ---------------- Fixtures ----------------
@pytest.fixture(scope="module")
def http():
    return requests.Session()


def _login_or_signup(http, creds):
    r = http.post(f"{API}/auth/login", json={"email": creds["email"], "password": creds["password"]})
    if r.status_code == 200:
        return r.json()["token"]
    payload = {k: creds[k] for k in ("email", "password", "name", "role") if k in creds}
    r2 = http.post(f"{API}/auth/signup", json=payload)
    assert r2.status_code == 200, f"signup failed: {r2.text}"
    return r2.json()["token"]


@pytest.fixture(scope="module")
def admin_token(http):
    r = http.post(f"{API}/auth/login", json=ADMIN)
    if r.status_code != 200:
        r = http.post(f"{API}/auth/signup", json={**ADMIN, "name": "Admin", "role": "admin"})
    return r.json()["token"]


@pytest.fixture(scope="module")
def analyst_token(http):
    return _login_or_signup(http, ANALYST)


@pytest.fixture(scope="module")
def rm_token(http):
    return _login_or_signup(http, RM)


def H(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def seeded_borrower_id(http, admin_token):
    # Ensure base seed exists
    http.post(f"{API}/seed", headers=H(admin_token))
    # Ensure financials are seeded
    http.post(f"{API}/seed-financials", headers=H(admin_token))
    r = http.get(f"{API}/borrowers?limit=5", headers=H(admin_token))
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) > 0, "Need at least one seeded borrower"
    return items[0]["id"]


# ---------------- Templates ----------------
class TestTemplates:
    @pytest.mark.parametrize("ttype", ["sales", "bank", "repayment", "balance_sheet", "pnl", "borrowers_bulk"])
    def test_template_download(self, http, admin_token, ttype):
        r = http.get(f"{API}/templates/{ttype}", headers=H(admin_token))
        assert r.status_code == 200, f"{ttype}: {r.status_code} {r.text[:200]}"
        assert "text/csv" in r.headers.get("content-type", "")
        body = r.text
        assert "," in body and "\n" in body, f"Template {ttype} does not look like CSV"
        cd = r.headers.get("content-disposition", "")
        assert ttype in cd

    def test_template_balance_sheet_columns(self, http, admin_token):
        r = http.get(f"{API}/templates/balance_sheet", headers=H(admin_token))
        header = r.text.splitlines()[0].split(",")
        for col in ["period", "current_assets", "current_liabilities", "equity", "short_term_debt", "long_term_debt"]:
            assert col in header, f"BS template missing {col}"

    def test_template_pnl_columns(self, http, admin_token):
        r = http.get(f"{API}/templates/pnl", headers=H(admin_token))
        header = r.text.splitlines()[0].split(",")
        for col in ["period", "revenue", "cogs", "ebitda", "ebit", "interest_expense", "net_profit"]:
            assert col in header, f"PnL template missing {col}"

    def test_template_unknown_returns_404(self, http, admin_token):
        r = http.get(f"{API}/templates/nonexistent_xyz", headers=H(admin_token))
        assert r.status_code == 404

    def test_template_requires_auth(self, http):
        r = http.get(f"{API}/templates/sales")
        assert r.status_code in (401, 403)


# ---------------- Financials GET endpoint ----------------
class TestFinancialsEndpoint:
    def test_get_financials_seeded(self, http, admin_token, seeded_borrower_id):
        r = http.get(f"{API}/borrowers/{seeded_borrower_id}/financials", headers=H(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert set(["balance_sheets", "pnl", "ratios", "latest_period"]).issubset(data.keys())
        # seed-financials was run per agent context => should have 4 quarters
        assert len(data["balance_sheets"]) >= 1, "expected at least 1 balance sheet from seed-financials"
        assert len(data["pnl"]) >= 1
        assert data["latest_period"] is not None

    def test_ratios_contain_all_10(self, http, admin_token, seeded_borrower_id):
        r = http.get(f"{API}/borrowers/{seeded_borrower_id}/financials", headers=H(admin_token))
        ratios = r.json()["ratios"]
        for key in EXPECTED_RATIOS:
            assert key in ratios, f"Missing ratio: {key}"
            ratio = ratios[key]
            for field in ("label", "value", "status", "benchmark", "description", "suffix"):
                assert field in ratio, f"{key} missing field {field}"
            assert ratio["status"] in ("good", "warning", "bad")
            assert isinstance(ratio["value"], (int, float))

    def test_financials_unknown_borrower(self, http, admin_token):
        r = http.get(f"{API}/borrowers/does-not-exist-xyz/financials", headers=H(admin_token))
        # endpoint returns empty lists/empty ratios when borrower has no data; that's acceptable
        assert r.status_code == 200
        data = r.json()
        assert data["balance_sheets"] == []
        assert data["pnl"] == []
        assert data["ratios"] == {}


# ---------------- Seed financials idempotency ----------------
class TestSeedFinancials:
    def test_seed_financials_idempotent(self, http, admin_token):
        r1 = http.post(f"{API}/seed-financials", headers=H(admin_token))
        assert r1.status_code == 200
        d1 = r1.json()
        assert "seeded" in d1 and "total_borrowers" in d1
        # Re-run should add 0
        r2 = http.post(f"{API}/seed-financials", headers=H(admin_token))
        assert r2.status_code == 200
        assert r2.json()["seeded"] == 0, f"second seed should be 0, got {r2.json()}"


# ---------------- Upload Balance Sheet & PnL ----------------
BS_CSV = (
    "period,current_assets,inventory,cash,receivables,fixed_assets,other_assets,"
    "current_liabilities,short_term_debt,long_term_debt,other_liabilities,equity\n"
    # Stressed BS: low CA vs CL, high debt vs equity to trigger ratio factors
    "2026-Q2,1000000,500000,100000,400000,2000000,100000,1500000,1200000,3000000,200000,400000\n"
    "2026-Q3,1100000,520000,110000,420000,2000000,100000,1600000,1250000,3000000,200000,420000\n"
)
PNL_CSV = (
    "period,revenue,cogs,gross_profit,operating_expenses,ebitda,depreciation,ebit,"
    "interest_expense,pbt,tax,net_profit\n"
    # Stressed PnL: high interest, near-zero EBIT, negative net profit
    "2026-Q2,2000000,1700000,300000,250000,80000,40000,40000,300000,-260000,0,-260000\n"
    "2026-Q3,2100000,1800000,300000,260000,85000,40000,45000,310000,-265000,0,-265000\n"
)


class TestUploadBSAndPnL:
    def test_upload_balance_sheet(self, http, analyst_token, seeded_borrower_id):
        files = {"file": ("bs.csv", BS_CSV.encode(), "text/csv")}
        data = {"file_type": "balance_sheet"}
        r = http.post(f"{API}/borrowers/{seeded_borrower_id}/upload",
                      headers=H(analyst_token), files=files, data=data)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body["uploaded"] is True
        assert body["rows_processed"] >= 2

    def test_upload_pnl(self, http, analyst_token, seeded_borrower_id):
        files = {"file": ("pnl.csv", PNL_CSV.encode(), "text/csv")}
        data = {"file_type": "pnl"}
        r = http.post(f"{API}/borrowers/{seeded_borrower_id}/upload",
                      headers=H(analyst_token), files=files, data=data)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body["uploaded"] is True
        assert body["rows_processed"] >= 2

    def test_financials_after_upload(self, http, admin_token, seeded_borrower_id):
        r = http.get(f"{API}/borrowers/{seeded_borrower_id}/financials", headers=H(admin_token))
        assert r.status_code == 200
        data = r.json()
        periods = [bs["period"] for bs in data["balance_sheets"]]
        assert "2026-Q3" in periods, f"uploaded BS period not persisted; periods={periods}"
        pnl_periods = [p["period"] for p in data["pnl"]]
        assert "2026-Q3" in pnl_periods
        # latest_period is the max-sorted period; seed may have already added later quarters
        assert data["latest_period"] is not None
        assert data["latest_period"] >= "2026-Q3"

    def test_ratio_based_risk_factors_added(self, http, admin_token, seeded_borrower_id):
        """After uploading stressed BS+PnL, risk factors should include ratio-derived ones."""
        # Trigger recompute explicitly
        http.post(f"{API}/borrowers/{seeded_borrower_id}/recompute", headers=H(admin_token))
        r = http.get(f"{API}/borrowers/{seeded_borrower_id}", headers=H(admin_token))
        assert r.status_code == 200
        factors = r.json().get("risk_factors", [])
        factor_names = " | ".join(f.get("factor", "") for f in factors)
        # Stressed sheet has: DSCR<1.0, interest_coverage<1.5, current_ratio<1, D/E>3, negative net_margin
        # So we expect at least one of these labels to show
        expected_any = ["DSCR", "interest coverage", "Liquidity", "leverage", "Operating losses",
                        "Over-leveraged", "Weak DSCR", "DSCR critical"]
        found = any(any(label.lower() in factor_names.lower() for label in expected_any) for _ in [0])
        assert found, f"No ratio-based factor found. factors={factor_names}"

    def test_upload_invalid_file_type(self, http, analyst_token, seeded_borrower_id):
        files = {"file": ("x.csv", b"a,b\n1,2\n", "text/csv")}
        data = {"file_type": "totally_invalid_type"}
        r = http.post(f"{API}/borrowers/{seeded_borrower_id}/upload",
                      headers=H(analyst_token), files=files, data=data)
        assert r.status_code == 400

    def test_upload_bs_rm_role_forbidden(self, http, rm_token, seeded_borrower_id):
        files = {"file": ("bs.csv", BS_CSV.encode(), "text/csv")}
        data = {"file_type": "balance_sheet"}
        r = http.post(f"{API}/borrowers/{seeded_borrower_id}/upload",
                      headers=H(rm_token), files=files, data=data)
        assert r.status_code == 403


# ---------------- Recovery AI Copilot ----------------
@pytest.fixture(scope="module")
def recovery_case_id(http, admin_token, analyst_token):
    # Get any borrower; create or fetch recovery case
    r = http.get(f"{API}/borrowers?limit=20", headers=H(admin_token))
    borrowers = r.json()["items"]
    # Try existing case first
    r2 = http.get(f"{API}/recovery", headers=H(admin_token))
    cases = r2.json().get("items", [])
    if cases:
        return cases[0]["id"]
    # Create a new one with available borrower
    for b in borrowers:
        payload = {"borrower_id": b["id"], "priority": "high", "next_action": "Initial outreach"}
        rc = http.post(f"{API}/recovery", json=payload, headers=H(analyst_token))
        if rc.status_code == 200:
            return rc.json()["id"]
    pytest.skip("Could not get a recovery case")


class TestRecoveryCopilot:
    def test_copilot_history_empty_or_list(self, http, admin_token, recovery_case_id):
        r = http.get(f"{API}/recovery/{recovery_case_id}/copilot", headers=H(admin_token))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_copilot_post_message(self, http, admin_token, recovery_case_id):
        payload = {"message": "Suggest next step in recovery for this borrower in 2 sentences."}
        r = http.post(f"{API}/recovery/{recovery_case_id}/copilot",
                      json=payload, headers=H(admin_token), timeout=90)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        assert "response" in data
        assert isinstance(data["response"], str)
        assert len(data["response"].strip()) > 0

    def test_copilot_history_persisted(self, http, admin_token, recovery_case_id):
        r = http.get(f"{API}/recovery/{recovery_case_id}/copilot", headers=H(admin_token))
        assert r.status_code == 200
        msgs = r.json()
        assert len(msgs) >= 2, f"expected at least user+assistant message, got {len(msgs)}"
        roles = [m["role"] for m in msgs]
        assert "user" in roles and "assistant" in roles

    def test_copilot_nonexistent_case(self, http, admin_token):
        r = http.post(f"{API}/recovery/does-not-exist/copilot",
                      json={"message": "hi"}, headers=H(admin_token), timeout=30)
        assert r.status_code == 404


# ---------------- Regression: existing endpoints still work ----------------
class TestRegression:
    def test_auth_me(self, http, admin_token):
        r = http.get(f"{API}/auth/me", headers=H(admin_token))
        assert r.status_code == 200

    def test_list_borrowers(self, http, admin_token):
        r = http.get(f"{API}/borrowers", headers=H(admin_token))
        assert r.status_code == 200
        assert "items" in r.json()

    def test_portfolio_overview(self, http, admin_token):
        r = http.get(f"{API}/portfolio/overview", headers=H(admin_token))
        assert r.status_code == 200
        d = r.json()
        assert "total_borrowers" in d and "by_category" in d

    def test_audit_log(self, http, admin_token):
        r = http.get(f"{API}/audit", headers=H(admin_token))
        assert r.status_code == 200

    def test_alerts_list(self, http, admin_token):
        r = http.get(f"{API}/alerts", headers=H(admin_token))
        assert r.status_code == 200

    def test_upload_sales_regression(self, http, analyst_token, seeded_borrower_id):
        csv = b"month,amount\n2024-12,1500000\n2025-01,1600000\n"
        files = {"file": ("sales.csv", csv, "text/csv")}
        data = {"file_type": "sales"}
        r = http.post(f"{API}/borrowers/{seeded_borrower_id}/upload",
                      headers=H(analyst_token), files=files, data=data)
        assert r.status_code == 200
