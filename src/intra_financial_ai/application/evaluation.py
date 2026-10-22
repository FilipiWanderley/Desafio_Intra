from __future__ import annotations

import json
from pathlib import Path


def evaluate(run_folder: Path, gold_path: Path) -> dict:
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    expected = gold["expected"]
    tolerance = gold["numeric_absolute_tolerance_million"]
    total = 0
    correct = 0
    citation_correct = 0
    failures = []
    for filename, fields in expected.items():
        data = json.loads((run_folder / filename.replace(".pdf", ".json")).read_text(encoding="utf-8"))
        for field, item in fields.items():
            total += 1
            actual = data["metrics"][field]
            value_ok = item.get("value") is None or (actual["value"] is not None and abs(actual["value"] - item["value"]) <= tolerance)
            status_ok = item["status"] == actual["status"]
            page_ok = item.get("page") is None or item["page"] in [ref["page"] for ref in actual["evidence"]]
            if status_ok and value_ok:
                correct += 1
            if page_ok:
                citation_correct += 1
            if not (status_ok and value_ok and page_ok):
                failures.append({"file": filename, "field": field, "expected": item, "actual_status": actual["status"], "actual_value": actual["value"], "citation_pages": [ref["page"] for ref in actual["evidence"]]})
    return {
        "samples": total,
        "field_accuracy": round(correct / total, 4) if total else None,
        "citation_page_accuracy": round(citation_correct / total, 4) if total else None,
        "failures": failures,
        "caveat": "Métricas apenas neste pequeno golden set; não estimam qualidade de produção ou generalização.",
    }
