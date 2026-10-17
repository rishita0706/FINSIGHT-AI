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

def test_login_rotates_and_revokes_the_previous_session():
    client = signup(make_client(), "rotation@example.com")
    old_token = client.cookies.get("fs_session")
    assert old_token
    assert client.post("/api/v1/auth/login", json={
        "email": "rotation@example.com", "password": "correct-horse-battery",
    }).status_code == 200
    new_token = client.cookies.get("fs_session")
    assert new_token and new_token != old_token
    old_session = make_client()
    old_session.cookies.set("fs_session", old_token)
    assert old_session.get("/api/v1/auth/me").status_code == 401

def test_secure_cookie_and_hsts_are_enabled_together(monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "true")
    client = make_client()
    response = client.post("/api/v1/auth/register", json={
        "email": "secure-cookie@example.com", "password": "correct-horse-battery",
    })
    assert response.status_code == 201
    login = client.post("/api/v1/auth/login", json={
        "email": "secure-cookie@example.com", "password": "correct-horse-battery",
    })
    assert "secure" in login.headers["set-cookie"].casefold()
    assert "strict-transport-security" in login.headers

def test_security_headers_and_upload_content_sniffing():
    client = signup(make_client(), "headers@example.com")
    headers = client.get("/health").headers
    assert headers["content-security-policy"].startswith("default-src 'none'")
    assert headers["x-content-type-options"] == "nosniff"
    pdf_as_csv = client.post("/api/v1/imports", files={
        "file": ("mislabelled.csv", b"%PDF-1.4 invalid", "text/csv"),
    })
    csv_as_pdf = client.post("/api/v1/imports", files={
        "file": ("mislabelled.pdf", CSV, "application/pdf"),
    })
    assert pdf_as_csv.status_code == csv_as_pdf.status_code == 415

def test_csrf_header_required():
    from fastapi.testclient import TestClient
    from app.main import app
    response = TestClient(app).post("/api/v1/auth/logout")
    assert response.status_code == 403
    assert response.headers["content-security-policy"].startswith("default-src 'none'")

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
    overview = client.get("/api/v1/analytics/overview", params={
        "start": "2026-09-01", "end": "2026-09-30",
    }).json()
    assert result.json()["calculation"]["value"] == overview["expenses"]

def test_pdf_import_review_confirmation_and_assistant_analytics_consistency():
    content = (Path(__file__).resolve().parents[2] / "data" / "synthetic" / "bank_statement_sample.pdf").read_bytes()
    client = signup(make_client(), "pdf-e2e@example.com")
    preview_response = client.post(
        "/api/v1/imports",
        files={"file": ("statement.pdf", content, "application/pdf")},
    )
    assert preview_response.status_code == 201
    preview = preview_response.json()
    assert preview["status"] == "preview"
    selected = next(row for row in preview["rows"] if row["status"] == "ok")
    reviewed = client.patch(
        f"/api/v1/imports/{preview['id']}/preview",
        json={"rows": [{
            "line": selected["line"],
            "category": "Reviewed category",
        }]},
    )
    assert reviewed.status_code == 200
    confirmed = client.post(f"/api/v1/imports/{preview['id']}/confirm")
    assert confirmed.status_code == 200
    overview = client.get("/api/v1/analytics/overview").json()
    answer = client.post(
        "/api/v1/assistant/query",
        json={"question": "How much did I spend in September 2026?"},
    ).json()
    assert answer["calculation"]["value"] == overview["expenses"]

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
    cited_document = client.get(answer.json()["citations"][0]["href"])
    assert cited_document.status_code == 200 and cited_document.json()["content"]
    unknown = client.post("/api/v1/assistant/query", json={"question": "What is the capital of France?"})
    assert unknown.json()["citations"] == []
    assert "not enough evidence" in unknown.json()["answer"]

def test_pgvector_cosine_distance_expression_returns_scalar_type():
    from sqlalchemy import Float
    from app.models import KnowledgeChunk

    distance = KnowledgeChunk.embedding.op("<=>", return_type=Float())([0.0] * 1536)
    assert isinstance(distance.type, Float)

def test_knowledge_refresh_is_versioned_and_idempotent():
    from app.db import SessionLocal
    from app.integrations.llm import MockProvider
    from app.knowledge import refresh_knowledge_base
    from app.models import KnowledgeChunk, KnowledgeDocument

    with SessionLocal() as db:
        assert refresh_knowledge_base(db, MockProvider()) in {0, 6}
        assert refresh_knowledge_base(db, MockProvider()) == 0
        assert db.query(KnowledgeDocument).count() == 6
        assert db.query(KnowledgeChunk).count() == 6

