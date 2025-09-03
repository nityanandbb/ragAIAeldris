# tests/test_contract.py
import schemathesis, requests, os
from schemathesis import DataGenerationMethod
from rag_eval.settings import settings

s = settings()
SCHEMA_URI = f"{s.base_url}{s.openapi_path}"

schema = schemathesis.from_uri(
    SCHEMA_URI,
    data_generation_methods=[DataGenerationMethod.positive]
)

def test_openapi_available():
    r = requests.get(SCHEMA_URI, timeout=s.timeout_s)
    assert r.status_code == 200, f"/openapi.json not accessible: {r.status_code}"

@schema.parametrize(filter_endpoint=lambda ep: ep.path in (s.ingest_path, s.query_path))
def test_api_contract(case):
    # auth header handled by server if needed; can inject here if required
    if s.token:
        case.headers["Authorization"] = f"Bearer {s.token}"
    case.headers["Content-Type"] = "application/json"
    response = case.call()
    case.validate_response(response)
