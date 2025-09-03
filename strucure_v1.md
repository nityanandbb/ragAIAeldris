
# Realtime RAG Testing & Evaluation — Reusable Framework

```
rag-eval/
├─ .env.example
├─ Makefile
├─ config/
│  ├─ base.yaml
│  ├─ dev.yaml
│  ├─ stage.yaml
│  └─ prod.yaml
├─ data/
│  ├─ gold.csv
│  └─ seed_docs.json
├─ rag_eval/                      # <— reusable Python package
│  ├─ __init__.py
│  ├─ settings.py
│  ├─ client.py
│  ├─ datasets.py
│  └─ utils.py
├─ scripts/
│  ├─ seed.py
│  └─ wait_for_healthy.sh
├─ tests/
│  ├─ conftest.py
│  ├─ test_contract.py
│  └─ test_rag_functional.py
├─ k6/
│  ├─ helpers.js
│  └─ script.js
├─ evals/
│  └─ run_ragas.py
├─ promptfooconfig.yaml
└─ .github/workflows/ci.yaml      # optional CI sample
```

## 0) Install (one-time)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -U pytest requests schemathesis hypothesis pyyaml
pip install "ragas>=0.1.9" "openai>=1.30" "pydantic<3" "pandas>=2" "pyarrow" "tqdm" "datasets>=2.19"
npm init -y && npm i -D promptfoo promptfoo-provider-http
# k6: brew install k6   OR   curl -s https://raw.githubusercontent.com/grafana/k6/master/scripts/install.sh | bash
```

---

## 1) Environment & Config Layering

### `.env.example`

```ini
# copy to .env and edit
ENV=dev                  # dev | stage | prod
API_BASE_URL=http://52.221.197.158:8000
RAG_API_TOKEN=
OPENAI_API_KEY=sk-...
K6_VUS=100
K6_P95_MS=1200
```

### `config/base.yaml`

```yaml
api:
  base_url: ${API_BASE_URL}
  token: ${RAG_API_TOKEN}
  timeout_s: 30
  openapi_path: /openapi.json
endpoints:
  ingest: /ingest
  query: /query
perf:
  k6:
    vus: ${K6_VUS}
    p95_ms: ${K6_P95_MS}
eval:
  ragas_thresholds:
    faithfulness: 0.80
    answer_relevancy: 0.85
    context_precision: 0.70
    context_recall: 0.70
```

### `config/dev.yaml`

```yaml
api:
  timeout_s: 20
perf:
  k6:
    vus: 50
    p95_ms: 1500
```

### `config/stage.yaml`

```yaml
perf:
  k6:
    vus: 100
    p95_ms: 1200
```

### `config/prod.yaml`

```yaml
perf:
  k6:
    vus: 150
    p95_ms: 1000
```

---

## 2) Shared, Reusable Python Package

### `rag_eval/__init__.py`

```python
__all__ = ["settings", "client", "datasets", "utils"]
```

### `rag_eval/settings.py`

```python
import os, yaml
from dataclasses import dataclass
from functools import lru_cache

def _env(name: str, default: str = ""):
    return os.getenv(name, default)

def _deep_merge(a: dict, b: dict) -> dict:
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            a[k] = _deep_merge(a[k], v)
        else:
            a[k] = v
    return a

@lru_cache()
def load_config():
    env = _env("ENV", "dev")
    base = yaml.safe_load(open("config/base.yaml"))
    overlay_path = f"config/{env}.yaml"
    if os.path.exists(overlay_path):
        overlay = yaml.safe_load(open(overlay_path))
        base = _deep_merge(base, overlay)
    # Expand simple ${ENV_VAR} tokens
    def expand(x):
        if isinstance(x, dict):
            return {k: expand(v) for k, v in x.items()}
        if isinstance(x, list):
            return [expand(i) for i in x]
        if isinstance(x, str) and x.startswith("${") and x.endswith("}"):
            return _env(x[2:-1], "")
        return x
    return expand(base)

@dataclass
class Settings:
    env: str
    base_url: str
    token: str
    timeout_s: int
    openapi_path: str
    ingest_path: str
    query_path: str
    k6_vus: int
    k6_p95_ms: int
    ragas_thresholds: dict

