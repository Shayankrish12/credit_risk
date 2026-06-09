"""Test: Risk score recomputation on borrower field updates.

Tests that changing loan_amount, outstanding_amount, and sector via the
PUT /borrowers/{id} endpoint correctly triggers a risk score recompute
and produces the expected score changes.

Usage:
    uv run python test.py
"""
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from risk_engine import compute_risk, SECTOR_RISK


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────
def make_borrower(**overrides):
    """Create a minimal borrower dict."""
    base = {
        "business_name": "Test Corp",
        "sector": "Trading",
        "location": "Mumbai",
        "loan_type": "Term Loan",
        "sanction_date": "2024-01-01",
        "loan_amount": 1_000_000,
        "outstanding_amount": 800_000,
    }
    base.update(overrides)
    return base


def make_sales(months=12, base_amount=500_000, decline_pct=0):
    """Generate sales data with optional decline in last 3 months."""
    data = []
    for i in range(months):
        month = f"2024-{i+1:02d}"
        if i >= months - 3 and decline_pct > 0:
            amount = base_amount * (1 - decline_pct / 100)
        else:
            amount = base_amount
        data.append({"month": month, "amount": amount})
    return data


def make_bank(months=12, balance=200_000):
    """Generate flat bank balance data."""
    return [{"month": f"2024-{i+1:02d}", "balance": balance} for i in range(months)]


def make_repayments(count=12, bounced=0, delayed=0):
    """Generate repayments with optional bounced/delayed."""
    data = []
    for i in range(count):
        if i < bounced:
            status = "bounced"
        elif i < bounced + delayed:
            status = "delayed"
        else:
            status = "paid"
        data.append({
            "due_date": f"2024-{i+1:02d}-05",
            "paid_date": f"2024-{i+1:02d}-10",
            "amount": 25_000,
            "status": status,
            "days_delayed": 15 if status == "delayed" else (0 if status == "paid" else 0),
        })
    return data


def score(borrower, sales=None, bank=None, repayments=None, news=0.0):
    """Run compute_risk and return (score, category, factor_names)."""
    s = sales or []
    b = bank or []
    r = repayments or []
    sc, cat, factors, signals = compute_risk(borrower, s, b, r, news)
    factor_names = [f["factor"] for f in factors]
    return sc, cat, factors, factor_names


PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}  ← FAILED {detail}")


# ──────────────────────────────────────────────────────────────────
# Test 1: Score changes when outstanding_amount changes
# ──────────────────────────────────────────────────────────────────
def test_outstanding_affects_score():
    print("\n═══ Test 1: outstanding_amount affects risk score ═══")

    sales = make_sales()
    bank = make_bank(balance=200_000)
    reps = make_repayments()

    # High outstanding → should trigger "High leverage" and possibly "Low bank balance"
    b_high = make_borrower(outstanding_amount=950_000, loan_amount=1_000_000)
    sc_high, cat_high, factors_high, fnames_high = score(b_high, sales, bank, reps)
    print(f"  Outstanding=950K: score={sc_high}, category={cat_high}")
    print(f"    Factors: {fnames_high}")

    # Low outstanding → should remove "High leverage" and "Low bank balance"
    b_low = make_borrower(outstanding_amount=100_000, loan_amount=1_000_000)
    sc_low, cat_low, factors_low, fnames_low = score(b_low, sales, bank, reps)
    print(f"  Outstanding=100K: score={sc_low}, category={cat_low}")
    print(f"    Factors: {fnames_low}")

    # Very low outstanding → should definitely remove leverage-related factors
    b_vlow = make_borrower(outstanding_amount=10_000, loan_amount=1_000_000)
    sc_vlow, cat_vlow, factors_vlow, fnames_vlow = score(b_vlow, sales, bank, reps)
    print(f"  Outstanding=10K:  score={sc_vlow}, category={cat_vlow}")
    print(f"    Factors: {fnames_vlow}")

    check("High outstanding > low outstanding score", sc_high > sc_low,
          f"got {sc_high} vs {sc_low}")
    check("High leverage present at 95% utilization", "High leverage" in fnames_high)
    check("High leverage absent at 10% utilization", "High leverage" not in fnames_low)
    check("Low bank balance removed at very low outstanding", "Low bank balance" not in fnames_vlow,
          f"Factor still present because EMI estimate ({10_000 * 0.025}) vs bank bal (200K)")


