---
report: code-review
date: 2026-07-16
scope: quality-v1
verdict: pass-with-known-limitations
---

# Code review Quality v1

## Kết luận

Không còn phát hiện mức Critical hoặc Important. Thay đổi đáp ứng yêu cầu không upload, giữ private contract và không vượt hard cap API.

## Kiểm tra chính

- Query strategy được version hóa; cache legacy vẫn tái lập được.
- `decision_v1` không đưa case focus dài vào truy vấn.
- Lời yêu cầu của đương sự không còn được xem ngang với phán quyết của tòa.
- Citation resolver chỉ trả `(law_id, aid)` có trong corpus.
- Draft/dev output không ghi vào `submissions/`.
- Backend registry, không phải cờ caller, quyết định eligibility.
- Prompt dev không chứa nhãn hoặc lời giải Public.

## Sửa trong review

- Resolve đúng file `.cmd` trên Windows và ép UTF-8 cho subprocess Codex.
- Trả chi tiết lỗi CLI đủ để chẩn đoán nhưng không in secret.
- Đánh dấu Naive Bayes dev-only vì chính sách dùng nhãn Public chưa rõ.
- Bỏ hướng trộn cache legacy/decision sau khi metric giảm.

## Hạn chế còn lại

- 54% là leave-one-out trên 50 mẫu Public, chưa phải bằng chứng chắc chắn cho Private Test.
- `PARTIAL_B` có recall bằng 0 trong run tốt nhất.
- Retrieval budget cục bộ đã hết; không thể thử query mới an toàn.
- Codex CLI cục bộ và Claude auth chưa chạy được; không ảnh hưởng đường deterministic/dev NB.