def test_knowledge_ingestion_extracts_html_pdf_and_text():
    import pymupdf
    from app.knowledge import extract_document_text

    html = b"<html><body><h1>Budget guide</h1><script>ignore this</script><p>Plan spending.</p></body></html>"
    assert extract_document_text(html, "text/html") == "Budget guide\n\nPlan spending."
    assert "simple text" in extract_document_text(b"simple text", "text/plain")
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "PDF body text")
    raw_pdf = pdf.tobytes()
    pdf.close()
    assert "PDF body text" in extract_document_text(raw_pdf, "application/pdf")

def test_llm_adapter_cannot_change_verified_values_or_urls():
    from app.integrations.llm import Generation, MockProvider, phrase_verified

    class HallucinatingProvider(MockProvider):
        def generate(self, instruction: str, verified_text: str) -> Generation:
            return Generation(
                verified_text.replace("10.00", "99.00") + " https://unverified.example",
                input_tokens=10,
                output_tokens=12,
            )

    source = "Verified total is ₹10.00. See https://www.rbi.org.in/FinancialEducation/Home.aspx"
    result = phrase_verified(HallucinatingProvider(), source)
    assert result.text == source and result.output_tokens == 0
    assert len(MockProvider().embed("budgeting")) == 1536

def test_categorizer_evaluation_is_available_to_the_ui():
    client = signup(make_client(), "evaluation@example.com")
    evaluation = client.get("/api/v1/ml/categorizer/evaluation").json()
    assert evaluation["available"] is True
    assert evaluation["version"] == "categorizer-v1"
    assert evaluation["needs_review_confidence_threshold"] == 0.6
    assert "precision" in evaluation["per_class"]["Groceries"]
    assert len(evaluation["confusion_matrix"]) == len(evaluation["labels"])

def test_conversation_history_is_persisted_and_user_scoped():
    owner = signup(make_client(), "conversation-a@example.com")
    other = signup(make_client(), "conversation-b@example.com")
    conversation = owner.post("/api/v1/conversations").json()
    response = owner.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"question": "How much did I spend in September 2026?"},
    )
    assert response.status_code == 201
    detail = owner.get(f"/api/v1/conversations/{conversation['id']}").json()
    assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["calculation"] is None
    assert other.get(f"/api/v1/conversations/{conversation['id']}").status_code == 404
    assert other.delete(f"/api/v1/conversations/{conversation['id']}").status_code == 404
    assert owner.delete(f"/api/v1/conversations/{conversation['id']}").status_code == 204
    assert owner.get(f"/api/v1/conversations/{conversation['id']}").status_code == 404

def test_combined_assistant_answer_persists_separate_verified_sections():
    client = signup(make_client(), "combined-answer@example.com")
    assert client.post("/api/v1/transactions", json={
        "date": "2026-09-05", "description": "Grocery store", "amount": "25.00",
        "direction": "debit", "category": "Groceries",
    }).status_code == 201
    conversation = client.post("/api/v1/conversations").json()
    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"question": "How much did I spend in September 2026 and how does compound interest work?"},
    )
    assert response.status_code == 201
    response_body = response.json()
    message = response_body["assistant_message"]
    assert [section["kind"] for section in message["sections"]] == ["personal_finance", "education"]
    assert message["calculation"]["value"] == "25.00"
    assert message["calculation"] == message["sections"][0]["calculation"]
    assert message["citations"] == message["sections"][1]["citations"]
    assert "Your financial data" in message["content"]
    assert "General education" in message["content"]

    detail = client.get(f"/api/v1/conversations/{conversation['id']}").json()
    saved_answer = detail["messages"][1]
    assert saved_answer["sections"] == message["sections"]
    assert saved_answer["calculation"] == message["calculation"]
    assert saved_answer["citations"] == message["citations"]

def test_combined_assistant_falls_back_to_lexical_education_without_losing_financial_result(monkeypatch):
    from app import main
    from app.db import SessionLocal
    from app.integrations.llm import MockProvider, ProviderError
    from app.models import ModelRun

    provider = MockProvider()
    retrieve_answer = main.answer_knowledge_question

    def fail_database_retrieval(question, db=None, provider=None):
        if db is not None:
            raise ProviderError("vector retrieval unavailable")
        return retrieve_answer(question, db, provider)

    monkeypatch.setattr(main, "get_provider", lambda: provider)
    monkeypatch.setattr(main, "answer_knowledge_question", fail_database_retrieval)
    client = signup(make_client(), "combined-fallback@example.com")
    assert client.post("/api/v1/transactions", json={
        "date": "2026-09-05", "description": "Grocery store", "amount": "25.00",
        "direction": "debit", "category": "Groceries",
    }).status_code == 201
    response = client.post("/api/v1/assistant/query", json={
        "question": "How much did I spend in September 2026 and how does compound interest work?",
    })
    assert response.status_code == 200
    answer = response.json()
    assert answer["mode"] == "combined"
    assert answer["calculation"]["value"] == "25.00"
    assert answer["sections"][0]["kind"] == "personal_finance"
    assert answer["sections"][1]["kind"] == "education"
    assert answer["citations"] == answer["sections"][1]["citations"]
    assert any("optional LLM service was unavailable" in warning for warning in response.json()["warnings"])
    user_id = client.get("/api/v1/auth/me").json()["id"]
    with SessionLocal() as db:
        failed_runs = db.query(ModelRun).filter_by(user_id=user_id, succeeded=False).all()
        assert [run.purpose for run in failed_runs] == ["assistant_retrieval"]

