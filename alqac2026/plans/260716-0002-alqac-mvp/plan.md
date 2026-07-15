---
title: "ALQAC 2026 MVP Implementation"
description: "Xây pipeline Private-safe từ case_query đến submission, có cache và kiểm soát ngân sách API."
status: in-progress
priority: P1
effort: 9-12d
branch: master
tags: [feature, api, experimental, critical]
blockedBy: []
blocks: []
created: 2026-07-16
source: manual-fallback-no-ck-cli
---

# ALQAC 2026 MVP Implementation

## Overview

Xây bản MVP chạy end-to-end cho ALQAC 2026. Đầu vào production chỉ gồm `case_id + case_query`; hệ thống lập truy vấn, lấy chứng cứ có cache, dự đoán một trong bốn nhãn, tìm điều luật và sinh `submission.json` hợp lệ.

Mặc định **không gọi mạng**. Chỉ gọi Retrieval API khi bật `--allow-network`; mọi request phải qua cache, rate limiter và budget guard.

## Quyết định đã chốt

- Python package + CLI; chưa làm web UI/database.
- JSON cache theo `case_id`; exact-match sau chuẩn hóa query.
- Giai đoạn prototype có adapter `codex`/`claude` CLI để kiểm tra contract dev-only; lượt nộp Public đầu tiên dùng backend thuật toán `deterministic_v0`, không dùng output proprietary.
- Output từ Codex/Claude CLI phải gắn `eligible_for_submission=false` và không dùng để nộp chính thức, vì luật cấm proprietary systems.
- Backend dự thi cuối cùng vẫn phải là model open-weight dưới 10B; adapter phải cho phép thay backend mà không đổi pipeline.
- Public Test dùng làm benchmark; production pipeline không được nhận field đáp án.
- Law retrieval local từ `corpus_law_pub.json`; baseline BM25/TF-IDF trước vector DB.
- Chỉ nộp đúng một lần lên Public leaderboard sau khi test, review và validator đều đạt; đây là thao tác đã được user phê duyệt ngày 2026-07-16.

## Kiến trúc

```text
PrivateCase(case_id, case_query)
  -> Query Planner
  -> Exact JSON Cache
  -> Budget Guard + Retrieval Client
  -> Evidence Store
  -> Outcome Predictor
  -> Case Evidence Selector
  -> Law Retriever
  -> Submission Builder + Validator
```

## Phases

| Phase | Tên | Trạng thái |
|---|---|---|
| 1 | [Foundation và chống leakage](./phase-01-foundation-private-contract.md) | Completed |
| 2 | [Cache, API client và ngân sách](./phase-02-retrieval-safety.md) | Completed |
| 3 | [Baseline reasoning và tìm luật](./phase-03-baseline-reasoning-law.md) | Completed |
| 4 | [Pipeline, submission và đánh giá](./phase-04-pipeline-submission-eval.md) | Completed |
| 5 | [Agentic retrieval có kiểm soát](./phase-05-agentic-retrieval.md) | Optional |

Tiến độ: **4/4 phase MVP hoàn tất**; Phase 5 là vòng tối ưu tùy chọn và chưa bắt đầu.

## Cấu trúc đích

```text
alqac2026/
  pyproject.toml
  configs/{default.yaml,prompts.yaml}
  src/alqac2026/
    config.py, schemas.py, data_loader.py, private_view.py
    retrieval/{client.py,cache.py,budget.py,query_planner.py}
    reasoning/{llm_runner.py,outcome_predictor.py,evidence_selector.py,pipeline.py}
    law/{corpus.py,index.py,retriever.py}
    submission/{builder.py,validator.py}
    evaluation/{metrics.py,error_analysis.py}
    cli.py
  prompts/*.txt
  scripts/*.py
  tests/{fixtures/,test_*.py}
  data/{public/,processed/,retrieval-cache/,runs/}
  submissions/
```

## Dependencies

