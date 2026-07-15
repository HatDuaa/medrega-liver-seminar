from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .schemas import PrivateCase


def to_private_view(public_row: Mapping[str, Any]) -> PrivateCase:
    """Return the only object a production predictor is allowed to receive."""
    if not isinstance(public_row, Mapping):
        raise TypeError("case row must be a mapping")
    return PrivateCase(
        case_id=public_row.get("case_id"),
        case_query=public_row.get("case_query"),
    )
