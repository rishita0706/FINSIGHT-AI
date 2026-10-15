from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.knowledge import DOCUMENTS

def main() -> None:
    print(f"Validated {len(DOCUMENTS)} bundled FinSight-authored education notes.")
    print("Retrieval is local lexical term-overlap; no source content is downloaded at runtime.")
    for document in DOCUMENTS:
        if document["reference_url"] and not document["reference_url"].startswith("https://"):
            raise SystemExit(f"Invalid reference URL in {document['id']}")
    print("All reference links use HTTPS. Verify publisher content before relying on it.")

if __name__ == "__main__":
    main()
