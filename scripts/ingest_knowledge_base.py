"""Ingest bundled notes or a JSON manifest into the configured SQL/pgvector database."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{(ROOT / 'backend' / 'finsight.db').as_posix()}",
)

from app.db import SessionLocal
from app.integrations.llm import get_provider
from app.knowledge import (
    MAX_SOURCE_BYTES,
    extract_document_text,
    ingest_documents,
    refresh_knowledge_base,
)

def fetch_source(url: str) -> tuple[bytes, str]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"Only absolute HTTPS source URLs are accepted: {url}")
    request = Request(url, headers={"User-Agent": "FinSightKnowledgeIngest/1.0"})
    try:
        with urlopen(request, timeout=10) as response:
            final_url = urlparse(response.geturl())
            if final_url.scheme != "https" or final_url.hostname != parsed.hostname:
                raise ValueError("Knowledge source redirected away from its verified HTTPS host")
            raw = response.read(MAX_SOURCE_BYTES + 1)
            if len(raw) > MAX_SOURCE_BYTES:
                raise ValueError("Knowledge source exceeds the 2 MB ingestion limit")
            return raw, response.headers.get_content_type()
    except URLError as exc:
        raise ValueError(f"Could not verify knowledge source URL: {url}") from exc


def documents_from_manifest(path: Path) -> list[dict]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, list):
        raise ValueError("The knowledge manifest must be a JSON array")
    documents = []
    for entry in manifest:
        if not isinstance(entry, dict):
            raise ValueError("Each knowledge manifest item must be a JSON object")
        if entry.get("path"):
            source_path = (path.parent / entry["path"]).resolve()
            if not source_path.is_file():
                raise ValueError(f"Knowledge source file does not exist: {source_path}")
            if source_path.stat().st_size > MAX_SOURCE_BYTES:
                raise ValueError(f"Knowledge source exceeds the {MAX_SOURCE_BYTES // 1_000_000} MB limit")
            raw = source_path.read_bytes()
            content_type = mimetypes.guess_type(source_path.name)[0] or "text/plain"
        elif entry.get("source_url"):
            raw, content_type = fetch_source(entry["source_url"])
        elif isinstance(entry.get("content"), str):
            raw = entry["content"].encode("utf-8")
            content_type = "text/plain"
        else:
            raise ValueError("Each manifest item needs path, source_url, or inline content")
        documents.append({
            **entry,
            "content": extract_document_text(raw, content_type),
            "source_type": entry.get("source_type", content_type),
        })
    return documents


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, help="JSON manifest for local or HTTPS HTML/PDF/text sources")
    args = parser.parse_args()
    provider = get_provider()
    with SessionLocal() as db:
        if args.manifest:
            documents = documents_from_manifest(args.manifest)
            for url in {item["reference_url"] for item in documents}:
                fetch_source(url)
            count = ingest_documents(db, documents, provider)
        else:
            from app.knowledge import DOCUMENTS

            for url in {item["reference_url"] for item in DOCUMENTS}:
                fetch_source(url)
            count = refresh_knowledge_base(db, provider)
    print(f"Knowledge base refreshed: {count} document version(s) updated.")


if __name__ == "__main__":
    main()
