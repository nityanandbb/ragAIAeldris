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
