"""Small, transparent local retrieval set for the no-credential demo mode."""
from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser

import pymupdf
from sqlalchemy import select
from sqlalchemy.orm import Session

from .integrations.llm import Provider, get_provider
from .models import KnowledgeChunk, KnowledgeDocument
RBI_EDUCATION = "https://www.rbi.org.in/FinancialEducation/Home.aspx"
MAX_SOURCE_BYTES = 2_000_000
MAX_SOURCE_CHARS = 2_000_000
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


def chunk_text(text: str, max_chars: int = 1200) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs or [text.strip()]:
        while len(paragraph) > max_chars:
            split_at = paragraph.rfind(" ", 0, max_chars)
            split_at = split_at if split_at > 0 else max_chars
            piece, paragraph = paragraph[:split_at].strip(), paragraph[split_at:].strip()
            if current:
                chunks.append(current)
                current = ""
            chunks.append(piece)
        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append(current)
            current = ""
        current = f"{current}\n\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks


class _TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            text = data.strip()
            if text:
                self.parts.append(text)


def extract_document_text(raw: bytes, content_type: str) -> str:
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("Knowledge source exceeds the 2 MB ingestion limit")
    content_type = content_type.casefold()
    if content_type == "application/pdf" or raw.startswith(b"%PDF-"):
        with pymupdf.open(stream=raw, filetype="pdf") as document:
            if document.page_count > 200:
                raise ValueError("Knowledge PDF exceeds the 200-page ingestion limit")
            return "\n\n".join(page.get_text("text") for page in document)
    if content_type in {"text/html", "application/xhtml+xml"} or b"<html" in raw[:512].lower():
        parser = _TextHTMLParser()
        parser.feed(raw.decode("utf-8", errors="strict"))
        return "\n\n".join(parser.parts)
    return raw.decode("utf-8-sig", errors="strict")


def ingest_documents(
    db: Session,
    documents: list[dict],
    provider: Provider | None = None,
) -> int:
    provider = provider or get_provider()
    count = 0
    for item in documents:
        for key in ("id", "title", "topic", "content", "source_type", "reference_url"):
            if not item.get(key):
                raise ValueError(f"Knowledge document is missing required metadata: {key}")
        for url_key in ("source_url", "reference_url"):
            url = item.get(url_key)
            if url is not None and not url.casefold().startswith("https://"):
                raise ValueError(f"{url_key} must use HTTPS")
        content = item["content"].strip()
        if not content:
            raise ValueError(f"Knowledge document {item['id']} contains no text")
        if len(content) > MAX_SOURCE_CHARS:
            raise ValueError(f"Knowledge document {item['id']} exceeds the 2 MB text limit")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        version = str(item.get("version") or digest[:16])
        document = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.external_id == item["id"]))
        if document and document.content_hash == digest and document.version == version:
            continue
        if document:
            db.delete(document)
            db.flush()
        document = KnowledgeDocument(
            external_id=item["id"],
            title=item["title"],
            topic=item["topic"],
            source_type=item["source_type"],
            source_url=item.get("source_url"),
            reference_url=item["reference_url"],
            version=version,
            content_hash=digest,
            active=True,
        )
        db.add(document)
        db.flush()
        for chunk_index, chunk in enumerate(chunk_text(content)):
            db.add(KnowledgeChunk(
                document_id=document.id,
                version=version,
                chunk_index=chunk_index,
                content=chunk,
                embedding=provider.embed(f"{item['title']} {item['topic']} {chunk}"),
            ))
        count += 1
    db.commit()
    return count


def refresh_knowledge_base(db: Session, provider: Provider | None = None) -> int:
    return ingest_documents(db, DOCUMENTS, provider)


def retrieve_from_db(
    query: str,
    db: Session,
    top_k: int = 3,
    provider: Provider | None = None,
    threshold: float = 0.9,
) -> list[dict]:
    provider = provider or get_provider()
    if db.get_bind().dialect.name != "postgresql":
        return retrieve(query, top_k)
    vector = provider.embed(query)
    if not any(vector):
        return []
    distance = KnowledgeChunk.embedding.op("<=>")(vector).label("distance")
    rows = db.execute(
        select(KnowledgeDocument, KnowledgeChunk, distance)
        .join(KnowledgeChunk, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(KnowledgeDocument.active.is_(True), KnowledgeChunk.version == KnowledgeDocument.version)
        .order_by(distance)
        .limit(top_k * 4)
    ).all()
    documents: list[dict] = []
    seen: set[str] = set()
    for document, chunk, score in rows:
        if score is None or score > threshold or document.external_id in seen:
            continue
        seen.add(document.external_id)
        documents.append({
            "id": document.external_id,
            "title": document.title,
            "topic": document.topic,
            "content": chunk.content,
            "source_type": document.source_type,
            "source_url": document.source_url,
            "reference_url": document.reference_url,
            "updated_at": document.updated_at.date().isoformat(),
            "relevance": 1 - float(score),
        })
        if len(documents) >= top_k:
            break
    return documents


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


def answer_knowledge_question(
    question: str,
    db: Session | None = None,
    provider: Provider | None = None,
) -> dict:
    provider = provider or get_provider()
    if db is None:
        documents = retrieve(question)
    else:
        refresh_knowledge_base(db, provider)
        documents = retrieve_from_db(question, db, provider=provider)
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