- Dữ liệu: xem `docs/data-manifest.md`.
- Luật và API: xem `docs/competition-scout.md` và `docs/reference/`.
- Secret: `.env`; tuyệt đối không commit hoặc in token.
- Chưa cần gọi `/retrieve` để hoàn thành Phase 1 và phần lớn Phase 2.
- Dev CLI đã có trên máy: Codex CLI `0.65.0`, Claude Code `2.1.210`. Không đưa session/chat state vào prompt; mỗi case chạy isolated, structured output.

## Definition of Done

- Pipeline chạy 50 Public cases dưới chế độ Private-view.
- Không field đáp án nào lọt vào predictor.
- Cache hit không tạo network request.
- Mọi network request có log, rate limit và budget check.
- Submission đủ 50 case, đúng schema, không bịa chunk/law ID.
- Có baseline Outcome Accuracy và báo cáo lỗi theo bốn nhãn.

## Validation Log — 2026-07-16

Plan validator đạt `0 errors, 0 warnings`. Red-team contract/fact/flow review đã chốt các sửa đổi sau trước khi cook:

| Phát hiện | Quyết định áp dụng |
|---|---|
| Public law gold là chuỗi tự do, không phải `{law_id, aid}` | Không tuyên bố Law F1 offline; chỉ validate evidence thuộc corpus. |
| `/retrieve` trả `results[]`, có thể 0/1/n | Client trả danh sách chunk, chấp nhận miss và reject response sai schema. |
| Rate limit là toàn đội; timeout có thể đã tiêu lượt | Dùng lock/timestamp dùng chung, ghi intent trước POST, không tự retry. |
| Codex có thể đọc file trong repo; Claude/Codex đều không hợp lệ để nộp | Chỉ smoke-test adapter bằng fixture cô lập; official builder chặn backend proprietary. |
| Cờ eligibility do caller truyền không đáng tin | Official builder tự suy từ backend registry và `RunManifest`. |
| Draft và bài nộp dễ bị trộn | Tách `draft.json` khỏi `submission.json`; official validator không có debug bypass. |
| Chưa có model open-weight `<10B` trên máy | Lượt Public đầu dùng `deterministic_v0` (BM25 + rule), hợp lệ về loại hệ thống; model open-weight là vòng sau. |
| Chưa biết `n_i` của từng vụ | Hard cap độc lập: tối đa 2 network call/case cho lượt baseline; cache hit không tính call mới. |
| Pilot đúng mốc 5 giây nhận HTTP 429 | Tăng khoảng cách client lên 6 giây; không retry attempt đã thất bại. |

### Phạm vi cook hiện tại

- Thực hiện Phase 1–4, chạy một lượt 50 Public case dưới Private-view.
- Retrieval tối đa 2 query/case, không retry tự động, có thể dừng thấp hơn nếu cache/evidence đủ.
- Phase 5 agentic retrieval giữ `Optional`, chưa triển khai trong lượt đầu.
- Sau quality gate, upload duy nhất một file Public bằng trình duyệt Edge và lưu lại phản hồi server.

## Kết quả lượt Public đầu tiên

- Server pre-validation: `valid=true`, `track=public`, đủ 50 case.
- Upload bằng Edge: đúng một lần; Final Score `0.3040`.
- Breakdown: Outcome Accuracy `40.0%`, Penalized Case Recall `5.3%`, Micro Law F1 `13.5%`.
- Law precision/recall: `26.0% / 9.1%`.
- Retrieval ledger: 50 attempt hoàn tất, 1 HTTP 429 ở pilot 5 giây; không retry.
- Code gate: 35/35 test pass; re-review PASS 8.7/10, không còn Critical.

## Rủi ro chính

- Public–Private lệch format: khóa bằng `PrivateCase` và leakage test.
- API call không reset: `allow_network=False` mặc định, không retry mù.
- Public chỉ 50 mẫu và có nhãn: tránh fine-tune/overfit sớm.
- Local call count không bằng server count: coi budget local là cận dưới.
- Email và website khác giới hạn submission: xác nhận server trước khi nộp.
- Codex/Claude CLI giúp prototype nhanh nhưng không hợp lệ để thi: khóa bằng backend metadata và submission validator.
