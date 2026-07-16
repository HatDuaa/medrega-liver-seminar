# Trạng thái MVP và roadmap

Cập nhật mốc: **2026-07-16**.

## Phase 1–4: MVP đã hoàn tất

- Phase 1 — Foundation và private contract: có schema, data loader và `PrivateCase` để ngăn predictor nhìn nhãn Public.
- Phase 2 — Retrieval an toàn: có exact JSON cache, cap 2 attempt/vụ, intent ledger, khóa liên tiến trình, không retry và rate limiter toàn cục 6 giây.
- Phase 3 — Baseline reasoning và luật: có truy hồi BM25, bộ chọn bằng chứng, `deterministic_v0` chính thức và adapter proprietary CLI chỉ dùng khi phát triển.
- Phase 4 — Pipeline, submission và đánh giá: có đường chạy offline, validator nghiêm ngặt, manifest cấu hình/backend và SHA-256 provenance.
- Bộ kiểm thử đã tăng từ **35** lên **50 test** sau Quality v1.

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

Retrieval API ở mốc baseline có 50 attempt hoàn tất và 1 attempt HTTP 429. Con số này độc lập với số lần upload bài và được giữ trong ledger để kiểm soát ngân sách.

## Phase 5: Quality v1 đã hoàn tất, chưa upload

Quality v1 đã triển khai query `decision_v1`, xếp hạng nguồn phán quyết, resolver `Điều N + tên luật`, diagnostics theo nhãn và đường chạy đánh giá chéo dev-only.

| Backend/cấu hình | Cách đo | Accuracy |
|---|---|---:|
| `deterministic_v0` | Public baseline đã nộp | 40% |
| `deterministic_v1` | Offline, cache `decision_v1` | 40% |
| `naive_bayes_v1` | Leave-one-out | 52% |
| NB + positive-decision override | Leave-one-out | **54%** |

Mốc 54% là đánh giá nội bộ: mỗi mẫu được dự đoán bởi mô hình không học chính nhãn của mẫu đó, nhưng vẫn dùng 49 nhãn Public còn lại. Vì quy tắc thi về việc học từ nhãn Public chưa được xác nhận, backend này bị khóa `eligible_for_submission=false`. Không có file nào được upload trong vòng Quality v1.

Retrieval ledger hiện có **100 attempt cho 50 vụ**, đúng hard cap 2 attempt/vụ: 99 hoàn tất và 1 HTTP 429. Vì vậy không gọi Retrieval API thêm nếu không có quy định/ngân sách mới từ ban tổ chức.

## Việc kế tiếp

1. Xác nhận bằng văn bản liệu nhãn Public được phép dùng để chọn/tinh chỉnh mô hình hay không.
2. Tập trung vào `PARTIAL_B`, lớp chưa có true positive trong run 54%.
3. Thử model open-weight dưới 10B hoặc đặc trưng pháp lý không học trực tiếp từ nhãn Public.
4. Cải thiện law evidence bằng đánh giá thủ công có kiểm soát; Outcome Accuracy tốt hơn chưa chứng minh Law F1 tốt hơn.
5. Chỉ tạo submission mới khi backend hợp lệ, validator qua và user phê duyệt upload.

MVP Phase 1–4 hoàn thành không đồng nghĩa đã hoàn thành cuộc thi. Điểm 0.3040 là đường cơ sở để đo các vòng cải thiện tiếp theo.
