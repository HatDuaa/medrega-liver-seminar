---
date: 2026-07-16
session: alqac-mvp-first-submission
---

# Journal: 2026-07-16 — ALQAC MVP và lần nộp đầu

## Bối cảnh

Hoàn thiện một vòng MVP từ phản biện plan, triển khai, gọi Retrieval API, kiểm thử đến nộp leaderboard.

## Đã xảy ra

- Red-team plan chặn các rủi ro: rò nhãn Public, backend dev không hợp lệ để nộp, API tính lượt gọi và output thiếu provenance.
- Triển khai Phase 1–4: schema/config, cache và Retrieval API client, baseline suy luận–luật, pipeline đánh giá và xuất submission.
- Pilot chờ 5 giây gặp HTTP 429; tăng lên 6 giây và không retry. Kết quả cache: 50 case hoàn tất, 1 lần 429.
- Review phát hiện lỗi giới hạn lượt gọi, provenance và tranh chấp khi ghi cache; đã sửa và chạy đạt 35 test.
- Upload bằng Edge đúng một lần. Leaderboard trả Final Score `0.3040`, Outcome Accuracy `40.0%`, Penalized Case Recall `5.3%`, Micro Law F1 `13.5%`, Law Precision `26.0%`, Law Recall `9.1%`; local outcome accuracy `0.40` (`20/50`).

## Phản tư

Pipeline đã chạy trọn vòng và giữ được kỷ luật chỉ nộp một lần. Tuy nhiên baseline lệch mạnh về `A_WIN`, nên accuracy `0.40` chưa phản ánh khả năng phân biệt đủ bốn nhãn.

## Quyết định

| Quyết định | Lý do | Tác động |
|---|---|---|
| Giữ khoảng cách API 6 giây, không retry | Tránh thêm 429 và tốn lượt gọi | Chậm hơn nhưng dễ kiểm soát ngân sách |
| Cache JSON có provenance và ghi an toàn | Dễ quan sát, tái lập và tránh ghi đè | Chạy lại không cần gọi API |
| Xem `0.3040` là mốc baseline | Hệ thống đã hợp lệ nhưng chất lượng còn thấp | Tập trung nâng outcome, luật và retrieval |

## Tiếp theo

- Giảm thiên lệch `A_WIN`, cải thiện phân loại outcome bốn nhãn.
- Nâng ánh xạ điều luật và chất lượng truy vấn retrieval.
- Phân tích lỗi theo case trước lần nộp tiếp theo.
