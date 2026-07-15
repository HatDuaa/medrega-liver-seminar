---
title: "ALQAC 2026 MVP Implementation"
description: "Xây pipeline Private-safe từ case_query đến submission, có cache và kiểm soát ngân sách API."
status: pending
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
- Model dự thi là local open-weight dưới 10B; cấm ChatGPT/Claude/Gemini.
- Public Test dùng làm benchmark; production pipeline không được nhận field đáp án.
- Law retrieval local từ `corpus_law_pub.json`; baseline BM25/TF-IDF trước vector DB.
- Không tự submit leaderboard trong MVP.

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
| 1 | [Foundation và chống leakage](./phase-01-foundation-private-contract.md) | Pending |
| 2 | [Cache, API client và ngân sách](./phase-02-retrieval-safety.md) | Pending |
| 3 | [Baseline reasoning và tìm luật](./phase-03-baseline-reasoning-law.md) | Pending |
| 4 | [Pipeline, submission và đánh giá](./phase-04-pipeline-submission-eval.md) | Pending |
| 5 | [Agentic retrieval có kiểm soát](./phase-05-agentic-retrieval.md) | Optional |

## Cấu trúc đích

```text
alqac2026/
  pyproject.toml
  configs/{default.yaml,prompts.yaml}
  src/alqac2026/
    config.py, schemas.py, data_loader.py, private_view.py
    retrieval/{client.py,cache.py,budget.py,query_planner.py}
    reasoning/{outcome_predictor.py,evidence_selector.py,pipeline.py}
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

## Definition of Done

- Pipeline chạy 50 Public cases dưới chế độ Private-view.
- Không field đáp án nào lọt vào predictor.
- Cache hit không tạo network request.
- Mọi network request có log, rate limit và budget check.
- Submission đủ 50 case, đúng schema, không bịa chunk/law ID.
- Có baseline Outcome Accuracy và báo cáo lỗi theo bốn nhãn.

## Rủi ro chính

- Public–Private lệch format: khóa bằng `PrivateCase` và leakage test.
- API call không reset: `allow_network=False` mặc định, không retry mù.
- Public chỉ 50 mẫu và có nhãn: tránh fine-tune/overfit sớm.
- Local call count không bằng server count: coi budget local là cận dưới.
- Email và website khác giới hạn submission: xác nhận server trước khi nộp.
