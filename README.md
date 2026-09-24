# TRACE. — TigerGraph Agentic Fraud Investigation

Integrated HHGOA hackathon project with a Python fraud-investigation agent,
TigerGraph graph contracts, deterministic mock graph data, benchmark output,
and a Streamlit analyst workbench.

## Repository layout

- `Backend/agent/` — investigation loop, GraphRAG grounding, mock graph tools, TigerGraph adapter, case memory, SAR drafting, and graph case writes.
- `Backend/graph/` — TigerGraph schema and GSQL investigation queries.
- `Backend/contracts/` — MCP operation contract and compatibility case schema.
- `Backend/pipeline/` — validated 20-case benchmark runner.
- `Backend/scripts/` — HHGOA dataset preparation utilities.
- `frontend/trace_fraud_ui/` — Streamlit UI connected to the live agent session.
- `CASE_RECORD_SCHEMA.json` — canonical agent/UI output contract.
- `TOOL_INTERFACE.md` — agent ↔ TigerGraph adapter contract.
- `docs/` — demo storyboard and technical blog outline.

## Run the integrated website

From the repository root:

```powershell
python -m streamlit run frontend/trace_fraud_ui/app.py --server.headless true --server.port 8501
```

Open `http://127.0.0.1:8501`. The UI starts with a mock high-risk case and
allows new fraud-signal, customer-report, and analyst-request investigations.

## Run the benchmark flow

The following creates 20 deterministic cases, validates every case against the
canonical schema, writes one answer file per case, records mock graph-write
status, and creates a manifest:

```powershell
python Backend/pipeline/run_benchmark.py
```

To use real benchmark triggers, pass a JSON array or `{ "triggers": [...] }`:

```powershell
python Backend/pipeline/run_benchmark.py --triggers-file .\data\benchmark_triggers.json
```

## TigerGraph integration

The mock graph layer is the default. Replace it with
`TigerGraphMCPGraphTools` and provide `invoke`, account resolution, and
transaction resolution callbacks. The adapter maps the bounded read queries
and the controlled `upsert_case_record` write described in
`Backend/contracts/mcp-tool-contract.json`.

The repository does not include HHGOA data, a TigerGraph endpoint, or
credentials. The benchmark and UI therefore remain runnable offline while the
integration seam is ready for the real dataset and MCP server.
