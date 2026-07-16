---
title: "ALQAC Quality v1: từ 40% lên 54% offline"
date: 2026-07-16
tags: [alqac, retrieval, evaluation, review]
---

# ALQAC Quality v1: từ 40% lên 54% offline

## Bối cảnh

Baseline đã nộp đạt 40% Outcome Accuracy nhưng có ba dấu hiệu yếu: truy vấn quá dài thường lấy `case_fact`, bộ dự đoán hay fallback về `A_WIN`, và law retrieval chưa hiểu trích dẫn Điều/tên luật. Vòng này được yêu cầu tự cải thiện, review, không upload leaderboard.

## Những gì đã làm

- Giữ `legacy_v0` để tái lập kết quả cũ và thêm `decision_v1` chỉ tìm quyết định/nhận định của HĐXX.
- Ưu tiên nguồn mang giọng phán quyết, tránh coi lời yêu cầu của đương sự là kết luận của tòa.
- Thêm resolver `Điều N + tên luật` trước BM25.
- Thêm diagnostics theo nhãn, fallback rate, CLI draft và leave-one-out.
- Dùng đúng một query mới cho 49 vụ còn ngân sách; không gọi lại `case_4101`.
- Thử Codex/Claude CLI trong chế độ dev-only nhưng dừng an toàn khi client/auth không dùng được.
- Thử Naive Bayes unigram và một override hẹp cho câu phán quyết dương tính.

## Kết quả

| Cấu hình | Accuracy |
|---|---:|
| Baseline đã nộp | 40% |
| Deterministic v1 | 40% |
| Naive Bayes leave-one-out | 52% |
| NB + override hẹp | **54%** |

54% tương ứng 27/50 vụ, tăng 14 điểm phần trăm so với baseline. Tuy nhiên `PARTIAL_B` vẫn không có true positive. Outcome tốt hơn cũng chưa chứng minh law evidence tốt hơn.

## Review và quyết định

- Không dùng kết quả học từ nhãn Public để nộp bài khi quy tắc này còn mơ hồ; backend bị khóa dev-only.
- Không trộn cache legacy với decision cache vì thử nghiệm cho kết quả kém hơn.
- Không nâng cấp global Codex CLI hoặc sửa credential Claude ngoài phạm vi task.
- Không upload và không ghi đè file submission đầu tiên.
- Không gọi API thêm: cả 50 vụ đã đạt hard cap 2 attempt/vụ.

## Bài học

Thay đổi deterministic hợp lý về mặt ngữ nghĩa chưa đủ làm tăng accuracy. Tín hiệu từ ngôn ngữ case query có thể học được, nhưng tập 50 mẫu quá nhỏ và mất cân bằng khiến kết quả dễ dao động, đặc biệt với `PARTIAL_B`. Vòng tiếp theo cần tách hai mục tiêu: tính hợp lệ theo luật thi và khả năng tổng quát hóa sang Private Test.

## Việc tiếp theo

1. Xác nhận chính sách dùng nhãn Public.
2. Phân tích riêng các lỗi `PARTIAL_B`.
3. Thử model open-weight dưới 10B hoặc đặc trưng pháp lý không phụ thuộc nhãn Public.
4. Chỉ chuẩn bị submission mới sau review, validator và phê duyệt upload riêng.
