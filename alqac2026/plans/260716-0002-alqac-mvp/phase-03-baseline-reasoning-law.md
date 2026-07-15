---
phase: 3
title: "Baseline reasoning và tìm luật"
status: completed
priority: P1
effort: 2-3d
dependencies: [1]
---

# Phase 03: Baseline reasoning và tìm luật

## Overview

Tạo baseline từ `case_query`, chunk API và corpus luật. `deterministic_v0` là backend chính thức cho lượt Public đầu; Codex/Claude CLI chỉ được smoke-test contract trong thư mục cô lập và không hợp lệ cho submission.

## Requirements

- Model interface không phụ thuộc backend cụ thể; có `DeterministicRunner` chính thức và adapter dev-only cho `CodexCliRunner`/`ClaudeCliRunner`.
- Mỗi invocation chạy isolated, không dùng lịch sử chat/session ngoài case hiện tại.
- CLI timeout, non-zero exit, output rỗng và JSON sai phải được xử lý rõ ràng.
- Kết quả CLI gắn `backend`, `model`, `eligible_for_submission=false`.
- Output structured JSON; parse fail có fallback rõ ràng.
- Model chỉ thấy Private-view.
- Law hit phải tồn tại thật trong corpus.
- Đánh giá Outcome Accuracy và confusion matrix bốn nhãn.

## Architecture

```text
PrivateCase + RetrievedChunk[] -> DeterministicRunner -> OutcomePrediction
PrivateCase -> LlmRunner(Codex CLI | Claude CLI) -> draft-only OutcomePrediction
PrivateCase -> Law Query Builder -> Local Law Index -> LawEvidence[]
```

Prototype invocation dự kiến:

```text
# Codex: prompt qua stdin, schema file, sandbox read-only, session mới
codex exec --sandbox read-only --skip-git-repo-check \
  --output-schema <schema.json> -

# Claude: prompt qua stdin, không tool, không lưu session, JSON schema
claude -p --tools "" --no-session-persistence \
  --output-format json --json-schema <inline-schema>
```

Không nối prompt vào shell command. Dùng subprocess argument list và truyền nội dung vụ án qua stdin để tránh shell injection.

## Related Code Files

- Create: `alqac2026/src/alqac2026/reasoning/{llm_runner.py,outcome_predictor.py}`
- Create: `alqac2026/src/alqac2026/law/{corpus.py,index.py,retriever.py}`
- Create: `alqac2026/src/alqac2026/evaluation/metrics.py`
- Create: `alqac2026/prompts/outcome-prediction.txt`
- Create: `alqac2026/scripts/{build-law-index.py,run-public.py}`
- Create: `alqac2026/tests/{test_outcome_predictor.py,test_law_retriever.py,test_metrics.py}`

## Helper Contracts

```python
predict_outcome(case, chunks=[]) -> OutcomePrediction
run_llm(prompt, *, backend, timeout_s) -> LlmResult
parse_structured_output(raw_text) -> OutcomePrediction
build_law_index(corpus) -> LawIndex
build_law_query(case, chunks=[]) -> str
search_law(query, top_k=10) -> list[LawHit]
deduplicate_law_evidence(items) -> list[LawEvidence]
outcome_accuracy(gold, pred) -> float
confusion_matrix_4way(gold, pred) -> Matrix
```

## Implementation Steps

1. Viết backend registry + `DeterministicRunner`; implement subprocess adapter contract cho `codex` và `claude`.
2. Chạy một prompt/case, không reuse conversation; prompt truyền qua stdin, `shell=False`.
3. Prompt trả nhãn, confidence và giải thích ngắn theo JSON schema.
4. Validate nhãn; không tin JSON CLI trực tiếp.
5. Dựng BM25/TF-IDF cho 3.352 điều luật.
6. Smoke-test vài case; sau đó mới chạy đủ 50 case chỉ bằng `case_query`.
7. Lưu prediction, backend, version CLI, prompt hash và config theo run ID.

## Success Criteria

- [x] Dự đoán đủ 50 case bằng `deterministic_v0`, không parse crash.
- [x] Có accuracy/confusion matrix baseline.
- [x] Mọi law evidence tồn tại trong corpus.
- [x] Không setup proprietary API; adapter CLI chỉ được kiểm tra bằng mock.
- [x] Mọi output CLI bị submission validator đánh dấu không hợp lệ để nộp.

## Risk Assessment

Public có 50 mẫu và nhãn mất cân bằng; không fine-tune trên cả 50 rồi tự chấm cùng tập. Codex/Claude CLI vi phạm giới hạn model của cuộc thi nếu dùng để dự đoán chính thức, nên chỉ dùng để kiểm tra thiết kế/prompt/pipeline. Adapter open-weight dưới 10B là gate bắt buộc trước submission.
