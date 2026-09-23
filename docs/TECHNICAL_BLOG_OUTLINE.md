# Technical blog outline

## Working title

From uncertain signals to defensible action: an agentic fraud investigator on TigerGraph

## Sections

1. **The problem** - why transaction-level alerts miss connected-account context and why uncertainty matters.
2. **Architecture** - TigerGraph graph, MCP tool boundary, agent loop, GraphRAG policy grounding, case memory, and analyst handoff.
3. **Graph model** - accounts, customers, transactions, devices, identities, prior cases, and the relationship patterns used for investigation.
4. **Investigation loop** - trigger, gather evidence, assess uncertainty, request controlled evidence, recommend an action, explain, and store memory.
5. **Pattern detection** - shared-device clusters, connected accounts, transaction context, and prior-case retrieval.
6. **Safety and governance** - approval routes, read-only graph tools, bounded traversals, and recommendation versus execution.
7. **Benchmark pipeline** - how the 20 cases are run and how case records are produced.
8. **What we learned** - graph context improves explanations, and explicit uncertainty prevents premature blocking.
9. **Future work** - live MCP deployment, richer temporal motifs, calibrated evaluation, and analyst feedback loops.

## Evidence to include

- A graph neighborhood screenshot for one benchmark case.
- The MCP contract and one tool request/response.
- Before/after recommendation as additional evidence arrives.
- A sample case record and approval route.
