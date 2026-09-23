"""Graph tool boundary used by the investigation agent.

The mock implementation returns stable, realistic JSON.  Person 1 can replace
it with an adapter that calls the TigerGraph MCP operations without changing
the agent loop.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Protocol


class GraphToolInterface(Protocol):
    """Exact high-level operations required by the agent."""

    def query_transactions(self, customer_id: str, days: int = 90) -> dict[str, Any]: ...

    def query_connected_accounts(self, customer_id: str) -> dict[str, Any]: ...

    def query_device_signals(self, device_ids: list[str]) -> dict[str, Any]: ...

    def query_prior_cases(self, pattern_or_customer_id: str) -> dict[str, Any]: ...

    def query_account_behavior(self, customer_id: str) -> dict[str, Any]: ...

    def query_fraud_patterns(self) -> dict[str, Any]: ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MockGraphTools:
    """Deterministic graph-shaped fixtures for local development and demos."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or _now
        self._patterns = _default_patterns()
        self._case_fixtures = [
            {
                "case_id": "prior-case-017",
                "customer_id": "cust-1001",
                "account_id": "acct-1001",
                "device_ids": ["dev-shared-07"],
                "fraud_patterns": ["mule_ring"],
                "outcome": "confirmed_fraud",
                "action": "block_account",
                "summary": "Shared device connected three accounts with rapid beneficiary additions.",
            },
            {
                "case_id": "prior-case-023",
                "customer_id": "cust-2099",
                "account_id": "acct-2099",
                "device_ids": ["dev-legit-02"],
                "fraud_patterns": ["account_takeover"],
                "outcome": "false_positive",
                "action": "allow_transaction",
                "summary": "Travel and a new phone explained the location and device change.",
            },
            {
                "case_id": "prior-case-031",
                "customer_id": "cust-1001",
                "account_id": "acct-1001",
                "device_ids": ["dev-shared-07"],
                "fraud_patterns": ["friendly_fraud"],
                "outcome": "escalated",
                "action": "monitor_account",
                "summary": "A disputed card purchase required customer and merchant validation.",
            },
        ]

    def query_transactions(self, customer_id: str, days: int = 90) -> dict[str, Any]:
        """Return the subject's recent transactions and aggregate signals."""
        if days < 1 or days > 365:
            raise ValueError("days must be between 1 and 365")
        now = self._clock()
        if customer_id in {"cust-1001", "cust-demo-001"}:
            txs = [
                self._tx("tx-1001-01", customer_id, now - timedelta(minutes=8), 4980, "new-merchant-77", "dev-shared-07", .96),
                self._tx("tx-1001-02", customer_id, now - timedelta(minutes=7), 4720, "new-merchant-77", "dev-shared-07", .91),
                self._tx("tx-1001-03", customer_id, now - timedelta(minutes=5), 3900, "beneficiary-14", "dev-shared-07", .88),
                self._tx("tx-1001-04", customer_id, now - timedelta(minutes=3), 2450, "beneficiary-14", "dev-shared-07", .86),
                self._tx("tx-1001-05", customer_id, now - timedelta(days=2), 120, "usual-merchant-02", "dev-known-01", .11),
            ]
        else:
            txs = [
                self._tx("tx-generic-01", customer_id, now - timedelta(hours=4), 86, "usual-merchant-02", "dev-known-01", .12),
                self._tx("tx-generic-02", customer_id, now - timedelta(days=3), 145, "usual-merchant-09", "dev-known-01", .16),
            ]
        recent_raw = [tx for tx in txs if (now - tx["timestamp"]).days <= days]
        amounts = [tx["amount"] for tx in recent_raw]
        recent = [{**tx, "timestamp": tx["timestamp"].isoformat()} for tx in recent_raw]
        return {
            "transactions": recent,
            "summary": {
                "count": len(recent),
                "total_amount": round(sum(amounts), 2),
                "high_risk_count": sum(tx["risk_score"] >= .75 for tx in recent_raw),
                "unique_merchants": len({tx["merchant"] for tx in recent}),
                "unique_devices": sorted({tx["device_id"] for tx in recent}),
                "velocity_1h": sum((now - tx["timestamp"]).total_seconds() <= 3600 for tx in recent_raw),
            },
        }

    def query_connected_accounts(self, customer_id: str) -> dict[str, Any]:
        if customer_id in {"cust-1001", "cust-demo-001"}:
            return {
                "accounts": [
                    {"account_id": "acct-1001", "customer_id": customer_id, "risk_score": .87, "status": "active"},
                    {"account_id": "acct-1014", "customer_id": "cust-1014", "risk_score": .81, "status": "review"},
                    {"account_id": "acct-1031", "customer_id": "cust-1031", "risk_score": .76, "status": "active"},
                ],
                "connection_types": ["shared_device", "shared_email", "shared_beneficiary"],
                "devices": ["dev-shared-07"],
                "identities": ["email-hash-44", "phone-hash-19"],
                "shared_contacts": ["beneficiary-14"],
            }
        return {
            "accounts": [{"account_id": f"acct-{customer_id.removeprefix('cust-')}", "customer_id": customer_id, "risk_score": .22, "status": "active"}],
            "connection_types": [],
            "devices": ["dev-known-01"],
            "identities": [],
            "shared_contacts": [],
        }

    def query_device_signals(self, device_ids: list[str]) -> dict[str, Any]:
        devices = []
        locations = []
        for device_id in device_ids:
            shared = device_id == "dev-shared-07"
            devices.append({
                "device_id": device_id,
                "first_seen": (self._clock() - timedelta(days=2 if shared else 420)).isoformat(),
                "account_count": 3 if shared else 1,
                "is_new_for_subject": shared,
                "risk_score": .89 if shared else .12,
            })
            locations.append({"device_id": device_id, "country": "IN", "city": "Mumbai" if shared else "Pune", "event_count_1h": 6 if shared else 1})
        return {
            "devices": devices,
            "velocity": {"login_count_1h": 7 if "dev-shared-07" in device_ids else 1, "distinct_accounts_1h": 3 if "dev-shared-07" in device_ids else 1, "spike": "dev-shared-07" in device_ids},
            "locations": locations,
        }

    def query_prior_cases(self, pattern_or_customer_id: str) -> dict[str, Any]:
        cases = []
        for case in self._case_fixtures:
            haystack = {case["customer_id"], case["account_id"], *case["device_ids"], *case["fraud_patterns"]}
            if pattern_or_customer_id in haystack:
                cases.append(case)
        return {"cases": cases, "outcomes": [case["outcome"] for case in cases]}

    def query_account_behavior(self, customer_id: str) -> dict[str, Any]:
        risky = customer_id in {"cust-1001", "cust-demo-001"}
        return {
            "customer_id": customer_id,
            "baseline": {"typical_amount": 180 if risky else 125, "p95_amount": 500 if risky else 350, "usual_countries": ["IN"], "usual_devices": ["dev-known-01"]},
            "anomalies": ["amount_above_p95", "new_device", "rapid_transactions"] if risky else [],
        }

    def query_fraud_patterns(self) -> dict[str, Any]:
        return {"patterns": self._patterns}

    def _tx(self, tx_id: str, customer_id: str, timestamp: datetime, amount: float, merchant: str, device_id: str, risk_score: float) -> dict[str, Any]:
        return {"transaction_id": tx_id, "customer_id": customer_id, "amount": amount, "currency": "INR", "merchant": merchant, "timestamp": timestamp, "risk_score": risk_score, "device_id": device_id, "country": "IN"}


def _default_patterns() -> list[dict[str, Any]]:
    return [
        {"pattern_id": "account_takeover", "name": "Account takeover", "indicators": ["new_device", "new_location", "rapid_transactions", "failed_authentication"], "typical_entities": ["account", "device", "identity"], "base_confidence": .78},
        {"pattern_id": "mule_ring", "name": "Potential mule ring", "indicators": ["shared_device", "shared_email", "multiple_connected_accounts", "rapid_transactions"], "typical_entities": ["account", "device", "beneficiary"], "base_confidence": .82},
        {"pattern_id": "friendly_fraud", "name": "Friendly fraud", "indicators": ["customer_dispute", "recognized_device", "merchant_delivery_confirmed"], "typical_entities": ["customer", "transaction", "merchant"], "base_confidence": .62},
        {"pattern_id": "synthetic_identity", "name": "Synthetic identity", "indicators": ["identity_mismatch", "thin_file", "shared_identity", "new_account"], "typical_entities": ["identity", "account"], "base_confidence": .74},
        {"pattern_id": "card_testing", "name": "Card testing", "indicators": ["many_small_transactions", "rapid_transactions", "multiple_merchants", "declines"], "typical_entities": ["transaction", "merchant", "device"], "base_confidence": .71},
    ]
