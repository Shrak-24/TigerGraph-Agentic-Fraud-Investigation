# HHGOA Person 1 - Graph & Data

This repository contains the graph/data workstream for the TigerGraph Agentic Fraud Investigation challenge. It is intentionally independent of the agent and UI workstreams: the graph can be loaded and queried before either of those components is available.

## Contents

- `graph/schema.gsql` - TigerGraph vertex, edge, loading-job, and index definitions.
- `graph/queries.gsql` - read-only investigation and pattern-detection queries.
- `contracts/mcp-tool-contract.json` - machine-readable tool signatures for the agent/MCP integration.
- `contracts/MCP_TOOL_CONTRACT.md` - human-readable contract with examples and stability rules.
- `scripts/prepare_hhgoa.py` - converts the raw IEEE-CIS-style CSVs into the normalized CSVs consumed by the loading jobs.
- `contracts/case-record.schema.json` - shared case-record contract for the agent and UI workstreams.
- `fixtures/sample-case.json` - frontend/integration-safe sample case object.
- `pipeline/run_benchmark.py` - dummy 20-case benchmark pipeline; replace its stub with the real agent call during integration.
- `docs/TECHNICAL_BLOG_OUTLINE.md` and `docs/DEMO_VIDEO_STORYBOARD.md` - Person 3 content scaffolds.
- `frontend/trace_fraud_ui/` - merged TRACE. Streamlit workbench and standalone HTML preview from the Desktop UI folder.

## Local UI

For the standalone preview, open `frontend/trace_fraud_ui/ui_preview.html` directly in a browser. For the interactive Streamlit workbench:

```powershell
cd frontend/trace_fraud_ui
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

It runs at `http://localhost:8501` and currently uses synthetic benchmark data. The UI is intentionally kept separate from the graph backend until the MCP and case-record integration is connected.

## Prerequisites

1. Obtain the HHGOA_IEEE dataset and read its bundled README first. The README is authoritative for filenames, column names, and the benchmark split.
2. Run TigerGraph Savanna or Community Edition and obtain an API token.
3. Put the raw CSV files in a local input directory. This workstream does not commit the dataset.

## Load flow

```powershell
$py = "C:\Users\<you>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py scripts/prepare_hhgoa.py --input-dir .\data\raw --output-dir .\data\normalized
```

Upload the generated `data/normalized/*.csv` files to TigerGraph, then run `graph/schema.gsql` in GSQL and execute the loading jobs it defines. The script tolerates missing optional device/identity/case files and preserves unknown source columns in the transaction `raw_features` JSON field.

Example GSQL deployment sequence:

```gsql
RUN QUERY install_query("get_transaction_context")
RUN QUERY install_query("find_connected_accounts")
RUN QUERY install_query("detect_mule_rings")
RUN QUERY install_query("link_device_identity")
RUN QUERY install_query("find_prior_cases")
```

The exact `CREATE LOADING JOB` run command depends on whether the files are uploaded to a Savanna file store or mounted in CE. The job names and input filenames are stable; only the file URI needs to be changed for the environment.

## What is and is not complete

The schema, normalized-file contract, GSQL queries, and MCP interface are implemented. A live import cannot be completed from this checkout because no HHGOA dataset, TigerGraph endpoint, or credentials were supplied. After those are available, run the loader, execute the loading jobs, and smoke-test the five MCP operations in the contract.
