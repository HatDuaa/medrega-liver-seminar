---
phase: 2
title: "Cache, API client và ngân sách"
status: completed
priority: P1
effort: 2d
dependencies: [1]
---

# Phase 02: Cache, API client và ngân sách

## Overview

Tạo lớp truy hồi an toàn. Cache exact JSON, rate limit, log và budget guard phải hoàn thành trước request thật đầu tiên.

## Requirements

- `allow_network=False` mặc định.
- Cache key = `case_id + normalized_query`.
- Không semantic-cache tự động.
- Server giới hạn 1 request/5 giây/đội; client dùng khoảng cách 6 giây để tránh lỗi biên `429`.
- Không retry tự động lỗi `403`, `422`, `429`.
- Không tự retry bất kỳ POST nào, kể cả timeout/503/connection reset.
- Rate limiter và ledger dùng chung toàn project, không chỉ theo từng case/process.
- Ghi file cache atomic; không làm hỏng cache cũ khi process chết.

## Architecture

```text
retrieve(case_id, query)
  -> normalize/query key
  -> cache lookup
  -> network flag
  -> local budget check
  -> rate limiter
  -> POST /retrieve
  -> atomic cache write + audit log
```

## Related Code Files

- Create: `alqac2026/src/alqac2026/retrieval/{cache.py,budget.py,client.py,query_planner.py}`
- Create: `alqac2026/tests/{test_cache.py,test_budget.py,test_retrieval_client.py}`
- Create local: `alqac2026/data/{retrieval-cache,runs}/`

## Helper Contracts

```python
normalize_query(query) -> str
make_cache_key(case_id, normalized_query) -> str
load_case_cache(case_id) -> CaseCache
find_cached_response(case_id, query) -> list[RetrievedChunk] | None
save_cache_atomic(case_id, cache) -> None
can_call(case_id, max_calls) -> bool
record_api_call(case_id, query, status) -> None
retrieve(case_id, query, *, allow_network=False) -> list[RetrievedChunk]
```

## Implementation Steps

1. Chuẩn hóa Unicode, chữ thường, khoảng trắng và dấu câu cuối.
2. Thiết kế JSON cache mỗi case; giữ raw response.
3. Viết atomic write `.tmp -> rename`.
4. Thêm local call ledger; ghi `intent` trước POST rồi chuyển sang `completed` hoặc `unknown_delivery`; đây chỉ là cận dưới của server count.
5. Tạo rate limiter và timeout.
6. Mock API; chứng minh cache hit tạo 0 network call.
7. Chỉ sau khi test pass mới cân nhắc một request thật có chủ đích.
8. Test response `results=[]`, nhiều item, non-JSON, status bất ngờ và field sai type.

## Success Criteria

- [x] Cache hit hoàn toàn offline.
- [x] Cache miss bị chặn nếu không bật network.
- [x] Request thứ hai cách request trước ít nhất 5 giây (client dùng 6 giây).
- [x] Token không hiện trong exception/log.
- [x] Mọi test dùng mock, không tiêu lượt thật.

## Risk Assessment

Server có thể đã tính request dù client nhận timeout. Không retry tự động khi trạng thái không chắc chắn; log `unknown_delivery` để xem thủ công.
