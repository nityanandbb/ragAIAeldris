import json, pandas as pd
from typing import List, Dict

def load_seed_docs(path="data/seed_docs.json") -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_gold(path="data/gold.csv") -> pd.DataFrame:
    return pd.read_csv(path).fillna("")
