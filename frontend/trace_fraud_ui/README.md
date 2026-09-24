# TRACE. Fraud Investigation Workbench

Redesigned from the supplied reference: dark cinematic/editorial shell, oversized typography, thin rules, restrained red accent, and a premium investigation-workbench layout.

Open `ui_preview.html` for an instant browser preview.

For Streamlit from the repository root:
`pip install -r frontend/trace_fraud_ui/requirements.txt`
`streamlit run frontend/trace_fraud_ui/app.py --server.headless true --server.port 8501`
then open `http://localhost:8501`.

Windows users can double-click `start_windows.bat` from this directory.

The workbench is connected to `Backend/agent/` and starts with deterministic
mock graph data. Use the sidebar to run fraud-signal, customer-report, or
analyst-request investigations and inspect the generated case record.
