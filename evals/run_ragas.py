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
