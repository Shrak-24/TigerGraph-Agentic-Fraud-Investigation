"""Case memory with indexed retrieval for similar investigations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CaseMemory:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.cases: dict[str, dict[str, Any]] = {}
        if self.path and self.path.exists():
            with self.path.open(encoding="utf-8") as handle:
                self.cases = json.load(handle)

    def store(self, case: dict[str, Any]) -> None:
        self.cases[case["case_id"]] = case
        self._flush()

    def retrieve(self, *, customer_id: str | None = None, connected_account_ids: list[str] | None = None, device_ids: list[str] | None = None, fraud_patterns: list[str] | None = None, limit: int = 5) -> list[dict[str, Any]]:
        requested = set(connected_account_ids or []) | set(device_ids or []) | set(fraud_patterns or [])
        scored = []
        for case in self.cases.values():
            subject = case.get("subject", {})
            refs = case.get("graph_refs", {}).get("entity_ids", {})
            case_ids = set(refs.get("accounts", [])) | set(refs.get("devices", []))
            case_patterns = {finding.get("pattern") for finding in case.get("findings", [])}
            score = 0
            if customer_id and subject.get("customer_id") == customer_id:
                score += 3
            score += 2 * len(requested.intersection(case_ids))
            score += len(requested.intersection(case_patterns))
            if score:
                scored.append((score, case))
        scored.sort(key=lambda item: (item[0], item[1].get("updated_at", "")), reverse=True)
        return [case for _, case in scored[:limit]]

    def _flush(self) -> None:
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8") as handle:
                json.dump(self.cases, handle, indent=2, default=str)
