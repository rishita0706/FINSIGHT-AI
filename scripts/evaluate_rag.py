from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.knowledge import answer_knowledge_question, refresh_knowledge_base, retrieve, retrieve_from_db

def main() -> None:
    cases = json.loads((ROOT / "data" / "synthetic" / "rag_evaluation.json").read_text(encoding="utf-8"))
    use_database = os.getenv("RAG_USE_DATABASE", "").casefold() == "true"
    db = None
    if use_database:
        from app.db import SessionLocal
        from app.integrations.llm import get_provider

        db = SessionLocal()
        refresh_knowledge_base(db, get_provider())
    recall, reciprocal_rank, citation_correct = [], [], []
    abstentions = []
    for case in cases:
        documents = (
            retrieve_from_db(case["question"], db, top_k=3)
            if db is not None
            else retrieve(case["question"], top_k=3)
        )
        expected = case["expected_document"]
        ids = [document["id"] for document in documents]
        recall.append(float(expected is None or expected in ids))
        rank = ids.index(expected) + 1 if expected in ids else 0
        reciprocal_rank.append(1 / rank if rank else 0)
        response = answer_knowledge_question(case["question"], db)
        citations = {citation["id"] for citation in response["citations"]}
        citation_correct.append(float(citations.issubset(set(ids))))
        if expected is None:
            abstentions.append(not response["citations"])
    result = {
        "dataset_size": len(cases),
        "recall_at_3": sum(recall) / len(recall),
        "mean_reciprocal_rank": sum(reciprocal_rank) / len(reciprocal_rank),
        "citation_source_membership": sum(citation_correct) / len(citation_correct),
        "insufficient_evidence_abstained": all(abstentions),
        "method": (
            "pgvector cosine-distance retrieval with a 0.10 cosine-similarity threshold and document deduplication."
            if use_database
            else "Deterministic lexical fallback with a 0.20 overlap threshold and document-level deduplication."
        ),
        "limitations": "Small hand-authored evaluation; no independent semantic relevance or answer-faithfulness judge.",
    }
    if db is not None:
        db.close()
    print(json.dumps(result, indent=2))
    if (
        result["recall_at_3"] < 0.8
        or result["citation_source_membership"] < 1
        or not result["insufficient_evidence_abstained"]
    ):
        raise SystemExit("RAG evaluation fell below its recall/citation/abstention regression thresholds")

if __name__ == "__main__":
    main()
