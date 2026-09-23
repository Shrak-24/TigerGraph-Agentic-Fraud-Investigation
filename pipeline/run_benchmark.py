"""Dummy HHGOA benchmark pipeline.

This is the Person 3 integration scaffold. It creates 20 deterministic sample
case records from fixtures/sample-case.json, validates the required shape, and
writes one answer file per benchmark case plus a manifest. Replace
make_dummy_case() with the real agent invocation during integration.
"""
import argparse, copy, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts" / "case-record.schema.json"
SAMPLE = ROOT / "fixtures" / "sample-case.json"

def make_dummy_case(template, n):
    case = copy.deepcopy(template)
    case_id = f"case-benchmark-{n:02d}"
    case["case_id"] = case_id
    case["benchmark_case_id"] = f"benchmark-{n:02d}"
    case["trigger"]["transaction_ids"] = [f"tx-benchmark-{n:04d}"]
    case["subject"]["account_id"] = f"acct-benchmark-{n:04d}"
    case["subject"]["customer_id"] = f"cust-benchmark-{n:04d}"
    for ev in case["evidence"]:
        ev["evidence_id"] = f"{ev['evidence_id']}-{n:02d}"
    case["graph_refs"]["entity_ids"] = {"accounts": [case["subject"]["account_id"]], "transactions": case["trigger"]["transaction_ids"], "devices": [f"dev-benchmark-{n:04d}"]}
    return case

def validate_shape(case):
    required = json.loads(SCHEMA.read_text(encoding="utf-8"))["required"]
    missing = [key for key in required if key not in case]
    if missing:
        raise ValueError(f"{case.get('case_id', '<unknown>')} missing fields: {missing}")
    if not 0 <= case["uncertainty"]["risk_score"] <= 1:
        raise ValueError(f"{case['case_id']} has invalid risk score")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--output-dir", default=str(ROOT / "outputs" / "benchmark")); ap.add_argument("--cases", type=int, default=20)
    args = ap.parse_args(); output = Path(args.output_dir); output.mkdir(parents=True, exist_ok=True)
    template = json.loads(SAMPLE.read_text(encoding="utf-8")); manifest = {"mode": "dummy", "case_count": args.cases, "cases": []}
    for n in range(1, args.cases + 1):
        case = make_dummy_case(template, n); validate_shape(case)
        path = output / f"{case['benchmark_case_id']}.json"; path.write_text(json.dumps(case, indent=2) + "\n", encoding="utf-8")
        manifest["cases"].append({"benchmark_case_id": case["benchmark_case_id"], "answer_file": path.name, "status": case["status"], "recommended_action": case["actions"][0]["action"]})
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {args.cases} dummy cases in {output}")

if __name__ == "__main__": main()
