---
phase: 5
title: "Agentic retrieval có kiểm soát"
status: pending
priority: P2
effort: 2-3d
dependencies: [4]
---

# Phase 05: Agentic retrieval có kiểm soát

## Overview

Nâng từ bộ query cố định lên planner tự nhận diện thông tin thiếu và sinh follow-up query. Chỉ làm nếu Retrieval API chứng minh cải thiện so với baseline.

## Requirements

- Bộ query cố định là baseline bắt buộc.
- Hard cap số request/case.
- Cảnh báo query gần nghĩa; không semantic-dedup tự động.
- Stopping rule dựa trên coverage thông tin và evidence trùng.

## Related Code Files

- Modify: `alqac2026/src/alqac2026/retrieval/query_planner.py`
- Modify: `alqac2026/src/alqac2026/reasoning/pipeline.py`
- Create: `alqac2026/prompts/query-planning.txt`
- Create: `alqac2026/tests/test_query_planner.py`

## Helper Contracts

```python
build_initial_queries(case) -> list[str]
build_followup_query(case, chunks) -> str | None
query_similarity_warning(new_query, previous_queries) -> float
should_stop_retrieval(chunks, budget) -> bool
```

## Implementation Steps

1. Benchmark bộ 4-6 query cố định.
2. Thêm planner structured output.
3. Dừng khi chunk ID lặp nhiều, đủ nhóm thông tin hoặc hết budget.
4. So sánh accuracy/evidence/requests với baseline cố định.
5. Chỉ giữ agentic planner nếu lợi ích đáng kể và ổn định.

## Success Criteria

- [ ] Không vượt hard cap.
- [ ] Không gọi lại exact query.
- [ ] Có bảng so sánh chất lượng và request cost.
- [ ] Có thể tắt planner để quay về deterministic baseline.

## Risk Assessment

Planner có thể tạo nhiều paraphrase làm cháy ngân sách. Giảm thiểu bằng cap, cảnh báo similarity, cache exact và deterministic fallback.