@lru_cache()
def settings() -> Settings:
    c = load_config()
    return Settings(
        env=os.getenv("ENV", "dev"),
        base_url=c["api"]["base_url"],
        token=c["api"]["token"],
        timeout_s=int(c["api"]["timeout_s"]),
        openapi_path=c["api"]["openapi_path"],
        ingest_path=c["endpoints"]["ingest"],
        query_path=c["endpoints"]["query"],
        k6_vus=int(c["perf"]["k6"]["vus"]),
        k6_p95_ms=int(c["perf"]["k6"]["p95_ms"]),
        ragas_thresholds=c["eval"]["ragas_thresholds"],
    )
```

### `rag_eval/client.py`

```python
import requests
from typing import Any, Dict, List, Tuple
from .settings import settings

class RagClient:
    def __init__(self):
        self.s = settings()
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        if self.s.token:
            self._session.headers.update({"Authorization": f"Bearer {self.s.token}"})

    def openapi_url(self) -> str:
        return f"{self.s.base_url}{self.s.openapi_path}"

    def _url(self, path: str) -> str:
        return f"{self.s.base_url}{path}"

    def ingest(self, docs: List[Dict[str, str]]) -> requests.Response:
        return self._session.post(
            self._url(self.s.ingest_path),
            json={"docs": docs},
            timeout=self.s.timeout_s,
        )

    def query(self, question: str) -> Tuple[str, List[str], Dict[str, Any]]:
        r = self._session.post(
            self._url(self.s.query_path),
            json={"question": question},
            timeout=self.s.timeout_s,
        )
        r.raise_for_status()
        j = r.json()
        return j.get("answer", ""), j.get("contexts", []) or [], j
```

### `rag_eval/datasets.py`

```python
import json, pandas as pd
from typing import List, Dict

def load_seed_docs(path="data/seed_docs.json") -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_gold(path="data/gold.csv") -> pd.DataFrame:
    return pd.read_csv(path).fillna("")
```

### `rag_eval/utils.py`

```python
import time

def retry(times=8, delay_s=1.0):
    def deco(fn):
        def wrapped(*a, **kw):
            last = None
            for _ in range(times):
                ok, val = fn(*a, **kw)
                if ok: return val
                last = val
                time.sleep(delay_s)
            return last
        return wrapped
    return deco
```

---

## 3) Data (deterministic tests)

### `data/seed_docs.json`

```json
[
  { "id": "seed-governance", "text": "Use Authorization: Bearer <token>. The OpenAPI spec is at /openapi.json." },
  { "id": "seed-capital",     "text": "The capital of India is New Delhi." },
  { "id": "seed-rag",         "text": "A RAG system retrieves contexts and grounds the generated answer in them." }
]
```

### `data/gold.csv`

```csv
question,ground_truth
Where is the OpenAPI spec URL?,/openapi.json
How do I authenticate to this API?,Authorization: Bearer
What is the capital of India?,New Delhi
What does a RAG system do?,retrieves contexts
```

---

## 4) Scripts (reusable ops)

### `scripts/seed.py`

```python
# Seed deterministic docs before tests / k6 / promptfoo
from rag_eval.client import RagClient
from rag_eval.datasets import load_seed_docs

if __name__ == "__main__":
    rc = RagClient()
    docs = load_seed_docs()
    r = rc.ingest(docs)
    print("Seed status:", r.status_code, r.text[:200])
    r.raise_for_status()
