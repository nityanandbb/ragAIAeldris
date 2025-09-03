# Seed deterministic docs before tests / k6 / promptfoo
from rag_eval.client import RagClient
from rag_eval.datasets import load_seed_docs

if __name__ == "__main__":
    rc = RagClient()
    docs = load_seed_docs()
    r = rc.ingest(docs)
    print("Seed status:", r.status_code, r.text[:200])
    r.raise_for_status()
