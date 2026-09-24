"""Small command-line smoke demo: ``python -m agent.demo``."""

import json

from .agent import FraudInvestigationAgent


if __name__ == "__main__":
    result = FraudInvestigationAgent().investigate({"type": "fraud_signal", "risk_score": .87, "reason": "velocity and device anomaly", "customer_id": "cust-1001", "transaction_id": "tx-1001-01"})
    print(json.dumps(result, indent=2, default=str))