```

### `scripts/wait_for_healthy.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${API_BASE_URL:-http://52.221.197.158:8000}"
until curl -sS "${BASE_URL}/openapi.json" >/dev/null; do
  echo "Waiting for API at ${BASE_URL} ..."
  sleep 2
done
echo "API is reachable."
```

`chmod +x scripts/wait_for_healthy.sh`

---

## 5) Tests — Reusable Fixtures & Contract/Functional

### `tests/conftest.py`

```python
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
```

### ✅ `tests/test_contract.py` (upgraded, still copy-paste ready)

```python
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
```

### ✅ `tests/test_rag_functional.py` (upgraded & modular)

```python
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
```

---

## 6) k6 (reusable helpers + env-driven script)

### `k6/helpers.js`

```javascript
export function authHeaders(token) {
  const h = { 'Content-Type': 'application/json' };
  if (token) h['Authorization'] = `Bearer ${token}`;
  return h;
}

export function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}
```

### ✅ `k6/script.js` (env-aware; still drop-in)

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { authHeaders, pick } from './helpers.js';

const BASE = __ENV.API_BASE_URL || 'http://52.221.197.158:8000';
const TOKEN = __ENV.RAG_API_TOKEN || '';
const P95 = Number(__ENV.K6_P95_MS || 1200);

export const options = {
  stages: [
    { duration: '15s', target: 10 },
    { duration: '45s', target: 50 },
    { duration: '1m', target: Number(__ENV.K6_VUS || 100) },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: [`p(95)<${P95}`],
  },
};

export function setup() {
  const seed = {
    docs: [
      { id: 'k6-1', text: 'Use Authorization: Bearer <token>. The OpenAPI spec is at /openapi.json.' },
      { id: 'k6-2', text: 'The capital of India is New Delhi.' },
      { id: 'k6-3', text: 'RAG retrieves passages (contexts) and grounds answers in them.' }
    ],
  };
  const res = http.post(`${BASE}/ingest`, JSON.stringify(seed), { headers: authHeaders(TOKEN), timeout: '30s' });
  check(res, { 'seed ingest ok': (r) => [200, 201, 202].includes(r.status) });
}

const questions = [
  'Where is the OpenAPI spec URL?',
  'How do I authenticate to this API?',
  'What is the capital of India?',
  'What does a RAG system do?',
];

export default function () {
  const q = pick(questions);
  const res = http.post(`${BASE}/query`, JSON.stringify({ question: q }), { headers: authHeaders(TOKEN), timeout: '30s' });
  check(res, {
    'status 200': (r) => r.status === 200,
    'answer present': (r) => { try { return typeof r.json().answer === 'string'; } catch { return false; } },
    'contexts array': (r) => { try { return Array.isArray(r.json().contexts); } catch { return false; } },
  });
  sleep(1);
}
```

---

## 7) RAG Quality — RAGAS (reusing client + thresholds from config)

### ✅ `evals/run_ragas.py` (upgraded; uses settings)

```python
import os, json, argparse, pandas as pd
from datasets import Dataset
from tqdm import tqdm
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from rag_eval.client import RagClient
from rag_eval.datasets import load_gold
from rag_eval.settings import settings

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", default="data/gold.csv")
    parser.add_argument("--out", default="evals/metrics.json")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY not set; required for RAGAS.")

    cfg = settings()
    rc = RagClient()
    gold = load_gold(args.gold)

    records = []
    for _, row in tqdm(gold.iterrows(), total=len(gold)):
        q = str(row["question"]).strip()
        gt = str(row["ground_truth"]).strip()
        ans, ctxs, _ = rc.query(q)
        records.append({
            "question": q,
            "answer": ans,
            "contexts": ctxs,
            "ground_truth": [gt] if gt else [],
        })

    ds = Dataset.from_pandas(pd.DataFrame(records))
    res = evaluate(ds, metrics=[faithfulness, answer_relevancy, context_precision, context_recall])
    summary = {
        "faithfulness": float(res["faithfulness"].mean()),
        "answer_relevancy": float(res["answer_relevancy"].mean()),
        "context_precision": float(res["context_precision"].mean()),
        "context_recall": float(res["context_recall"].mean()),
        "num_samples": len(records),
    }
    print("RAGAS summary:", json.dumps(summary, indent=2))
    os.makedirs("evals", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"per_sample": res.to_pandas().to_dict(orient="records"), "summary": summary}, f, indent=2)

    thr = cfg.ragas_thresholds
    ok = (
        summary["faithfulness"]     >= thr["faithfulness"] and
        summary["answer_relevancy"] >= thr["answer_relevancy"] and
        summary["context_precision"]>= thr["context_precision"] and
        summary["context_recall"]   >= thr["context_recall"]
    )
    if not ok:
        raise SystemExit(f"❌ RAGAS thresholds not met: {json.dumps(summary)}")
    print("✅ RAGAS thresholds met.")

if __name__ == "__main__":
    main()
```

---

## 8) Promptfoo (regression) — env-ready and seed-compatible

### ✅ `promptfooconfig.yaml`

