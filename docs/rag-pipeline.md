# Knowledge retrieval pipeline

## Current demo implementation

`backend/app/knowledge.py` contains a bounded set of short FinSight-authored financial education notes. Queries are normalized to lowercase alphanumeric terms; stop words are removed; a simple overlap score ranks notes; only scores at or above a threshold are returned. The assistant repeats the retrieved note text and returns an internal document ID/title plus a separate RBI financial-education further-reading link. If nothing meets the threshold, it abstains.

Notes are not downloaded from RBI and are not attributed to RBI. The RBI page is an externally verified educational landing page, not the source text for each authored note. Documents are static application content and do not contain user transaction data.

## Evaluation and limitations

The five-query synthetic evaluation reports Recall@3, MRR, citation ID membership, and whether the unanswerable question abstains. The evaluation is small and deterministic; it does not measure semantic relevance or independently establish answer faithfulness.

There is no document ingestion/download refresh, chunking pipeline, sentence embedding, vector schema, pgvector query, hybrid retrieval, LLM generation, or prompt provider in this MVP. `scripts/ingest_knowledge_base.py` validates the bundled content/reference URL scheme only. Do not describe this implementation as semantic or vector RAG.

## Extension path

For a future production-oriented implementation, add licensed source manifests, page/version metadata, bounded HTML/PDF extraction, deterministic chunking, pgvector migrations, a configurable embedding provider, refresh/idempotency tests, relevance thresholds, source permissions, adversarial document tests, and independently reviewed citation/faithfulness evaluation. Keep transaction calculations outside the generation pipeline.
