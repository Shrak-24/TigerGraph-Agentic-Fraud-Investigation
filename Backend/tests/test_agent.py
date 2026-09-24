from __future__ import annotations

import json
import unittest
from pathlib import Path

from agent import CaseMemory, FraudInvestigationAgent, MockGraphTools, TigerGraphMCPGraphTools


ROOT = Path(__file__).resolve().parents[2]


class FraudAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = MockGraphTools()
        self.agent = FraudInvestigationAgent(graph_tools=self.graph, memory=CaseMemory(), evidence_wait_seconds=0)

    def test_all_supported_trigger_types(self) -> None:
        triggers = [
            {"type": "fraud_signal", "risk_score": .87, "reason": "velocity", "customer_id": "cust-1001", "transaction_id": "tx-test-signal"},
            {"type": "customer_report", "customer_id": "cust-test-report", "description": "unrecognized activity", "reported_date": "2026-09-24"},
            {"type": "analyst_request", "analyst_id": "analyst-1", "customer_id": "cust-test-analyst", "description": "review activity"},
        ]
        for trigger in triggers:
            with self.subTest(trigger=trigger["type"]):
                case = self.agent.investigate(trigger)
                self.assertEqual(case["trigger"]["type"], trigger["type"])
                self.assertIn(case["status"], {"needs_evidence", "escalated"})
                self.assertEqual(case["graph_refs"]["case_write"]["status"], "written")

    def test_high_risk_case_creates_sar_draft_and_gated_actions(self) -> None:
        case = self.agent.investigate({"type": "fraud_signal", "risk_score": .95, "reason": "high risk", "customer_id": "cust-1001", "transaction_id": "tx-sar"})
        self.assertEqual(case["status"], "escalated")
        self.assertTrue(case["sar"]["required"])
        self.assertEqual(case["sar"]["status"], "pending_approval")
        self.assertIn("SAR DRAFT", case["sar"]["report"])
        self.assertTrue(all(action["status"] == "pending_approval" for action in case["actions"] if action["mode"] == "recommend"))

    def test_low_signal_case_is_bounded_and_records_before_after_steps(self) -> None:
        case = self.agent.investigate({"type": "customer_report", "customer_id": "cust-low-signal", "description": "I am unsure about a transaction", "reported_date": "2026-09-24"})
        self.assertEqual(case["status"], "needs_evidence")
        self.assertFalse(case["uncertainty"]["enough_evidence_to_act"])
        self.assertLessEqual(len(case["uncertainty"]["assessment_history"]), 3)
        self.assertTrue(any(decision["stage"] == "before_additional_evidence" for decision in case["decisions"]))
        self.assertTrue(any(decision["stage"] == "after_additional_evidence" for decision in case["decisions"]))
        self.assertEqual(sum(action["mode"] == "request_evidence" for action in case["actions"]), 2)

    def test_memory_retrieves_previous_case(self) -> None:
        first = self.agent.investigate({"type": "customer_report", "customer_id": "cust-memory", "description": "possible fraud", "reported_date": "2026-09-24"})
        second = self.agent.investigate({"type": "analyst_request", "analyst_id": "analyst-2", "customer_id": "cust-memory", "description": "follow up"})
        self.assertIn(first["case_id"], second["memory"]["similar_cases"])

    def test_invalid_trigger_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.agent.investigate({"type": "unknown", "customer_id": "cust-1"})
        with self.assertRaises(ValueError):
            self.agent.investigate({"type": "fraud_signal", "customer_id": "cust-1"})

    def test_case_matches_canonical_schema(self) -> None:
        import jsonschema
        schema = json.loads((ROOT / "CASE_RECORD_SCHEMA.json").read_text(encoding="utf-8"))
        case = self.agent.investigate({"type": "fraud_signal", "risk_score": .95, "reason": "test", "customer_id": "cust-1001", "transaction_id": "tx-schema"})
        jsonschema.validate(case, schema)


class AdapterTests(unittest.TestCase):
    def test_adapter_maps_read_and_write_calls(self) -> None:
        calls = []

        def invoke(name, request):
            calls.append((name, request))
            if name == "get_transaction_context":
                return {"transactions": [{"transaction_id": request["tx_id"], "amount": 100, "model_risk_score": .9, "device_id": "dev-1"}]}
            if name == "find_connected_accounts":
                return {"accounts": [{"account_id": "acct-2"}], "shared_devices": ["dev-1"], "shared_identities": ["id-1"]}
            if name == "link_device_identity":
                return {"accounts": [{"account_id": "acct-2"}], "identities": []}
            if name == "find_prior_cases":
                return {"cases": [{"case_id": "prior-1", "outcome": "confirmed_fraud"}]}
            return {"case_id": request["case"]["case_id"], "status": "written", "graph": "HHGOA_FRAUD"}

        adapter = TigerGraphMCPGraphTools(invoke, lambda customer_id: "acct-1", lambda customer_id, days: ["tx-1"], [{"pattern_id": "mule_ring"}])
        self.assertEqual(adapter.query_transactions("cust-1")["summary"]["count"], 1)
        self.assertEqual(adapter.query_connected_accounts("cust-1")["connection_types"], ["shared_device", "shared_identity"])
        self.assertEqual(adapter.query_prior_cases("cust-1")["cases"][0]["case_id"], "prior-1")
        self.assertEqual(adapter.write_case({"case_id": "case-1"})["status"], "written")
        self.assertEqual(len(calls), 4)


if __name__ == "__main__":
    unittest.main()
