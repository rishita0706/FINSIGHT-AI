from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.knowledge import answer_knowledge_question, retrieve

def main() -> None:
    cases = json.loads((ROOT / "data" / "synthetic" / "rag_evaluation.json").read_text(encoding="utf-8"))
    recall, reciprocal_rank, citation_correct = [], [], []
    abstentions = []
    for case in cases:
        documents = retrieve(case["question"], top_k=3)
        expected = case["expected_document"]
        ids = [document["id"] for document in documents]
        recall.append(float(expected is None or expected in ids))
        rank = ids.index(expected) + 1 if expected in ids else 0
        reciprocal_rank.append(1 / rank if rank else 0)
        response = answer_knowledge_question(case["question"])
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
        "method": "Deterministic lexical term-overlap retrieval; citation correctness checks that emitted IDs were retrieved.",
        "limitations": "Small hand-authored evaluation; no semantic embedding or independent answer-faithfulness judge.",
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
