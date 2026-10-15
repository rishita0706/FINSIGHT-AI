from decimal import Decimal
from .conftest import make_client, signup, H

CSV = "Date,Description,Debit,Credit\n01/09/2026,Salary ACME,,50000\n02/09/2026,Swiggy order,450.50,\n03/09/2026,Rent,15000,\n04/09/2026,Self transfer,2000,\nbad,Oops,1,\n"

def test_auth_flow_and_generic_failure():
    c = make_client()
    assert c.get("/api/v1/auth/me").status_code == 401
    signup(c, "a@example.com")
    assert c.get("/api/v1/auth/me").json()["email"] == "a@example.com"
    r = make_client().post("/api/v1/auth/login", json={"email": "a@example.com", "password": "wrong-password-1"})
    assert r.status_code == 401 and r.json()["detail"] == "Invalid email or password"

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
    assert c.post("/api/v1/imports", files={"file": ("x.pdf", b"%PDF-1.4 ...", "application/pdf")}).status_code == 501
    assert c.post("/api/v1/imports", files={"file": ("x.csv", b"\xff\xfe\x00", "text/csv")}).status_code == 422
