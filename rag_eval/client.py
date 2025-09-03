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
