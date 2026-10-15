"""Small, transparent local retrieval set for the no-credential demo mode."""
from __future__ import annotations

import re

RBI_EDUCATION = "https://www.rbi.org.in/FinancialEducation/Home.aspx"
DOCUMENTS = [
    {
        "id": "compound-interest",
        "title": "Compound interest: a plain-language guide",
        "topic": "Saving and interest",
        "content": "Compound interest is calculated on the original amount and on interest already added. For example, if interest remains in an account, a later period's interest can be calculated on a slightly larger balance. The result depends on the rate, compounding frequency, fees, taxes and whether the rate changes. This is a general explanation, not a product comparison or return estimate.",
        "source_type": "FinSight-authored educational note",
        "source_url": None,
        "reference_url": RBI_EDUCATION,
        "updated_at": "2026-10-15",
    },
    {
        "id": "budgeting-basics",
        "title": "A practical starting point for budgeting",
        "topic": "Budgeting",
        "content": "A budget is a plan for income and spending over a chosen period. Start with take-home income, list essential and flexible costs, and compare the plan with actual transactions. Leave room for irregular costs and revisit the plan when circumstances change. A budget is a planning tool, not a guarantee that expenses will match estimates.",
        "source_type": "FinSight-authored educational note",
        "source_url": None,
        "reference_url": RBI_EDUCATION,
        "updated_at": "2026-10-15",
    },
    {
        "id": "emergency-fund",
        "title": "Thinking about an emergency fund",
        "topic": "Saving habits",
        "content": "An emergency fund is money set aside for unexpected needs, such as a temporary income interruption or urgent repair. The suitable amount and where to keep it depend on a person's essential costs, income stability, access needs and obligations. Build it gradually if that is practical, and understand access conditions and risks before choosing a financial product.",
        "source_type": "FinSight-authored educational note",
        "source_url": None,
        "reference_url": RBI_EDUCATION,
        "updated_at": "2026-10-15",
    },
    {
        "id": "credit-card-interest",
        "title": "Credit card interest and fees",
        "topic": "Credit",
        "content": "Credit card costs can include interest, late-payment charges and other fees described in the card terms. Paying only a minimum due can leave a balance on which interest may accrue. The exact calculation, grace period and charges depend on the issuer's current terms, so check the statement and official card agreement or contact the issuer before making a decision.",
        "source_type": "FinSight-authored educational note",
        "source_url": None,
        "reference_url": RBI_EDUCATION,
        "updated_at": "2026-10-15",
    },
    {
        "id": "loan-comparison",
        "title": "A checklist for comparing loan offers",
        "topic": "Borrowing",
        "content": "When comparing loan offers, review the interest rate and whether it is fixed or variable, the annual percentage or equivalent disclosed cost, processing and other fees, repayment schedule, late charges, prepayment terms and total amount repayable. Use the lender's written key disclosures and ask a qualified professional when the terms or implications are unclear. This general checklist is not a recommendation to borrow.",
        "source_type": "FinSight-authored educational note",
        "source_url": None,
        "reference_url": RBI_EDUCATION,
        "updated_at": "2026-10-15",
    },
    {
        "id": "digital-safety",
        "title": "Safer digital banking habits",
        "topic": "Fraud awareness",
        "content": "Never share a one-time password, UPI PIN, card PIN or banking password with someone who contacts you. Verify requests through an official channel you find independently, and contact your bank promptly using its official contact details if you suspect unauthorized activity. This educational note does not determine whether a particular transaction is fraud.",
        "source_type": "FinSight-authored educational note",
        "source_url": None,
        "reference_url": RBI_EDUCATION,
        "updated_at": "2026-10-15",
    },
]
STOP_WORDS = {"a", "an", "and", "are", "about", "can", "do", "for", "how", "i", "in", "is", "it", "me", "of", "on", "the", "to", "what", "with", "you"}


def _terms(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", text.casefold()) if len(word) > 2 and word not in STOP_WORDS}


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    query_terms = _terms(query)
    if not query_terms:
        return []
    scored = []
    for document in DOCUMENTS:
        body_terms = _terms(f"{document['title']} {document['topic']} {document['content']}")
        score = len(query_terms & body_terms) / len(query_terms)
        if score >= 0.2:
            scored.append((score, document))
    return [document for _, document in sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]]


def answer_knowledge_question(question: str) -> dict:
    documents = retrieve(question)
    if not documents:
        return {
            "mode": "local_retrieval",
            "answer": "There is not enough evidence in the local financial education library to answer that reliably. Try a budgeting, saving, interest, credit-card, loan-comparison or digital-safety question.",
            "calculation": None,
            "citations": [],
        }
    citations = [
        {
            "id": document["id"],
            "title": document["title"],
            "href": f"/api/v1/knowledge/documents/{document['id']}",
            "source_type": document["source_type"],
            "reference_url": document["reference_url"],
        }
        for document in documents
    ]
    answer = "Based on the retrieved FinSight educational note:\n\n" + "\n\n".join(document["content"] for document in documents)
    answer += "\n\nThis is general education, not individualized financial, legal, tax or investment advice."
    return {"mode": "local_retrieval", "answer": answer, "calculation": None, "citations": citations}


def public_document(document: dict) -> dict:
    return {key: value for key, value in document.items() if key != "content"} | {"content": document["content"]}
