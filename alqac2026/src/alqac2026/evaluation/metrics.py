from __future__ import annotations

from typing import Any

from ..schemas import ALLOWED_LABELS, CasePrediction


def outcome_metrics(
    public_rows: list[dict[str, Any]], predictions: list[CasePrediction]
) -> dict[str, Any]:
    gold_by_id: dict[str, str] = {}
    for row in public_rows:
        label = row.get("verdict_label")
        case_id = row.get("case_id")
        if label not in ALLOWED_LABELS:
            raise ValueError(f"missing or invalid Public label for {case_id}")
        gold_by_id[case_id] = label
    pred_by_id = {prediction.case_id: prediction.prediction for prediction in predictions}
    if set(gold_by_id) != set(pred_by_id):
        raise ValueError("prediction IDs do not match Public IDs")
    labels = sorted(ALLOWED_LABELS)
    confusion = {gold: {pred: 0 for pred in labels} for gold in labels}
    correct = 0
    for case_id, gold in gold_by_id.items():
        predicted = pred_by_id[case_id]
        confusion[gold][predicted] += 1
        correct += int(gold == predicted)
    return {
        "num_cases": len(gold_by_id),
        "correct": correct,
        "outcome_accuracy": correct / len(gold_by_id),
        "confusion_matrix": confusion,
        "note": "Law F1 is not computed because Public gold is free text, not corpus pairs.",
    }