```yaml
version: 1
providers:
  - id: http
    label: RAG API /query
    config:
      url: "${API_BASE_URL:-http://52.221.197.158:8000}/query"
      method: POST
      headers:
        Content-Type: application/json
        Authorization: "Bearer ${RAG_API_TOKEN}"
      body: |
        {"question":"{{question}}"}
      responsePath: "answer"

prompts:
  - "{{question}}"

tests:
  - vars: { question: "Where is the OpenAPI spec URL?" }
    assert:
      - type: contains
        value: "/openapi.json"
  - vars: { question: "How do I authenticate to this API?" }
    assert:
      - type: contains
        value: "Authorization: Bearer"
  - vars: { question: "What is the capital of India?" }
    assert:
      - type: contains
        value: "New Delhi"
  - vars: { question: "What does a RAG system do?" }
    assert:
      - type: icontains
        value: "retrieve"
```

---

## 9) Makefile (developer ergonomics)

### `Makefile`

```makefile
include .env
export

PY=python
PIP=pip

.PHONY: seed test contract functional k6 ragas promptfoo all

seed:
	$(PY) scripts/seed.py

contract:
	pytest -q tests/test_contract.py

functional:
	pytest -q tests/test_rag_functional.py

test: contract functional

k6:
	k6 run k6/script.js

ragas:
	$(PY) evals/run_ragas.py --gold data/gold.csv --out evals/metrics.json

promptfoo:
	npx promptfoo eval

all: seed test k6 ragas promptfoo
```

---

## 10) Optional CI (GitHub Actions, single job example)

### `.github/workflows/ci.yaml`

```yaml
name: RAG Eval CI
on: [push, workflow_dispatch]
jobs:
  rag-eval:
    runs-on: ubuntu-latest
    env:
      ENV: dev
      API_BASE_URL: ${{ secrets.API_BASE_URL }}
      RAG_API_TOKEN: ${{ secrets.RAG_API_TOKEN }}
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      K6_VUS: 80
      K6_P95_MS: 1200
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - name: Install deps
        run: |
          python -m pip install -U pip
          pip install -U pytest requests schemathesis hypothesis pyyaml ragas "openai>=1.30" "pydantic<3" pandas pyarrow tqdm datasets
      - name: Seed corpus
        run: python scripts/seed.py
      - name: Contract tests
        run: pytest -q tests/test_contract.py
      - name: Functional tests
        run: pytest -q tests/test_rag_functional.py
      - name: Install k6
        run: |
          curl -s https://raw.githubusercontent.com/grafana/k6/master/scripts/install.sh | bash
      - name: k6 smoke (short)
        run: K6_VUS=30 k6 run k6/script.js
      - name: Node + promptfoo
        uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm i -D promptfoo promptfoo-provider-http
      - name: Promptfoo checks
        run: npx promptfoo eval
      - name: RAGAS metrics
        run: python evals/run_ragas.py --gold data/gold.csv --out evals/metrics.json
      - uses: actions/upload-artifact@v4
        with:
          name: rag-metrics
          path: evals/metrics.json
```

---

## 11) How you actually run (dev, stage, prod)

```bash
# 1) setup .env from .env.example and edit values
cp .env.example .env

# 2) choose environment (affects config overlay)
export ENV=dev   # or stage/prod

# 3) seed + run everything
make all
# Or individual:
make seed
make test
make k6
make ragas
make promptfoo
```

---

## 12) CI Thresholds (baked in)

* **RAG Quality (RAGAS)**

  * Faithfulness ≥ **0.80**
  * Answer relevancy ≥ **0.85**
  * Context precision ≥ **0.70**
  * Context recall ≥ **0.70**

* **Performance (k6)**

  * **p95 ≤ 1.2s** (env-driven; see `config/*`)

* **Contract/Functional**

  * `/openapi.json` reachable (200)
  * `/query` shape `{ answer: string, contexts: string[] }`
  * Ingest → Query round-trip retrieves seeded fact

---

### Why this meets “reusable framework” expectations

* **Separation of concerns**: client, config, datasets, utils are reusable across test, eval, and ops.
* **Env layering**: dev/stage/prod overlays with env-variable interpolation.
* **Deterministic data**: `data/seed_docs.json` and `data/gold.csv` feed all tools.
* **One-liners**: `make all` or pick any target.
* **CI-ready**: Opinionated thresholds, artifacts, and staged jobs.
* **Extensible**: Add more metrics/tests without touching core plumbing.

If req  Playwright/Cypress API assertions, Dockerized k6, or Grafana dashboards wired to k6 output — we can add those next.