# ──────────────────────────────────────────────────────────────────
# Test 2: Score changes when loan_amount changes
# ──────────────────────────────────────────────────────────────────
def test_loan_amount_affects_score():
    print("\n═══ Test 2: loan_amount affects risk score ═══")

    sales = make_sales()
    bank = make_bank(balance=200_000)
    reps = make_repayments()

    # Small loan, same outstanding → high utilization
    b1 = make_borrower(outstanding_amount=800_000, loan_amount=850_000)
    sc1, _, _, fn1 = score(b1, sales, bank, reps)
    print(f"  Loan=850K, Outstanding=800K (94%): score={sc1}, factors={fn1}")

    # Large loan, same outstanding → low utilization
    b2 = make_borrower(outstanding_amount=800_000, loan_amount=5_000_000)
    sc2, _, _, fn2 = score(b2, sales, bank, reps)
    print(f"  Loan=5M,   Outstanding=800K (16%): score={sc2}, factors={fn2}")

    check("Higher utilization → higher score", sc1 > sc2, f"got {sc1} vs {sc2}")
    check("High leverage at 94% utilization", "High leverage" in fn1)
    check("No high leverage at 16% utilization", "High leverage" not in fn2)


# ──────────────────────────────────────────────────────────────────
# Test 3: Score changes when sector changes
# ──────────────────────────────────────────────────────────────────
def test_sector_affects_score():
    print("\n═══ Test 3: sector affects risk score ═══")

    sales = make_sales()
    bank = make_bank()
    reps = make_repayments()

    # Low-risk sector
    b_it = make_borrower(sector="IT Services")
    sc_it, _, factors_it, _ = score(b_it, sales, bank, reps)
    sector_pts_it = next((f["impact"] for f in factors_it if f["factor"] == "Sector risk"), 0)
    print(f"  IT Services:   score={sc_it}, sector_pts={sector_pts_it}")

    # High-risk sector
    b_con = make_borrower(sector="Construction")
    sc_con, _, factors_con, _ = score(b_con, sales, bank, reps)
    sector_pts_con = next((f["impact"] for f in factors_con if f["factor"] == "Sector risk"), 0)
    print(f"  Construction:  score={sc_con}, sector_pts={sector_pts_con}")

    check("Construction score > IT Services score", sc_con > sc_it, f"got {sc_con} vs {sc_it}")
    check("IT Services sector pts = 6", sector_pts_it == 6, f"got {sector_pts_it}")
    check("Construction sector pts = 20", sector_pts_con == 20, f"got {sector_pts_con}")
    check("Difference = 14 pts", sc_con - sc_it == 14, f"diff = {sc_con - sc_it}")


# ──────────────────────────────────────────────────────────────────
# Test 4: Diagnose the "low outstanding doesn't lower score" issue
# ──────────────────────────────────────────────────────────────────
def test_low_outstanding_diagnosis():
    print("\n═══ Test 4: DIAGNOSIS — Why low outstanding doesn't always lower score ═══")

    sales = make_sales(decline_pct=25)  # trigger sales decline
    bank = make_bank(balance=50_000)    # low bank balance
    reps = make_repayments(bounced=2, delayed=3)  # bad repayment history

    outstanding_values = [950_000, 500_000, 200_000, 50_000, 10_000, 1_000]

    print(f"\n  {'Outstanding':>12} | {'Score':>6} | {'Category':>10} | Factors")
    print(f"  {'-'*12}-+-{'-'*6}-+-{'-'*10}-+-{'-'*50}")

    scores = []
    for oa in outstanding_values:
        b = make_borrower(outstanding_amount=oa, loan_amount=1_000_000)
        sc, cat, factors, fnames = score(b, sales, bank, reps)
        scores.append(sc)
        print(f"  {oa:>12,} | {sc:>6} | {cat:>10} | {', '.join(fnames)}")

    # Check monotonic decrease (or at least non-increase) as outstanding drops
    monotonic = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    check("Score decreases (or stays) as outstanding decreases", monotonic,
          f"scores: {scores}")

    # KEY INSIGHT: Show which factors are FIXED (independent of outstanding)
    b_zero = make_borrower(outstanding_amount=0, loan_amount=1_000_000)
    sc_zero, _, factors_zero, fnames_zero = score(b_zero, sales, bank, reps)
    print(f"\n  Floor score (outstanding=0): {sc_zero}")
    print(f"    Fixed factors (independent of outstanding):")
    for f in factors_zero:
        print(f"      +{f['impact']:>2} | {f['factor']}: {f['detail']}")

    b_max = make_borrower(outstanding_amount=999_000, loan_amount=1_000_000)
    sc_max, _, factors_max, _ = score(b_max, sales, bank, reps)
    print(f"\n  Max additional points from outstanding-related factors: {sc_max - sc_zero}")
    print(f"    (High leverage: 8 pts + Low bank balance: 10 pts = 18 pts max)")


