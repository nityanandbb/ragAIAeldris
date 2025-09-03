import os, pytest
from rag_eval.client import RagClient
from rag_eval.datasets import load_seed_docs

@pytest.fixture(scope="session")
def client():
    return RagClient()

@pytest.fixture(scope="session", autouse=True)
def seed_data(client):
    # Seed once for the test session
    docs = load_seed_docs()
    r = client.ingest(docs)
    assert r.status_code in (200, 201, 202), f"Seed failed: {r.status_code} {r.text}"
