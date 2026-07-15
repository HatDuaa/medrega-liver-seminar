---
phase: 1
title: "Foundation và chống leakage"
status: pending
priority: P1
effort: 1-2d
dependencies: []
---

# Phase 01: Foundation và chống leakage

## Overview

Khởi tạo package Python, schema và lớp Private-view. Đây là hàng rào bắt buộc trước mọi model/retrieval.

## Requirements

- Production input chỉ có `case_id`, `case_query`.
- Public fields vẫn đọc được để đánh giá nhưng nằm ngoài object truyền cho predictor.
- Corpus luật kiểm tra được cặp `{law_id, aid}`.
- Config đọc `.env` nhưng không log secret.

## Architecture

```python
@dataclass(frozen=True)
class PrivateCase:
    case_id: str
    case_query: str

def to_private_view(public_row: dict) -> PrivateCase: ...
```

Schema thêm: `RetrievedChunk`, `LawEvidence`, `OutcomePrediction`, `CasePrediction`, `SubmissionRow`.

## Related Code Files

- Create: `alqac2026/pyproject.toml`
- Create: `alqac2026/src/alqac2026/{config.py,schemas.py,data_loader.py,private_view.py}`
- Create: `alqac2026/tests/{test_data_loader.py,test_private_view.py,test_schemas.py}`
- Modify: `alqac2026/README.md`

## Helper Contracts

```python
load_public_cases(path) -> list[dict]
load_law_corpus(path) -> list[LawDocument]
validate_unique_case_ids(cases) -> None
to_private_view(public_row) -> PrivateCase
validate_law_pair(law_id, aid, corpus) -> bool
```

## Implementation Steps

1. Tạo package và dependency tối thiểu.
2. Định nghĩa schema có validation bốn nhãn.
3. Viết loader UTF-8, kiểm tra 50 case ID duy nhất.
4. Viết `to_private_view()` chỉ copy hai trường hợp lệ.
5. Viết test cố tình đưa `verdict_label`/`judgment_text` và xác nhận predictor không nhận được.

## Success Criteria

- [ ] Parse được hai JSON chính thức.
- [ ] Sinh đúng 50 `PrivateCase`.
- [ ] Leakage tests pass.
- [ ] `.env` không xuất hiện trong Git status.

## Risk Assessment

Rủi ro lớn nhất là code tiện tay dùng `judgment_text` hoặc `verdict_label`. Giảm thiểu bằng type contract, không truyền raw dict qua pipeline.
