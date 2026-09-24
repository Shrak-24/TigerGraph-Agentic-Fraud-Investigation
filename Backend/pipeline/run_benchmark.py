"""Run the agent against the 20-case benchmark contract.

With ``--triggers-file`` this accepts the real benchmark trigger file. Without
one it generates deterministic mock triggers so the complete submission flow
can be tested before the HHGOA dataset is available.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent import CaseMemory, FraudInvestigationAgent, MockGraphTools  # noqa: E402

SCHEMA = REPO_ROOT / "CASE_RECORD_SCHEMA.json"


def mock_triggers(count: int) -> list[dict[str, Any]]:
    triggers = []
    for number in range(1, count + 1):
        benchmark_id = f"benchmark-{number:02d}"
        if number % 3 == 1:
            triggers.append({"type": "fraud_signal", "risk_score": .95 if number % 2 else .87, "reason": "benchmark velocity and device anomaly", "customer_id": "cust-1001", "transaction_id": f"tx-benchmark-{number:04d}", "benchmark_case_id": benchmark_id})
        elif number % 3 == 2:
            triggers.append({"type": "customer_report", "customer_id": f"cust-benchmark-{number:04d}", "description": "Customer reports an unrecognized transaction.", "reported_date": "2026-09-24", "benchmark_case_id": benchmark_id})
        else:
            triggers.append({"type": "analyst_request", "analyst_id": "analyst-benchmark", "customer_id": "cust-1001", "description": "Review connected accounts and prior cases.", "benchmark_case_id": benchmark_id})
    return triggers


def validate_case(case: dict[str, Any]) -> None:
    try:
        import jsonschema
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(case, schema)
    except ImportError:
        required = json.loads(SCHEMA.read_text(encoding="utf-8"))["required"]
        missing = [key for key in required if key not in case]
        if missing:
            raise ValueError(f"{case.get('case_id', '<unknown>')} missing fields: {missing}")
    if not 0 <= case["uncertainty"]["risk_score"] <= 1:
        raise ValueError(f"{case['case_id']} has invalid risk score")
    if not 0 <= case["uncertainty"]["confidence"] <= 1:
        raise ValueError(f"{case['case_id']} has invalid confidence")


def load_triggers(path: Path | None, count: int) -> list[dict[str, Any]]:
    if not path:
        return mock_triggers(count)
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, dict):
        value = value.get("triggers", value.get("cases", []))
    if not isinstance(value, list):
        raise ValueError("triggers file must contain a JSON array or a {triggers: [...]} object")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate validated HHGOA case outputs")
    parser.add_argument("--output-dir", default=str(BACKEND_ROOT / "outputs" / "benchmark"))
    parser.add_argument("--cases", type=int, default=20)
    parser.add_argument("--triggers-file", type=Path, help="JSON array of real benchmark triggers")
    args = parser.parse_args()
    if args.cases < 1:
        raise ValueError("--cases must be positive")

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    graph = MockGraphTools()
    agent = FraudInvestigationAgent(graph_tools=graph, memory=CaseMemory(), evidence_wait_seconds=0)
    triggers = load_triggers(args.triggers_file, args.cases)
    manifest: dict[str, Any] = {"mode": "real_triggers" if args.triggers_file else "mock", "case_count": len(triggers), "cases": []}

    for number, trigger in enumerate(triggers, start=1):
        trigger = {**trigger, "benchmark_case_id": trigger.get("benchmark_case_id", f"benchmark-{number:02d}")}
        case = agent.investigate(trigger)
        validate_case(case)
        path = output / f"{case['benchmark_case_id']}.json"
        path.write_text(json.dumps(case, indent=2, default=str) + "\n", encoding="utf-8")
        manifest["cases"].append({"benchmark_case_id": case["benchmark_case_id"], "answer_file": path.name, "status": case["status"], "recommended_actions": [action["action"] for action in case["actions"]], "sar_status": case.get("sar", {}).get("status"), "graph_write_status": case.get("graph_refs", {}).get("case_write", {}).get("status")})

    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(triggers)} validated cases in {output}")


if __name__ == "__main__":
    main()
