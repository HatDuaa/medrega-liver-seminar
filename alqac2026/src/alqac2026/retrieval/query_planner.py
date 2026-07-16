from __future__ import annotations

import re

from ..schemas import PrivateCase


_QUESTION_TAIL = re.compile(
    r"\s+(agent dự đoán|theo bạn|nguyên đơn có khả năng|nguyên đơn sẽ|agent cho biết).*$",
    flags=re.IGNORECASE | re.DOTALL,
)


def _case_focus(case_query: str, max_chars: int = 420) -> str:
    focus = _QUESTION_TAIL.sub("", case_query).strip()
    return focus[:max_chars].rstrip(" ,.;")


QUERY_STRATEGIES = frozenset({"legacy_v0", "decision_v1"})


def build_initial_queries(
    case: PrivateCase,
    max_queries: int = 2,
    *,
    strategy: str = "legacy_v0",
) -> list[str]:
    if not isinstance(case, PrivateCase):
        raise TypeError("query planner only accepts PrivateCase")
    if not 1 <= max_queries <= 2:
        raise ValueError("deterministic baseline supports one or two queries")
    if strategy not in QUERY_STRATEGIES:
        raise ValueError(f"unknown query strategy: {strategy}")
    if strategy == "decision_v1":
        queries = [
            (
                "quyết định của Tòa án tuyên xử chấp nhận toàn bộ chấp nhận một phần "
                "không chấp nhận bác yêu cầu khởi kiện yêu cầu phản tố"
            ),
            (
                "nhận định của Hội đồng xét xử yêu cầu nguyên đơn bị đơn có căn cứ "
                "không có căn cứ chấp nhận không chấp nhận"
            ),
        ]
        return queries[:max_queries]
    focus = _case_focus(case.case_query)
    queries = [
        f"chấp nhận yêu cầu khởi kiện của nguyên đơn; quyết định của Tòa án; {focus}",
        f"không chấp nhận hoặc bác yêu cầu khởi kiện của nguyên đơn; Hội đồng xét xử; {focus}",
    ]
    return queries[:max_queries]
