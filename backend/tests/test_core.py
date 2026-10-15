from decimal import Decimal
from pathlib import Path
from .conftest import make_client, signup, H

CSV = "Date,Description,Debit,Credit\n01/09/2026,Salary ACME,,50000\n02/09/2026,Swiggy order,450.50,\n03/09/2026,Rent,15000,\n04/09/2026,Self transfer,2000,\nbad,Oops,1,\n"

def test_auth_flow_and_generic_failure():
    c = make_client()
    assert c.get("/api/v1/auth/me").status_code == 401
    signup(c, "a@example.com")
    assert c.get("/api/v1/auth/me").json()["email"] == "a@example.com"
    r = make_client().post("/api/v1/auth/login", json={"email": "a@example.com", "password": "wrong-password-1"})
    assert r.status_code == 401 and r.json()["detail"] == "Invalid email or password"

def test_authentication_attempts_are_rate_limited():
    client = make_client()
    for _ in range(10):
        response = client.post("/api/v1/auth/login", json={
            "email": "throttle@example.com", "password": "wrong-password-123",
        })
        assert response.status_code == 401
    limited = client.post("/api/v1/auth/login", json={
        "email": "throttle@example.com", "password": "wrong-password-123",
    })
    assert limited.status_code == 429

def test_csrf_header_required():
    from fastapi.testclient import TestClient
    from app.main import app
    assert TestClient(app).post("/api/v1/auth/logout").status_code == 403

def test_cross_user_isolation():
    a, b = signup(make_client(), "iso-a@example.com"), signup(make_client(), "iso-b@example.com")
    tid = a.post("/api/v1/transactions", json={"date": "2026-09-01", "description": "Coffee", "amount": "120", "direction": "debit"}).json()["id"]
    assert b.get(f"/api/v1/transactions/{tid}").status_code == 404
    assert b.patch(f"/api/v1/transactions/{tid}", json={"category": "X"}).status_code == 404
    assert b.delete(f"/api/v1/transactions/{tid}").status_code == 404
    assert b.get("/api/v1/transactions").json()["total"] == 0
    updated = a.patch(f"/api/v1/transactions/{tid}", json={"date": "2026-09-02", "amount": "150.00", "direction": "credit"})
    assert updated.status_code == 200 and updated.json()["amount"] == "150.00"
    assert a.get(f"/api/v1/transactions/{tid}").status_code == 200

def test_csv_import_preview_confirm_and_analytics():
    c = signup(make_client(), "imp@example.com")
    r = c.post("/api/v1/imports", files={"file": ("s.csv", CSV, "text/csv")})
    assert r.status_code == 201
    statuses = [x["status"] for x in r.json()["rows"]]
    assert statuses == ["ok", "ok", "ok", "ok", "error"]
    assert c.get("/api/v1/analytics/overview").json()["transaction_count"] == 0  # nothing saved before confirm
    jid = r.json()["id"]
    assert c.post(f"/api/v1/imports/{jid}/confirm").json()["imported"] == 4
    o = c.get("/api/v1/analytics/overview").json()
    assert Decimal(o["income"]) == Decimal("50000") and Decimal(o["expenses"]) == Decimal("15450.50")  # transfer excluded
    assert o["savings_rate"] == "0.6910"
    # re-import flags duplicates
    r2 = c.post("/api/v1/imports", files={"file": ("s.csv", CSV, "text/csv")})
    assert [x["status"] for x in r2.json()["rows"]].count("duplicate") == 4
    assert c.post(f"/api/v1/imports/{jid}/confirm").status_code == 409
    assert c.post(f"/api/v1/imports/{r2.json()['id']}/confirm").json()["imported"] == 0  # duplicates never double-saved
    other = signup(make_client(), "imp2@example.com")
    assert other.get(f"/api/v1/imports/{jid}/preview").status_code == 404

def test_invalid_uploads_not_silent_success():
    c = signup(make_client(), "bad@example.com")
    assert c.post("/api/v1/imports", files={"file": ("x.csv", "foo,bar\n1,2\n", "text/csv")}).status_code == 422
    invalid_pdf = c.post("/api/v1/imports", files={"file": ("x.pdf", b"%PDF-1.4 ...", "application/pdf")})
    assert invalid_pdf.status_code == 422 and "readable PDF" in invalid_pdf.json()["detail"]
    assert c.post("/api/v1/imports", files={"file": ("x.csv", b"\xff\xfe\x00", "text/csv")}).status_code == 422

