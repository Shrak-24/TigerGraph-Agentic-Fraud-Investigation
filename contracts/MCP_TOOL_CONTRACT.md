# TigerGraph MCP tool contract

Version `1.0.0` is the integration boundary between the graph workstream and the agent. The agent calls the five operations in `mcp-tool-contract.json`; the MCP adapter maps each operation to the same-named installed GSQL query on graph `HHGOA_FRAUD`.

## Stable behavior

- Inputs are JSON objects. IDs are opaque strings; the adapter must not coerce leading zeros.
- Outputs are JSON objects with the named arrays, even when no matches exist.
- Results should include only the fields listed in the contract entities section plus query-specific arrays.
- The graph is read-only through these operations. Case writes are intentionally reserved for the later case-record integration.
- Invalid IDs return an empty result with `NOT_FOUND` only when the adapter can distinguish absence from a valid zero-match traversal.
- Enforce the documented bounds for hop counts and limits to prevent accidental graph-wide traversals.

## Example

Request: `{"account_id":"acct_001","min_shared_devices":1,"min_ring_size":3}`

Response:

```json
{
  "accounts": [{"account_id":"acct_014","customer_id":"cust_22","risk_score":0.91}],
  "devices": ["dev_77"],
  "members": ["acct_001","acct_014","acct_031"]
}
```

## Smoke-test checklist

1. Call each operation with a known ID from the loaded sample.
2. Call each operation with a syntactically valid unknown ID and confirm a stable empty-array response.
3. Confirm max-hop and limit bounds are rejected with `INVALID_ARGUMENT`.
4. Confirm the MCP adapter does not expose credentials, raw query text, or unbounded arbitrary GSQL execution.