def test_account_deletion_cleans_conversation_history():
    from app.db import SessionLocal
    from app.models import (
        AuthSession, Budget, Conversation, ImportJob, Message, SavingsGoal,
        Transaction, User, UserSettings,
    )

    client = signup(make_client(), "conversation-delete@example.com")
    user_id = client.get("/api/v1/auth/me").json()["id"]
    client.post("/api/v1/transactions", json={
        "date": "2026-09-01", "description": "Groceries", "amount": "200",
        "direction": "debit",
    })
    client.post("/api/v1/budgets", json={
        "category": "Groceries", "amount": "5000", "period_start": "2026-09-01",
    })
    client.post("/api/v1/goals", json={
        "name": "Reserve", "target_amount": "10000", "saved_amount": "1000",
    })
    client.post("/api/v1/imports", files={"file": ("preview.csv", CSV, "text/csv")})
    client.get("/api/v1/settings")
    conversation = client.post("/api/v1/conversations").json()
    client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"question": "How much did I spend in September 2026?"},
    )
    assert client.delete("/api/v1/settings/account").status_code == 204
    with SessionLocal() as db:
        assert db.get(User, user_id) is None
        assert db.query(AuthSession).filter_by(user_id=user_id).count() == 0
        assert db.query(Transaction).filter_by(user_id=user_id).count() == 0
        assert db.query(ImportJob).filter_by(user_id=user_id).count() == 0
        assert db.query(Budget).filter_by(user_id=user_id).count() == 0
        assert db.query(SavingsGoal).filter_by(user_id=user_id).count() == 0
        assert db.get(UserSettings, user_id) is None
        assert db.query(Conversation).filter_by(user_id=user_id).count() == 0
        assert db.query(Message).filter_by(conversation_id=conversation["id"]).count() == 0
    assert client.get("/api/v1/auth/me").status_code == 401

def test_pdf_parser_handles_multiple_bank_layout_fixtures():
    from app.pdf_import import _parse_statement_line

    fixtures = [
        ("01/09/2026 Metro card 250.00 DR", "debit", "250.00"),
        ("02-Sep-2026 Salary credit 50000.00 CR", "credit", "50000.00"),
        ("2026-09-03 Online purchase 1,250.50", "debit", "1250.50"),
        ("04/09/26 Refund merchant -450.00", "credit", "450.00"),
    ]
    for line_number, (line, direction, amount) in enumerate(fixtures, 1):
        row = _parse_statement_line(line, line_number)
        assert row is not None and row["status"] == "ok"
        assert row["direction"] == direction and row["amount"] == amount

def test_pdf_balance_reconciliation_warnings():
    from app.pdf_import import GenericTextAdapter

    matched = GenericTextAdapter().parse(
        "Opening balance: 1000.00\n01/09/2026 Metro fare 10.00 DR\nClosing balance: 990.00"
    )
    mismatched = GenericTextAdapter().parse(
        "Opening balance: 1000.00\n01/09/2026 Metro fare 10.00 DR\nClosing balance: 995.00"
    )
    assert not any("reconciliation difference" in warning for warning in matched[1])
    assert any("reconciliation difference" in warning for warning in mismatched[1])

def test_password_protected_pdf_password_is_not_persisted():
    import pymupdf

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "01/09/2026 Salary deposit 10000.00 CR")
    raw = document.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner-only",
        user_pw="one-time-statement-password",
    )
    document.close()
    client = signup(make_client(), "password-pdf@example.com")
    locked = client.post("/api/v1/imports", files={
        "file": ("locked.pdf", raw, "application/pdf"),
    })
    assert locked.status_code == 422
    imported = client.post(
        "/api/v1/imports",
        data={"password": "one-time-statement-password"},
        files={"file": ("locked.pdf", raw, "application/pdf")},
    )
    assert imported.status_code == 201
    assert "one-time-statement-password" not in imported.text
    assert client.get(f"/api/v1/imports/{imported.json()['id']}/preview").status_code == 200

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
    assert owner.get("/api/v1/settings").json()["bank_connectivity_message"] == "Live bank connections are unavailable in this MVP."
    assert owner.post("/api/v1/settings/export").json()["transactions"][0]["amount"] == "1200.00"
    owner.delete("/api/v1/settings/transactions")
    assert owner.get("/api/v1/analytics/overview").json()["transaction_count"] == 0
    assert other.get("/api/v1/analytics/overview").json()["transaction_count"] == 0
