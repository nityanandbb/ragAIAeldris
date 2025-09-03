# Welcome.


### 🔑 Root files
- **`.env.example`** → Sample env vars (safe to share). Copy to `.env` for local dev.  
- **`Makefile`** → One-line shortcuts (`make test`, `make ragas`, `make all`).  

### ⚙️ Config
- **`config/`** → Centralized environment configs.  
  - `base.yaml` → shared defaults  
  - `dev.yaml`, `stage.yaml`, `prod.yaml` → environment-specific overrides  

### 📊 Data
- **`data/`** → Deterministic fixtures for tests & evals.  
  - `gold.csv` → ground truth Q&A for ragas/regression  
  - `seed_docs.json` → canonical docs seeded before tests  

### 🛠 Reusable Library
- **`rag_eval/`** → Shared Python package (so tests/scripts don’t duplicate code).  
  - `settings.py` → loads config/env overlays  
  - `client.py` → API client for `/ingest` + `/query`  
  - `datasets.py` → loaders for `gold.csv` / `seed_docs.json`  
  - `utils.py` → generic helpers (retry, etc.)  

### 📜 Scripts
- **`scripts/`** → Ops utilities for CI/CD and local setup.  
  - `seed.py` → seeds docs into API  
  - `wait_for_healthy.sh` → waits for API health before running tests  

### ✅ Tests
- **`tests/`** → Pytest-based contract + functional checks.  
  - `conftest.py` → shared fixtures (client, seeding)  
  - `test_contract.py` → Schemathesis contract tests  
  - `test_rag_functional.py` → RAG ingest/query roundtrip, schema validation, negatives  

### ⚡ Performance
- **`k6/`** → Load/perf testing.  
  - `helpers.js` → reusable k6 helpers  
  - `script.js` → load test script with latency thresholds  

### 📈 RAG Quality
- **`evals/`** → RAGAS evaluation pipeline.  
  - `run_ragas.py` → runs faithfulness, answer relevancy, context precision/recall  

### 🔍 Regression
- **`promptfooconfig.yaml`** → Promptfoo regression checks; enforces governance rules like `/openapi.json` and `Authorization: Bearer`.  

### 🤖 CI/CD
- **`.github/workflows/ci.yaml`** → Example GitHub Actions pipeline: seeds, runs tests, load, ragas, promptfoo, uploads metrics.  

---

## Usage Quickstart

```bash
# 1. Copy env template
cp .env.example .env

# 2. Seed deterministic docs
make seed

# 3. Run contract + functional tests
make test

# 4. Run k6 performance test
make k6

# 5. Run ragas evaluation
make ragas

# 6. Run promptfoo regression checks
make promptfoo

Perfect 👍 — badges make your repo look “production-grade” on GitHub.
Here’s an updated **README.md snippet** with **setup instructions** + **badges** you can copy:

````markdown
# 📂 RAG Eval Framework

[![CI](https://github.com/<your-org>/<your-repo>/actions/workflows/ci.yaml/badge.svg)](https://github.com/<your-org>/<your-repo>/actions/workflows/ci.yaml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-18%2B-green.svg)](https://nodejs.org/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#)
[![Coverage](https://img.shields.io/badge/coverage-90%25%2B-brightgreen.svg)](#)
[![Perf](https://img.shields.io/badge/p95%20latency-%3C1.2s-orange.svg)](#)
[![RAG Quality](https://img.shields.io/badge/ragas-faithfulness%20≥0.8%20%7C%20relevancy%20≥0.85%20%7C%20precision%20%2F%20recall%20≥0.7-blueviolet.svg)](#)

A **reusable testing & evaluation framework** for Retrieval-Augmented Generation (RAG) APIs.  
It covers **contract testing, functional testing, performance (k6), RAG quality (ragas), and regression checks (promptfoo)** with environment-aware configs.

---

## 🚀 Setup

```bash
# Create a Python virtual environment
python -m venv .venv && source .venv/bin/activate   # (Windows: .venv\Scripts\activate)

# Upgrade pip
pip install -U pip

# Install Python dependencies
pip install -U pytest requests schemathesis hypothesis pyyaml
pip install "ragas>=0.1.9" "openai>=1.30" "pydantic<3" "pandas>=2" "pyarrow" "tqdm" "datasets>=2.19"

# Install Node.js dependencies for regression checks
npm init -y && npm i -D promptfoo promptfoo-provider-http

# Install k6 (choose one)
brew install k6   # macOS
# OR
curl -s https://raw.githubusercontent.com/grafana/k6/master/scripts/install.sh | bash  # Linux
````

---

## ✅ Features

* **Contract tests** with Schemathesis against `/openapi.json`
* **Functional tests** for ingest/query workflows & edge cases
* **Performance tests** (k6, enforce p95 ≤ 1.2s)
* **RAG quality eval** with ragas (faithfulness, answer relevancy, precision/recall)
* **Regression checks** via promptfoo (governance: `/openapi.json`, `Authorization: Bearer`)
* **Environment configs** (`dev`, `stage`, `prod`) with YAML overlays
* **CI/CD ready** with GitHub Actions (`.github/workflows/ci.yaml`)

---

## 🧪 Quickstart

```bash
# 1. Copy env template
cp .env.example .env

# 2. Seed deterministic docs
make seed

# 3. Run contract + functional tests
make test

# 4. Run k6 performance test
make k6

# 5. Run ragas evaluation
make ragas

# 6. Run promptfoo regression checks
make promptfoo
```

---

## 📊 Thresholds (CI Gates)

* **Faithfulness** ≥ 0.80
* **Answer Relevancy** ≥ 0.85
* **Context Precision/Recall** ≥ 0.70
* **Performance**: p95 latency ≤ 1.2s

---

## 🏗 Repo Structure

(see [Project Structure](#) section above for details)

---

## 🔒 Secrets

* `API_BASE_URL` → your API endpoint
* `RAG_API_TOKEN` → (optional) bearer token
* `OPENAI_API_KEY` → required for ragas metrics

```

---

✨ With these badges:  
- CI → shows workflow status.  
- Coverage/Tests → you can hook to Codecov or pytest-cov.  
- Perf & RAG Quality → static shields (you can auto-update if you publish metrics).  

Would you like me to also **add pytest-cov + Codecov integration** so the **coverage badge updates automatically** instead of being static?
```
