# Agent ↔ Graph tool interface

Version `1.0.0`. Person 2's agent depends on these high-level operations. The
mock implementation is in `agent/graph_tools.py`; Person 1's TigerGraph MCP
adapter should expose the same method names, arguments, and response keys.

All IDs are opaque strings. All operations return JSON-compatible dictionaries
and must return an empty array rather than `null` when there are no matches.
The adapter may add `error` with one of `INVALID_ARGUMENT`, `NOT_FOUND`,
`QUERY_TIMEOUT`, or `GRAPH_UNAVAILABLE`.

```python
def query_transactions(customer_id: str, days: int = 90) -> dict:
    # {"transactions": [...], "summary": {...}}

def query_connected_accounts(customer_id: str) -> dict:
    # {"accounts": [...], "connection_types": [...], "devices": [...],
    #  "identities": [...], "shared_contacts": [...]}

def query_device_signals(device_ids: list[str]) -> dict:
    # {"devices": [...], "velocity": {...}, "locations": [...]}

def query_prior_cases(pattern_or_customer_id: str) -> dict:
    # {"cases": [...], "outcomes": [...]}

def query_account_behavior(customer_id: str) -> dict:
    # {"customer_id": "...", "baseline": {...}, "anomalies": [...]}

def query_fraud_patterns() -> dict:
    # {"patterns": [{"pattern_id": "...", "name": "...",
    #                 "indicators": [...], "typical_entities": [...],
    #                 "base_confidence": 0.0}]}
```

## Entity shapes

`transactions` contain `transaction_id`, `customer_id`, `amount`, `currency`,
`merchant`, `timestamp`, `risk_score`, `device_id`, and `country`.

`accounts` contain `account_id`, `customer_id`, `risk_score`, and `status`.
`devices` contain `device_id`, `first_seen`, `account_count`,
`is_new_for_subject`, and `risk_score`. `cases` contain `case_id`, subject
IDs, `device_ids`, `fraud_patterns`, `outcome`, `action`, and `summary`.

## TigerGraph mapping

The existing low-level operations in `contracts/mcp-tool-contract.json` can
back this interface: `get_transaction_context` feeds transactions,
`find_connected_accounts` feeds account links, `detect_mule_rings` feeds
device/account overlap, `link_device_identity` feeds identity signals, and
`find_prior_cases` feeds prior-case retrieval. Account behavior may be a
derived aggregate or an additional read-only query.

The agent never sends arbitrary GSQL, credentials, or case writes through this
interface. Consequential actions are recommendations with an approval route;
the current implementation does not execute account or transaction controls.

## Existing Person 1 contract compatibility

`agent.tigergraph_adapter.TigerGraphMCPGraphTools` bridges the current
low-level operations in `contracts/mcp-tool-contract.json` to this interface.
It requires two small application-owned resolvers:

```python
TigerGraphMCPGraphTools(
    invoke=mcp_call,
    resolve_account_id=lambda customer_id: "acct-...",
    resolve_transaction_ids=lambda customer_id, days: ["tx-..."],
    pattern_catalog=known_patterns,
)
```

This removes the previous mismatch: the agent remains customer-oriented while
the MCP adapter handles account/transaction-keyed TigerGraph calls. The
low-level contract currently has no account-baseline query, so the adapter
returns a neutral baseline until that read-only query is added.
