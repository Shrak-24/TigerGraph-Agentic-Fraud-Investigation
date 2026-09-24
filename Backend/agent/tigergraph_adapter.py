"""Compatibility adapter from Person 1's low-level MCP contract.

The investigation loop stays on the stable high-level interface. This class
lets it consume the existing operations in ``contracts/mcp-tool-contract.json``
without making the agent know about GSQL query names or account resolution.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class TigerGraphMCPGraphTools:
    """Adapt low-level TigerGraph MCP calls to :class:`GraphToolInterface`.

    ``invoke`` receives an operation name and JSON request object. The two
    resolver callbacks are required because the current low-level contract is
    account/transaction keyed while the agent intentionally works by
    ``customer_id``.
    """

    def __init__(
        self,
        invoke: Callable[[str, dict[str, Any]], dict[str, Any]],
        resolve_account_id: Callable[[str], str],
        resolve_transaction_ids: Callable[[str, int], list[str]],
        pattern_catalog: list[dict[str, Any]] | None = None,
    ) -> None:
        self.invoke = invoke
        self.resolve_account_id = resolve_account_id
        self.resolve_transaction_ids = resolve_transaction_ids
        self.pattern_catalog = pattern_catalog or []

    def query_transactions(self, customer_id: str, days: int = 90) -> dict[str, Any]:
        transactions: list[dict[str, Any]] = []
        for tx_id in self.resolve_transaction_ids(customer_id, days):
            result = self.invoke("get_transaction_context", {"tx_id": tx_id, "max_hops": 0})
            transactions.extend(result.get("transactions", []))
        amounts = [float(tx.get("amount", 0)) for tx in transactions]
        return {
            "transactions": transactions,
            "summary": {
                "count": len(transactions),
                "total_amount": round(sum(amounts), 2),
                "high_risk_count": sum(float(tx.get("model_risk_score", tx.get("risk_score", 0))) >= .75 for tx in transactions),
                "unique_merchants": len({tx.get("merchant_id", tx.get("merchant", "")) for tx in transactions}),
                "unique_devices": sorted({tx.get("device_id") for tx in transactions if tx.get("device_id")}),
            },
        }

    def query_connected_accounts(self, customer_id: str) -> dict[str, Any]:
        result = self.invoke("find_connected_accounts", {"account_id": self.resolve_account_id(customer_id), "max_hops": 2})
        shared_devices = result.get("shared_devices", [])
        shared_identities = result.get("shared_identities", [])
        connection_types = []
        if shared_devices:
            connection_types.append("shared_device")
        if shared_identities:
            connection_types.append("shared_identity")
        return {"accounts": result.get("accounts", []), "connection_types": connection_types, "devices": shared_devices, "identities": shared_identities, "shared_contacts": []}

    def query_device_signals(self, device_ids: list[str]) -> dict[str, Any]:
        devices: list[dict[str, Any]] = []
        for device_id in device_ids:
            result = self.invoke("link_device_identity", {"device_id": device_id})
            devices.append({"device_id": device_id, "identity_count": len(result.get("identities", [])), "account_count": len(result.get("accounts", []))})
        return {"devices": devices, "velocity": {}, "locations": []}

    def query_prior_cases(self, pattern_or_customer_id: str) -> dict[str, Any]:
        account_id = pattern_or_customer_id if pattern_or_customer_id.startswith("acct-") else self.resolve_account_id(pattern_or_customer_id)
        result = self.invoke("find_prior_cases", {"account_id": account_id, "limit": 100})
        cases = result.get("cases", [])
        return {"cases": cases, "outcomes": [case.get("outcome") for case in cases]}

    def query_account_behavior(self, customer_id: str) -> dict[str, Any]:
        # The existing contract has no behavior-baseline operation. Returning a
        # neutral baseline keeps the adapter honest until Person 1 adds one.
        return {"customer_id": customer_id, "baseline": {}, "anomalies": []}

    def query_fraud_patterns(self) -> dict[str, Any]:
        return {"patterns": self.pattern_catalog}

    def write_case(self, case: dict[str, Any]) -> dict[str, Any]:
        """Write a case through the optional ``upsert_case_record`` MCP call."""
        return self.invoke("upsert_case_record", {"case": case})
