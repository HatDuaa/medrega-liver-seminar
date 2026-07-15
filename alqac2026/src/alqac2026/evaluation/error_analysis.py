from __future__ import annotations

from typing import Any

from ..schemas import CasePrediction


def misclassified_case_ids(
    public_rows: list[dict[str, Any]], predictions: list[CasePrediction]
) -> list[str]:
    gold = {row["case_id"]: row.get("verdict_label") for row in public_rows}
    return [
        prediction.case_id
        for prediction in predictions
        if gold.get(prediction.case_id) != prediction.prediction
    ]