def test_pdf_import_requires_review_and_confirm_before_saving():
    payload = (Path(__file__).resolve().parents[2] / "data" / "synthetic" / "bank_statement_sample.pdf").read_bytes()
    client = signup(make_client(), "pdf@example.com")
    preview = client.post("/api/v1/imports", files={"file": ("statement.pdf", payload, "application/pdf")})
    assert preview.status_code == 201
    data = preview.json()
    assert data["source_type"] == "pdf" and data["confidence"] == "review_required"
    assert len(data["rows"]) == 4 and all(row["status"] == "ok" for row in data["rows"])
    assert client.get("/api/v1/analytics/overview").json()["transaction_count"] == 0
    confirmed = client.post(f"/api/v1/imports/{data['id']}/confirm")
    assert confirmed.json()["imported"] == 4
    assert client.get("/api/v1/analytics/overview").json()["transaction_count"] == 4

def test_financial_assistant_is_grounded_in_the_signed_in_users_data():
    client = signup(make_client(), "assistant@example.com")
    question = client.post("/api/v1/assistant/query", json={"question": "How much did I spend in September 2026?"})
    assert question.status_code == 200 and "transactions for your account" in question.json()["answer"]
    client.post("/api/v1/transactions", json={"date": "2026-09-02", "description": "Groceries",
                                               "amount": "1200.50", "direction": "debit"})
    result = client.post("/api/v1/assistant/query", json={"question": "How much did I spend on groceries in September 2026?"})
    assert result.json()["calculation"]["value"] == "1200.50"
    assert result.json()["calculation"]["currency"] == "INR"

def test_preview_corrections_are_saved_only_after_confirmation():
    content = (Path(__file__).resolve().parents[2] / "data" / "synthetic" / "bank_statement_sample.pdf").read_bytes()
    client = signup(make_client(), "review@example.com")
    preview = client.post("/api/v1/imports", files={"file": ("statement.pdf", content, "application/pdf")}).json()
    row = preview["rows"][0]
    corrected = client.patch(f"/api/v1/imports/{preview['id']}/preview", json={"rows": [{
        "line": row["line"], "description": "Metro card recharge", "amount": "250.00",
    }]})
    assert corrected.status_code == 200
    assert next(item for item in corrected.json()["rows"] if item["line"] == row["line"])["amount"] == "250.00"
    persisted = client.get(f"/api/v1/imports/{preview['id']}/preview").json()
    assert next(item for item in persisted["rows"] if item["line"] == row["line"])["amount"] == "250.00"
    assert client.get("/api/v1/analytics/overview").json()["transaction_count"] == 0
    assert client.post(f"/api/v1/imports/{preview['id']}/confirm").json()["imported"] == 4
    stored = next(item for item in client.get("/api/v1/transactions").json()["items"]
                  if item["description"] == "Metro card recharge" and item["date"] == "2026-09-01")
    assert stored["amount"] == "250.00"

def test_knowledge_retrieval_cites_retrieved_notes_and_abstains():
    client = signup(make_client(), "learn@example.com")
    answer = client.post("/api/v1/assistant/query", json={"question": "Explain compound interest"})
    assert answer.json()["mode"] == "local_retrieval"
    assert answer.json()["citations"][0]["id"] == "compound-interest"
    unknown = client.post("/api/v1/assistant/query", json={"question": "What is the capital of France?"})
    assert unknown.json()["citations"] == []
    assert "not enough evidence" in unknown.json()["answer"]

def test_budgets_and_goals_are_user_scoped():
    owner = signup(make_client(), "plan-a@example.com")
    other = signup(make_client(), "plan-b@example.com")
    created = owner.post("/api/v1/budgets", json={"category": "Groceries", "amount": "10000", "period_start": "2026-09-01"})
    assert created.status_code == 201
    owner.post("/api/v1/transactions", json={"date": "2026-09-12", "description": "Groceries",
                                               "amount": "1250.50", "direction": "debit", "category": "Groceries"})
    goal = owner.post("/api/v1/goals", json={"name": "Emergency fund", "target_amount": "50000", "saved_amount": "12500"})
    assert goal.json()["progress"] == "0.25"
    budget = owner.get("/api/v1/budgets").json()[0]
    assert budget["spent"] == "1250.50" and budget["usage"] == "0.1251"
    assert other.get("/api/v1/budgets").json() == []
    assert other.get("/api/v1/goals").json() == []

def test_user_settings_and_data_deletion_are_scoped():
    owner = signup(make_client(), "settings-a@example.com")
    other = signup(make_client(), "settings-b@example.com")
    owner.post("/api/v1/transactions", json={"date": "2026-09-02", "description": "Groceries",
                                              "amount": "1200", "direction": "debit"})
    assert owner.get("/api/v1/settings").json()["bank_connectivity"] == "not_available_in_mvp"
    assert owner.post("/api/v1/settings/export").json()["transactions"][0]["amount"] == "1200.00"
    owner.delete("/api/v1/settings/transactions")
    assert owner.get("/api/v1/analytics/overview").json()["transaction_count"] == 0
    assert other.get("/api/v1/analytics/overview").json()["transaction_count"] == 0
