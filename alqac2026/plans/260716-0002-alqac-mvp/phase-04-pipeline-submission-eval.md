---
phase: 4
title: "Pipeline, submission và đánh giá"
status: pending
priority: P1
effort: 2d
dependencies: [2, 3]
---

# Phase 04: Pipeline, submission và đánh giá

## Overview

Ghép các module thành CLI end-to-end, chọn evidence, tạo submission và kiểm tra trước khi nộp.

## Requirements

- Dry-run mặc định.
- Không cho model bịa `chunk_id` hoặc `{law_id, aid}`.
- Submission đủ case, không trùng, không field thừa.
- Mọi run có config snapshot và audit log.

## Architecture

```python
def run_case(case, *, allow_network=False) -> CasePrediction: ...
def run_batch(cases, *, allow_network=False) -> list[CasePrediction]: ...
```

## Related Code Files

- Create: `alqac2026/src/alqac2026/reasoning/{evidence_selector.py,pipeline.py}`
- Create: `alqac2026/src/alqac2026/submission/{builder.py,validator.py}`
- Create: `alqac2026/src/alqac2026/evaluation/error_analysis.py`
- Create: `alqac2026/src/alqac2026/cli.py`
- Create: `alqac2026/scripts/build-submission.py`
- Create: `alqac2026/tests/{test_pipeline_offline.py,test_submission.py}`

## Helper Contracts

```python
deduplicate_chunks(chunks) -> list[RetrievedChunk]
rank_case_evidence(chunks, outcome) -> list[RetrievedChunk]
select_case_evidence(chunks, max_items=5) -> list[str]
build_submission(predictions) -> list[dict]
validate_submission(rows, expected_case_ids, law_corpus) -> ValidationReport
write_submission_atomic(path, rows) -> None
```

## Implementation Steps

1. Orchestrate case/batch pipeline.
2. Evidence selector chỉ nhận ID từ retrieved chunks.
3. Validator kiểm tra schema, ID đúng case và law pair tồn tại.
4. Thêm CLI `inspect-data`, `run-public`, `validate-submission`.
5. Chạy offline 50 case; không network.
6. Kiểm tra thủ công 5-10 case trước lần nộp đầu.

## Success Criteria

- [ ] End-to-end offline không lỗi.
- [ ] Submission validator từ chối ID bịa, case thiếu/trùng và nhãn sai.
- [ ] File cuối tên `submission.json` và được ghi atomic.
- [ ] Không tự upload/submit.

## Risk Assessment

Điểm evidence chính thức không tái tạo hoàn toàn offline. Phân biệt metric local với leaderboard; không gọi local proxy là Final Score.
