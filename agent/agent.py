"""Evidence-first fraud investigation loop."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .graph_tools import GraphToolInterface, MockGraphTools
from .knowledge import DEFAULT_POLICY, load_fraud_patterns, load_fraud_policy, match_patterns
from .memory import CaseMemory


class FraudInvestigationAgent:
    """Run trigger -> investigate -> assess -> act -> explain -> memory."""

    def __init__(self, graph_tools: GraphToolInterface | None = None, memory: CaseMemory | None = None, policy_path: str | None = None, patterns_path: str | None = None, evidence_wait_seconds: float = .02, evidence_provider: Callable[[dict[str, Any], str], dict[str, Any]] | None = None) -> None:
        self.graph = graph_tools or MockGraphTools()
        self.memory = memory or CaseMemory()
        package_data = Path(__file__).parent / "data"
        self.policy = load_fraud_policy(policy_path or package_data / "fraud_policy.json")
        graph_patterns = self.graph.query_fraud_patterns().get("patterns", [])
        self.patterns = load_fraud_patterns(patterns_path or package_data / "5_known_fraud_patterns.json", fallback=graph_patterns)
        self.evidence_wait_seconds = evidence_wait_seconds
        self.evidence_provider = evidence_provider

    def investigate(self, trigger: dict[str, Any]) -> dict[str, Any]:
        normalized = self._validate_trigger(trigger)
        now = self._now()
        customer_id = normalized["customer_id"]
        existing = self._existing_open_case(customer_id, normalized.get("transaction_id"))
        case_id = existing.get("case_id") if existing else f"case-{uuid.uuid4().hex[:12]}"
        case = self._new_case(case_id, normalized, now, existing)
        evidence: list[dict[str, Any]] = case["evidence"]
        queries: list[str] = case["graph_refs"]["queries_called"]

        transactions = self._call("query_transactions", lambda: self.graph.query_transactions(customer_id, 90), queries)
        connected = self._call("query_connected_accounts", lambda: self.graph.query_connected_accounts(customer_id), queries)
        device_ids = sorted(set(transactions.get("summary", {}).get("unique_devices", [])) | set(connected.get("devices", [])))
        devices = self._call("query_device_signals", lambda: self.graph.query_device_signals(device_ids), queries)
        behavior = self._call("query_account_behavior", lambda: self.graph.query_account_behavior(customer_id), queries)
        prior = self._call("query_prior_cases", lambda: self.graph.query_prior_cases(customer_id), queries)

        self._entity_refs(case, transactions, connected, devices)
        for item in self._graph_evidence(transactions, connected, devices, behavior, prior):
            evidence.append(item)
        similar = self.memory.retrieve(customer_id=customer_id, connected_account_ids=[a.get("account_id", "") for a in connected.get("accounts", [])], device_ids=device_ids)
        graph_similar = [item.get("case_id") for item in prior.get("cases", []) if item.get("case_id")]
        case["memory"]["similar_cases"] = list(dict.fromkeys([item["case_id"] for item in similar] + graph_similar))

        indicators = self._indicators(normalized, transactions, connected, devices, behavior)
        matches = match_patterns({"indicators": indicators}, self.patterns)
        case["memory"]["retrieved_patterns"] = [match["pattern_id"] for match in matches]
        evidence.extend(self._grounding_evidence(matches))
        confidence, contributions = self._score_confidence(transactions, connected, devices, matches, prior, behavior)
        case["findings"] = self._findings(matches, evidence)
        self._record_uncertainty(case, "initial", confidence, contributions)

        if confidence < .8:
            action = self._next_evidence_action(indicators)
            case["actions"].append({"action_id": f"action-{uuid.uuid4().hex[:8]}", "action": action, "mode": "request_evidence", "status": "pending_approval", "approval_route": "fraud_analyst", "reason": "Additional controlled evidence is needed before a consequential action."})
            case["decisions"].append(self._decision("request_more_evidence", "Risk signals are corroborated but uncertainty remains; request controlled validation."))
            case["approval"] = {"required": True, "route": "fraud_analyst", "status": "pending", "approved_by": None}
            follow_up = self._gather_evidence(case, action, normalized)
            evidence.append(follow_up)
            confidence = min(.99, confidence + .15)
            self._record_uncertainty(case, "after_controlled_evidence", confidence, ["controlled_validation_completed"])

        case["uncertainty"]["confidence"] = round(confidence, 2)
        case["uncertainty"]["risk_score"] = normalized.get("risk_score", self._risk_from_transactions(transactions))
        case["uncertainty"]["enough_evidence_to_act"] = confidence >= .8
        case["uncertainty"]["missing_evidence"] = [] if confidence >= .8 else self._missing_evidence(indicators)
        self._decide(case, normalized, confidence, matches, evidence)
        case["updated_at"] = self._now().isoformat()
        case["memory"]["outcome_to_store"] = self._memory_outcome(case)
        case["explanation"] = self._explain(case, matches, contributions)
        self.memory.store(case)
        return case

    run = investigate

    def _validate_trigger(self, trigger: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(trigger, dict) or trigger.get("type") not in {"fraud_signal", "customer_report", "analyst_request"}:
            raise ValueError("trigger.type must be fraud_signal, customer_report, or analyst_request")
        if not trigger.get("customer_id"):
            raise ValueError("trigger.customer_id is required")
        if trigger["type"] == "fraud_signal" and not trigger.get("transaction_id"):
            raise ValueError("fraud_signal.transaction_id is required")
        received_at = trigger.get("received_at", self._now())
        if isinstance(received_at, datetime):
            received_at = received_at.isoformat()
        return {**trigger, "source": trigger.get("source", trigger["type"]), "received_at": received_at}

    def _new_case(self, case_id: str, trigger: dict[str, Any], now: datetime, existing: dict[str, Any] | None) -> dict[str, Any]:
        if existing:
            existing["trigger"] = trigger
            return existing
        return {
            "case_id": case_id, "benchmark_case_id": trigger.get("benchmark_case_id", ""), "status": "open", "created_at": now.isoformat(), "updated_at": now.isoformat(),
            "trigger": trigger, "subject": {"account_id": f"acct-{trigger['customer_id'].removeprefix('cust-')}", "customer_id": trigger["customer_id"]}, "evidence": [], "findings": [],
            "uncertainty": {"risk_score": trigger.get("risk_score", 0), "confidence": .1, "enough_evidence_to_act": False, "missing_evidence": [], "assessment_history": []},
            "decisions": [], "actions": [], "approval": {"required": False, "route": "none", "status": "not_required", "approved_by": None}, "memory": {"similar_cases": [], "retrieved_patterns": [], "outcome_to_store": None},
            "graph_refs": {"queries_called": [], "entity_ids": {"accounts": [], "transactions": [], "devices": [], "identities": []}}, "explanation": "",
        }

    def _call(self, name: str, operation: Callable[[], dict[str, Any]], queries: list[str]) -> dict[str, Any]:
        queries.append(name)
        try:
            return operation()
        except Exception as exc:
            return {"error": str(exc), "transactions": [], "accounts": [], "devices": [], "cases": [], "patterns": []}

    def _graph_evidence(self, transactions: dict[str, Any], connected: dict[str, Any], devices: dict[str, Any], behavior: dict[str, Any], prior: dict[str, Any]) -> list[dict[str, Any]]:
        evidence = []
        if transactions.get("transactions"):
            evidence.append(self._evidence("transaction", "tigergraph.query_transactions", f"{len(transactions['transactions'])} transactions in the last 90 days; {transactions.get('summary', {}).get('high_risk_count', 0)} are high risk.", .96, "query_transactions"))
        if connected.get("connection_types"):
            evidence.append(self._evidence("connected_account", "tigergraph.query_connected_accounts", f"Connected-account traversal found {len(connected.get('accounts', []))} accounts through {', '.join(connected['connection_types'])}.", .84, "query_connected_accounts"))
        if devices.get("velocity", {}).get("spike"):
            evidence.append(self._evidence("device_signal", "tigergraph.query_device_signals", "Device velocity is elevated across multiple accounts in a one-hour window.", .87, "query_device_signals"))
        for anomaly in behavior.get("anomalies", []):
            evidence.append(self._evidence("behavior_baseline", "tigergraph.query_account_behavior", f"Baseline anomaly: {anomaly}.", .80, "query_account_behavior"))
        if prior.get("cases"):
            evidence.append(self._evidence("prior_case", "tigergraph.query_prior_cases", f"{len(prior['cases'])} related prior case(s) were retrieved from case memory.", .82, "query_prior_cases"))
        return evidence

    def _grounding_evidence(self, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        evidence = [self._evidence("policy_grounding", self.policy.get("source", "fraud_policy"), "Assessment grounded against transaction limits, approval gates, SAR rules, and acceptable evidence types.", .9, None)]
        if matches:
            evidence.append(self._evidence("pattern_grounding", "known_fraud_patterns", "Observed indicators were compared with the five-pattern fraud catalog.", .9, None))
        return evidence

    def _score_confidence(self, transactions: dict[str, Any], connected: dict[str, Any], devices: dict[str, Any], matches: list[dict[str, Any]], prior: dict[str, Any], behavior: dict[str, Any]) -> tuple[float, list[str]]:
        score, contributions = .1, []
        if behavior.get("anomalies") or any(tx.get("amount", 0) > behavior.get("baseline", {}).get("p95_amount", float("inf")) for tx in transactions.get("transactions", [])):
            score += .2; contributions.append("transaction_amount_anomaly:+0.20")
        if devices.get("velocity", {}).get("spike"):
            score += .2; contributions.append("device_location_velocity:+0.20")
        if len(connected.get("accounts", [])) > 1:
            score += .2; contributions.append("multiple_connected_accounts:+0.20")
        if matches:
            score += .3; contributions.append("known_fraud_pattern_match:+0.30")
        if prior.get("cases"):
            score += .15; contributions.append("related_prior_case:+0.15")
        return min(.99, score), contributions

    def _decide(self, case: dict[str, Any], trigger: dict[str, Any], confidence: float, matches: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> None:
        risk = case["uncertainty"]["risk_score"]
        if confidence < .8:
            case["status"] = "needs_evidence"
            return
        case["status"] = "escalated"
        high_risk = risk >= self.policy["approval_thresholds"].get("block_transaction", .8)
        actions = [("block_transaction" if high_risk else "monitor_account", "Consequential action remains analyst-controlled after corroborating evidence.")]
        if not high_risk:
            actions.append(("warn_customer", "Customer notification is appropriate while the case remains under review."))
        if risk >= self.policy["sar_rules"].get("minimum_risk_score", .9) and matches:
            actions.append(("file_sar", "Risk and pattern evidence meet the configured SAR review threshold."))
        for action, reason in actions:
            case["actions"].append({"action_id": f"action-{uuid.uuid4().hex[:8]}", "action": action, "mode": "recommend", "status": "pending_approval", "approval_route": "fraud_analyst", "reason": reason})
        case["approval"] = {"required": True, "route": "fraud_analyst", "status": "pending", "approved_by": None}
        case["decisions"].append(self._decision("recommend_controlled_action", f"Confidence {confidence:.2f} is sufficient to recommend controlled action; approval is required by policy."))

    def _gather_evidence(self, case: dict[str, Any], action: str, trigger: dict[str, Any]) -> dict[str, Any]:
        if self.evidence_wait_seconds:
            time.sleep(self.evidence_wait_seconds)
        result = self.evidence_provider(case, action) if self.evidence_provider else {"summary": f"Simulated {action} completed successfully for controlled validation.", "type": "customer_validation"}
        return self._evidence(result.get("type", "customer_validation"), "controlled_action", result.get("summary", "Controlled evidence returned."), .94, None)

    def _indicators(self, trigger: dict[str, Any], transactions: dict[str, Any], connected: dict[str, Any], devices: dict[str, Any], behavior: dict[str, Any]) -> list[str]:
        indicators = []
        if trigger["type"] == "customer_report": indicators.append("customer_dispute")
        if behavior.get("anomalies"): indicators.extend(["amount_above_p95", "new_device", "rapid_transactions"])
        if devices.get("velocity", {}).get("spike"): indicators.append("rapid_transactions")
        if len(connected.get("accounts", [])) > 1: indicators.append("multiple_connected_accounts")
        for connection in connected.get("connection_types", []):
            if connection in {"shared_device", "shared_email"}: indicators.append(connection)
        return sorted(set(indicators))

    def _findings(self, matches: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ids = [item["evidence_id"] for item in evidence if item["type"] not in {"policy_grounding", "pattern_grounding"}]
        return [{"finding_id": f"finding-{uuid.uuid4().hex[:8]}", "pattern": match["pattern_id"], "assessment": f"{match['name']} matches indicators: {', '.join(match['matched_indicators'])}.", "confidence": match["confidence"], "supporting_evidence_ids": ids} for match in matches]

    def _record_uncertainty(self, case: dict[str, Any], stage: str, confidence: float, factors: list[str]) -> None:
        case["uncertainty"]["assessment_history"].append({"stage": stage, "confidence": round(confidence, 2), "factors": factors, "at": self._now().isoformat()})

    def _entity_refs(self, case: dict[str, Any], transactions: dict[str, Any], connected: dict[str, Any], devices: dict[str, Any]) -> None:
        refs = case["graph_refs"]["entity_ids"]
        refs["transactions"] = sorted({tx.get("transaction_id") for tx in transactions.get("transactions", []) if tx.get("transaction_id")})
        refs["accounts"] = sorted({account.get("account_id") for account in connected.get("accounts", []) if account.get("account_id")})
        refs["devices"] = sorted({device.get("device_id") for device in devices.get("devices", []) if device.get("device_id")})
        refs["identities"] = sorted(set(connected.get("identities", [])))

    def _evidence(self, type_: str, source: str, summary: str, confidence: float, graph_query: str | None) -> dict[str, Any]:
        return {"evidence_id": f"ev-{uuid.uuid4().hex[:8]}", "type": type_, "source": source, "summary": summary, "confidence": confidence, "observed_at": self._now().isoformat(), "graph_query": graph_query}

    def _decision(self, decision: str, rationale: str) -> dict[str, Any]:
        return {"decision_id": f"decision-{uuid.uuid4().hex[:8]}", "stage": "agent_loop", "decision": decision, "rationale": rationale, "at": self._now().isoformat()}

    def _next_evidence_action(self, indicators: list[str]) -> str:
        if "new_device" in indicators or "shared_device" in indicators:
            return "request_step_up_authentication"
        return "request_customer_validation"

    def _missing_evidence(self, indicators: list[str]) -> list[str]:
        missing = ["transaction_owner_validation"]
        if "shared_device" in indicators or "new_device" in indicators:
            missing.append("device_owner_validation")
        return missing

    def _risk_from_transactions(self, transactions: dict[str, Any]) -> float:
        scores = [tx.get("risk_score", 0) for tx in transactions.get("transactions", [])]
        return max(scores, default=0)

    def _memory_outcome(self, case: dict[str, Any]) -> str:
        if case["status"] == "needs_evidence": return "pending_more_evidence"
        return "recommended:" + ",".join(action["action"] for action in case["actions"] if action["mode"] == "recommend")

    def _explain(self, case: dict[str, Any], matches: list[dict[str, Any]], contributions: list[str]) -> str:
        patterns = ", ".join(match["name"] for match in matches) or "no confirmed catalog pattern"
        return f"The case is grounded in {len(case['evidence'])} evidence items and matches {patterns}. Confidence is {case['uncertainty']['confidence']:.2f}; contributors were {', '.join(contributions) or 'signal only'}. {('Approval is required before consequential controls.' if case['approval']['required'] else 'No approval gate is required.') }"

    def _existing_open_case(self, customer_id: str, transaction_id: str | None) -> dict[str, Any] | None:
        for case in self.memory.cases.values():
            if case.get("subject", {}).get("customer_id") != customer_id: continue
            if case.get("status") not in {"open", "needs_evidence", "escalated"}: continue
            if transaction_id and transaction_id in case.get("graph_refs", {}).get("entity_ids", {}).get("transactions", []): return case
        return None

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
