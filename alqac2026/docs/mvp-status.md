# Trạng thái MVP và roadmap

Cập nhật mốc: **2026-07-16**.

## Phase 1–4: MVP đã hoàn tất

- Phase 1 — Foundation và private contract: có schema, data loader và `PrivateCase` để ngăn predictor nhìn nhãn Public.
- Phase 2 — Retrieval an toàn: có exact JSON cache, cap 2 attempt/vụ, intent ledger, khóa liên tiến trình, không retry và rate limiter toàn cục 6 giây.
- Phase 3 — Baseline reasoning và luật: có truy hồi BM25, bộ chọn bằng chứng, `deterministic_v0` chính thức và adapter proprietary CLI chỉ dùng khi phát triển.
- Phase 4 — Pipeline, submission và đánh giá: có đường chạy offline, validator nghiêm ngặt, manifest cấu hình/backend và SHA-256 provenance.
- Bộ kiểm thử hiện có: **35 test**, đã qua ở mốc MVP.

## Kết quả Public đầu tiên

Bài baseline được nộp lên leaderboard đúng **một lần**:

| Chỉ số | Kết quả |
|---|---:|
| Điểm tổng | 0.3040 |
| Accuracy | 40.0% |
| Case Recall | 5.3% |
| Law F1 | 13.5% |
| Precision | 26.0% |
| Recall | 9.1% |

Retrieval API có 50 attempt hoàn tất và 1 attempt HTTP 429. Con số này độc lập với số lần upload bài và được giữ trong ledger để kiểm soát ngân sách.

## Phase 5: bước tiếp theo

Ưu tiên kế tiếp là cải thiện chất lượng, không mở rộng hạ tầng trước khi có phân tích lỗi:

1. Phân tích lỗi theo outcome, thiếu `case_evidence` và sai/thiếu `law_evidence`.
2. Cải thiện query planner và chọn bằng chứng trên cache hiện có trước khi cân nhắc thêm API call.
3. Cải thiện truy hồi luật, đặc biệt chuẩn hóa tham chiếu và xếp hạng điều/khoản liên quan.
4. So sánh baseline quyết định với model open-weight dưới 10B, nhưng vẫn giữ cùng private contract và validator.
5. Chỉ tạo mốc submission tiếp theo khi test qua, artifact hash khớp và có cải thiện offline đủ rõ.

MVP Phase 1–4 hoàn thành không đồng nghĩa đã hoàn thành cuộc thi. Điểm 0.3040 là đường cơ sở để đo các vòng cải thiện tiếp theo.
