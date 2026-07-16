from __future__ import annotations

from collections import Counter
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
    prediction_distribution = Counter(pred_by_id.values())
    per_label: dict[str, dict[str, float | int]] = {}
    for label in labels:
        true_positive = confusion[label][label]
        gold_count = sum(confusion[label].values())
        predicted_count = sum(confusion[gold][label] for gold in labels)
        precision = true_positive / predicted_count if predicted_count else 0.0
        recall = true_positive / gold_count if gold_count else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[label] = {
            "gold": gold_count,
            "predicted": predicted_count,
            "true_positive": true_positive,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    fallback_count = sum(
        prediction.rationale.casefold().startswith("fallback:")
        for prediction in predictions
    )
    return {
        "num_cases": len(gold_by_id),
        "correct": correct,
        "outcome_accuracy": correct / len(gold_by_id),
        "confusion_matrix": confusion,
        "prediction_distribution": {
            label: prediction_distribution.get(label, 0) for label in labels
        },
        "per_label": per_label,
        "fallback_count": fallback_count,
        "fallback_rate": fallback_count / len(predictions),
        "note": "Law F1 is not computed because Public gold is free text, not corpus pairs.",
    }
