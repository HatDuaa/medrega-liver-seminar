---
phase: 5
title: "Quality v1: decision retrieval, source-aware outcome và law citations"
status: completed
priority: P1
effort: 1d
dependencies: [4]
---

# Phase 05: Quality v1 không upload leaderboard

## Mục tiêu

Nâng baseline Public `0.40` outcome accuracy bằng cách sửa đúng ba nút thắt đã đo:
query dài kéo 41/50 chunk về `case_fact`, 42/50 vụ fallback về `A_WIN`, và law
retrieval không hiểu tên luật/số Điều. Vòng này chỉ sinh artifact draft/offline; tuyệt đối
không ghi đè hoặc upload `submissions/submission.json`.

## Contract đã chốt

- Predictor production chỉ nhận `PrivateCase(case_id, case_query)` và chunk đã cache.
- Query strategy `decision_v1` phải ngắn, không nối tên người/số tiền/toàn bộ case query.
- Giữ `legacy_v0` để đọc lại cache cũ và tái lập submission đầu.
- Không vượt 2 API attempt/vụ; `case_4101` đã đủ 2 nên không được gọi thêm.
- Codex/Claude chỉ được tạo draft dev-only, luôn `eligible_for_submission=false`.
- Không cài model/API LLM mới và không upload leaderboard trong phase này.

## Phạm vi triển khai

1. **Decision retrieval**
   - Version query planner thành `legacy_v0` và `decision_v1`.
   - Query v1 nhắm `quyết định` và `nhận định/HĐXX`; tối đa hai query khác nhau.
   - CLI nhận `--query-strategy`; manifest/trace ghi strategy.

2. **Source-aware outcome**
   - Tách câu mang giọng phán quyết khỏi lời yêu cầu/trình bày của đương sự.
   - Dùng score theo tín hiệu A/B/partial; không để fallback thay đổi chỉ confidence.
   - Giữ deterministic và structured rationale để audit.

3. **Law citation resolver**
   - Bổ sung metadata số Điều suy ra từ thứ tự trong từng law corpus.
   - Chuẩn hóa alias các luật có trong corpus; trích dẫn trực tiếp được ưu tiên trước BM25.
   - Law BM25 vẫn là fallback và kết quả luôn phải thuộc corpus.

4. **Quality diagnostics**
   - Báo distribution dự đoán, confusion/per-label, fallback rate và source hit.
   - So sánh run với baseline `20260715T175840Z`.
   - Draft output đặt dưới `data/runs/<run_id>/`, không dưới `submissions/`.

## Acceptance criteria

- [x] Unit test khóa query v1 không chứa case focus và legacy v0 không đổi.
- [x] Test outcome phân biệt lời đương sự với phán quyết và phủ đủ bốn nhãn.
- [x] Test citation `Điều N + tên luật` ánh xạ đúng `(law_id, aid)`; không bịa pair.
- [x] Test cũ và test mới đều qua; CLI offline không mở network.
- [x] Có báo cáo offline so baseline, tách rõ kết quả dev-only khỏi kết quả leaderboard.
- [x] Review không còn Critical/Important; không có file leaderboard nào được upload.

## Trình tự

1. Viết test đỏ cho query, outcome, luật và diagnostics.
2. Implement từng module, giữ public signatures tương thích bằng default/keyword mới.
3. Chạy offline trên cache cũ; chỉ sau review query mới cân nhắc network retrieval.
4. Nếu gọi API, gọi tối đa một query `decision_v1` cho 49 vụ còn ngân sách, tuần tự 6 giây.
5. Chạy deterministic draft và Codex/Claude draft nếu CLI sẵn; proprietary draft không được
   chuyển thành official artifact.
6. Review diff, full test, cập nhật docs/journal và commit.

## Out of scope

- Upload/nộp leaderboard.
- Fine-tune hoặc cài model open-weight.
- Tăng hard cap quá 2 attempt/vụ.
- Dùng Public verdict/reasoning/label làm input predictor.

## Kết quả hoàn tất

- `decision_v1` đã lấy thêm đúng một truy vấn cho 49 vụ còn ngân sách; `case_4101` được bỏ qua. Ledger hiện có 100 attempt cho 50 vụ, mỗi vụ đúng 2 attempt: 99 hoàn tất và 1 HTTP 429 cũ. Không còn ngân sách API cục bộ cho vòng tiếp theo.
- Deterministic source-aware đạt `40%` Outcome Accuracy trên Public, chưa cải thiện so với baseline.
- Naive Bayes leave-one-out đạt `52%`; thêm một override hẹp cho câu phán quyết dương tính đạt `54%` (`27/50`), tăng 14 điểm phần trăm so với baseline `40%`.
- Kết quả `54%` chỉ là đánh giá chéo dev-only. Backend này có `eligible_for_submission=false` vì chưa xác nhận luật có cho phép học/tinh chỉnh từ nhãn Public hay không.
- Lớp `PARTIAL_B` vẫn là điểm yếu chính: chưa có true positive trong run tốt nhất. Đây là mục tiêu bắt buộc của vòng kế tiếp.
- Codex CLI cục bộ quá cũ so với model tài khoản hỗ trợ; Claude CLI trả 401. Không đổi credential và không nâng cấp global tool trong vòng này.
- Không upload leaderboard, không ghi đè submission chính thức; SHA-256 của file đã nộp vẫn là `06D5B124BFA2212083A3A0BA545346B44E90257D722BC48D017CE093CA91AC71`.
