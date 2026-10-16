# Knowledge retrieval pipeline

## Sources and ingestion

The bundled corpus consists of FinSight-authored educational summaries, not copied regulator text. Each answer cites its internal document and links to the Reserve Bank of India's Financial Education landing page as further reading. That HTTPS URL was checked and returned the RBI financial-education portal on 2026-10-15; it does not imply RBI authorship or endorsement of the summaries.

Run `python scripts/ingest_knowledge_base.py` from the repository root to refresh the bundled notes into the configured database. A JSON manifest can additionally ingest local text/HTML/PDF files, inline UTF-8 text, or HTTPS source URLs:

```json
[
  {
    "id": "rbi-financial-education-home",
    "title": "RBI Financial Education Portal",
    "topic": "Financial education",
    "source_type": "official HTML",
    "source_url": "https://www.rbi.org.in/FinancialEducation/Home.aspx",
    "reference_url": "https://www.rbi.org.in/FinancialEducation/Home.aspx",
    "version": "2026-10-15"
  }
]
```

Use `python scripts/ingest_knowledge_base.py --manifest path/to/manifest.json`. URLs must be HTTPS; downloads have a 10-second timeout and a 2 MB limit, and redirects must remain on the original host. Source text is extracted from HTML, selectable-text PDF, or UTF-8 text. Ingestion hashes content, versions documents, creates deterministic bounded chunks and provider embeddings, and replaces prior chunks for a changed document rather than adding duplicates.

## Retrieval and citations

The configured provider embeds documents and queries to 1536 dimensions. PostgreSQL ranks by pgvector cosine distance, keeps top-k chunks under the configured relevance threshold (distance <= 0.9), and deduplicates by source document. Local SQLite uses a transparent lexical fallback because SQLite does not support pgvector queries. User transaction records are never included in the education corpus.

Personal finance questions use separate fixed calculations and are not answerable from the knowledge corpus. The assistant returns calculations/citations as structured fields and abstains when no retrieved note meets the threshold. The LLM provider receives only a verified answer for phrasing; it cannot issue SQL or modify calculation/citation fields.

## Evaluation

`python scripts/evaluate_rag.py` reports Recall@3, MRR, citation-source membership, and abstention on the fixed synthetic evaluation cases. Set `RAG_USE_DATABASE=true` with a migrated pgvector database to measure the vector path; otherwise it reports the lexical fallback. These small hand-authored cases are regression checks, not an independent semantic relevance or answer-faithfulness certification.