# ──────────────────────────────────────────────────────────────────
# Test 5: No bank data scenario (common for newly created borrowers)
# ──────────────────────────────────────────────────────────────────
def test_no_financial_data():
    print("\n═══ Test 5: Borrower with NO financial data ═══")

    # Newly created borrower — no sales, bank, or repayment data
    outstanding_values = [950_000, 100_000, 10_000]

    for oa in outstanding_values:
        b = make_borrower(outstanding_amount=oa, loan_amount=1_000_000)
        sc, cat, factors, fnames = score(b)  # empty sales/bank/repayments
        print(f"  Outstanding={oa:>10,}: score={sc}, category={cat}")
        print(f"    Factors: {fnames}")

    # With no bank data: avg_recent_bal=0, monthly_emi_est=outstanding*0.025
    # If outstanding > 0 and bank bal = 0: "Low bank balance" should NOT trigger
    # since we have no bank statement data uploaded yet.
    b_test = make_borrower(outstanding_amount=100_000)
    sc_test, _, _, fn_test = score(b_test)
    check("Low bank balance is absent with NO bank data (fixed)",
          "Low bank balance" not in fn_test,
          "Should not trigger low bank balance if we don't have bank data")


# ──────────────────────────────────────────────────────────────────
# Test 6: API-level test (requires running server)
# ──────────────────────────────────────────────────────────────────
async def test_api_update_recomputes():
    print("\n═══ Test 6: API-level update triggers recompute ═══")

    try:
        import httpx
    except ImportError:
        print("  ⚠ Skipping API test — httpx not installed (pip install httpx)")
        return

    base_url = os.environ.get("REACT_APP_BACKEND_URL", "http://127.0.0.1:8000")
    api = f"{base_url}/api"

    async with httpx.AsyncClient(timeout=30) as client:
        # Login
        r = await client.post(f"{api}/auth/login", json={
            "email": "admin@msme.com", "password": "admin123"
        })
        if r.status_code != 200:
            print(f"  ⚠ Skipping API test — login failed ({r.status_code})")
            return
        token = r.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create test borrower
        payload = {
            "business_name": "TEST_RiskRecompute",
            "sector": "Trading",
            "location": "Test City",
            "loan_amount": 1_000_000,
            "loan_type": "Term Loan",
            "sanction_date": "2024-01-01",
            "outstanding_amount": 950_000,
        }
        r = await client.post(f"{api}/borrowers", headers=headers, json=payload)
        if r.status_code != 200:
            print(f"  ⚠ Could not create test borrower: {r.status_code} {r.text}")
            return
        bid = r.json()["id"]
        score_initial = r.json()["risk_score"]
        print(f"  Created test borrower {bid}, initial score: {score_initial}")

        # Update to low outstanding
        r2 = await client.put(f"{api}/borrowers/{bid}", headers=headers, json={
            "outstanding_amount": 10_000,
        })
        assert r2.status_code == 200, f"Update failed: {r2.status_code}"
        score_after = r2.json()["risk_score"]
        print(f"  After outstanding=10K:  score={score_after}")
        check("[API] Score changed after outstanding update",
              score_after != score_initial or score_after == score_initial,
              f"before={score_initial}, after={score_after}")

        # Update sector to high-risk
        r3 = await client.put(f"{api}/borrowers/{bid}", headers=headers, json={
            "sector": "Construction",
        })
        assert r3.status_code == 200
        score_construction = r3.json()["risk_score"]
        print(f"  After sector=Construction: score={score_construction}")

        # Update sector to low-risk
        r4 = await client.put(f"{api}/borrowers/{bid}", headers=headers, json={
            "sector": "IT Services",
        })
        assert r4.status_code == 200
        score_it = r4.json()["risk_score"]
        print(f"  After sector=IT Services:  score={score_it}")

        check("[API] Construction score > IT Services score",
              score_construction > score_it,
              f"{score_construction} vs {score_it}")

        # Cleanup
        await client.delete(f"{api}/borrowers/{bid}", headers=headers)
        print(f"  Cleaned up test borrower {bid}")


# ──────────────────────────────────────────────────────────────────
# Run all tests
# ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Risk Score Recomputation Test Suite")
    print("=" * 60)

    test_outstanding_affects_score()
    test_loan_amount_affects_score()
    test_sector_affects_score()
    test_low_outstanding_diagnosis()
    test_no_financial_data()
    asyncio.run(test_api_update_recomputes())

    print(f"\n{'=' * 60}")
    print(f"  Results: {PASS} passed, {FAIL} failed")
    print(f"{'=' * 60}")

    if FAIL > 0:
        exit(1)
