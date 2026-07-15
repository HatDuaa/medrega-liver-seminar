---
phase: 3
title: "Baseline reasoning và tìm luật"
status: pending
priority: P1
effort: 2-3d
dependencies: [1]
---

# Phase 03: Baseline reasoning và tìm luật

## Overview

Tạo baseline hoàn toàn local từ `case_query`, model open-weight dưới 10B và corpus luật. Chưa cần Retrieval API.

## Requirements

- Model interface không phụ thuộc một backend cụ thể.
- Output structured JSON; parse fail có fallback rõ ràng.
- Model chỉ thấy Private-view.
- Law hit phải tồn tại thật trong corpus.
- Đánh giá Outcome Accuracy và confusion matrix bốn nhãn.

## Architecture

```text
PrivateCase -> LocalModel -> OutcomePrediction
PrivateCase -> Law Query Builder -> Local Law Index -> LawEvidence[]
```

## Related Code Files

- Create: `alqac2026/src/alqac2026/reasoning/outcome_predictor.py`
- Create: `alqac2026/src/alqac2026/law/{corpus.py,index.py,retriever.py}`
- Create: `alqac2026/src/alqac2026/evaluation/metrics.py`
- Create: `alqac2026/prompts/outcome-prediction.txt`
- Create: `alqac2026/scripts/{build-law-index.py,run-public.py}`
- Create: `alqac2026/tests/{test_outcome_predictor.py,test_law_retriever.py,test_metrics.py}`

## Helper Contracts

```python
predict_outcome(case, chunks=[]) -> OutcomePrediction
build_law_index(corpus) -> LawIndex
build_law_query(case, chunks=[]) -> str
search_law(query, top_k=10) -> list[LawHit]
deduplicate_law_evidence(items) -> list[LawEvidence]
outcome_accuracy(gold, pred) -> float
confusion_matrix_4way(gold, pred) -> Matrix
```

## Implementation Steps

1. Chọn adapter local model nhưng chưa khóa model cuối cùng.
2. Prompt trả nhãn, confidence và giải thích ngắn.
3. Validate nhãn; không tin JSON model trực tiếp.
4. Dựng BM25/TF-IDF cho 3.352 điều luật.
5. Chạy 50 case chỉ bằng `case_query` để tạo mốc dưới.
6. Lưu prediction và config theo run ID để tái lập.

## Success Criteria

- [ ] Dự đoán đủ 50 case, không parse crash.
- [ ] Có accuracy/confusion matrix baseline.
- [ ] Mọi law evidence tồn tại trong corpus.
- [ ] Không dùng proprietary API.

## Risk Assessment

Public có 50 mẫu và nhãn mất cân bằng; không fine-tune trên cả 50 rồi tự chấm cùng tập. MVP ưu tiên zero/few-shot local và báo trung thực giới hạn.
