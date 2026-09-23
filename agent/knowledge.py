"""Policy and fraud-pattern grounding used by the agent.

The loader accepts JSON, text, or a PDF when ``pypdf`` is installed.  The
repository does not ship the hackathon's policy PDF, so the explicit defaults
below keep local runs deterministic and are marked as demo policy values.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_POLICY: dict[str, Any] = {
    "source": "demo_default_policy",
    "transaction_limits_by_risk": {"low": 10000, "medium": 5000, "high": 1000},
    "approval_thresholds": {"block_transaction": .80, "block_account": .90, "sar": .90},
    "sar_rules": {"minimum_risk_score": .90, "requires_human_approval": True, "requires_transaction_and_identity_evidence": True},
    "acceptable_evidence_types": ["transaction", "device_signal", "connected_account", "prior_case", "customer_validation", "policy_grounding", "pattern_grounding"],
}


def load_fraud_policy(path: str | Path | None = None) -> dict[str, Any]:
    """Load policy context, falling back to the demo policy if unavailable."""
    if path is None:
        return deepcopy(DEFAULT_POLICY)
    policy_path = Path(path)
    if not policy_path.exists():
        return deepcopy(DEFAULT_POLICY)
    if policy_path.suffix.lower() == ".json":
        with policy_path.open(encoding="utf-8") as handle:
            loaded = json.load(handle)
        return {**DEFAULT_POLICY, **loaded, "source": str(policy_path)}
    text = _extract_text(policy_path)
    return _policy_from_text(text, source=str(policy_path))


def load_fraud_patterns(path: str | Path | None = None, fallback: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if path is None or not Path(path).exists():
        return list(fallback or _fallback_patterns())
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    return value.get("patterns", value) if isinstance(value, dict) else value


def match_patterns(snapshot: dict[str, Any], patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observed = set(snapshot.get("indicators", []))
    matches = []
    for pattern in patterns:
        indicators = set(pattern.get("indicators", []))
        overlap = sorted(observed.intersection(indicators))
        if overlap:
            score = min(.99, pattern.get("base_confidence", .5) + .06 * max(0, len(overlap) - 1))
            matches.append({"pattern_id": pattern.get("pattern_id", pattern.get("name", "unknown")), "name": pattern.get("name", "Unknown pattern"), "matched_indicators": overlap, "confidence": round(score, 2)})
    return sorted(matches, key=lambda item: item["confidence"], reverse=True)


def _extract_text(path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    except Exception:
        return path.read_text(encoding="utf-8", errors="ignore")


def _policy_from_text(text: str, source: str) -> dict[str, Any]:
    policy = deepcopy(DEFAULT_POLICY)
    policy["source"] = source
    for key, risk in [("low", "low"), ("medium", "medium"), ("high", "high")]:
        match = re.search(rf"{key}.{{0,80}}?(?:INR|USD|₹|\$)?\s*([\d,]+)", text, flags=re.I | re.S)
        if match:
            policy["transaction_limits_by_risk"][risk] = float(match.group(1).replace(",", ""))
    sar = re.search(r"SAR.{0,120}?([0-9]+(?:\.[0-9]+)?)", text, flags=re.I | re.S)
    if sar:
        threshold = float(sar.group(1))
        policy["sar_rules"]["minimum_risk_score"] = threshold / 100 if threshold > 1 else threshold
    return policy


def _fallback_patterns() -> list[dict[str, Any]]:
    return [
        {"pattern_id": "account_takeover", "name": "Account takeover", "indicators": ["new_device", "new_location", "rapid_transactions"], "base_confidence": .78},
        {"pattern_id": "mule_ring", "name": "Potential mule ring", "indicators": ["shared_device", "shared_email", "multiple_connected_accounts", "rapid_transactions"], "base_confidence": .82},
        {"pattern_id": "friendly_fraud", "name": "Friendly fraud", "indicators": ["customer_dispute", "recognized_device", "merchant_delivery_confirmed"], "base_confidence": .62},
        {"pattern_id": "synthetic_identity", "name": "Synthetic identity", "indicators": ["identity_mismatch", "thin_file", "shared_identity"], "base_confidence": .74},
        {"pattern_id": "card_testing", "name": "Card testing", "indicators": ["many_small_transactions", "rapid_transactions", "multiple_merchants"], "base_confidence": .71},
    ]
