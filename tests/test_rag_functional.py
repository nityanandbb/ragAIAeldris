# tests/test_rag_functional.py
import uuid, time, pytest
from rag_eval.client import RagClient

@pytest.mark.order(1)
def test_ingest_and_query_roundtrip(client: RagClient):
    uniq = str(uuid.uuid4())[:8]
    fact = f"The capital of India is New Delhi. [seed:{uniq}]"
    r = client.ingest([{"id": f"doc-{uniq}", "text": fact}])
    assert r.status_code in (200, 201, 202)

    # eventual consistency window
    for _ in range(10):
        ans, ctxs, raw = client.query("What is the capital of India?")
        joined = " ".join(ctxs)
        if "New Delhi" in ans or "New Delhi" in joined:
            return
        time.sleep(1)
    pytest.fail("Seeded fact not retrieved in answer or contexts")

def test_query_schema_and_edges(client: RagClient):
    ans, ctxs, raw = client.query("Ping?")
    assert isinstance(ans, str) and isinstance(ctxs, list)

def test_bad_ingest_validation(client: RagClient):
    r = client.ingest([{"id": "missing-text"}])
    assert r.status_code in (400, 422), f"Expected 400/422, got {r.status_code}"
