# Kiến trúc MVP ALQAC 2026

Tài liệu này mô tả kiến trúc đã triển khai cho MVP Phase 1–4. Mục tiêu chính là tạo một đường chạy có thể kiểm tra lại, ngăn rò nhãn Public và không lãng phí lượt gọi Retrieval API.

## Luồng xử lý

1. `data_loader` đọc dữ liệu, sau đó `private_view` chỉ chuyển tiếp `PrivateCase(case_id, case_query)` vào pipeline. Các trường nhãn và lời giải trong Public không đi vào predictor.
2. `query_planner` có hai strategy: `legacy_v0` để tái lập cache/bài đầu, và `decision_v1` tạo truy vấn ngắn nhắm vào quyết định/nhận định của HĐXX. `RetrievalClient` ưu tiên đọc cache; chỉ gọi mạng khi người chạy bật `--allow-network` rõ ràng.
3. Kết quả API được lưu nguyên dạng JSON theo `case_id` và khóa truy vấn đã chuẩn hóa. Cache chỉ hit khi khóa khớp chính xác, không dùng cosine hay so gần đúng. Việc giữ raw response giúp quan sát lại chính xác dữ liệu server từng trả về.
4. Pipeline ưu tiên đoạn mang giọng phán quyết hơn lời yêu cầu của đương sự, truy hồi điều luật bằng resolver trích dẫn chính xác trước rồi mới fallback BM25, sau đó dự đoán nhãn.
5. `submission.builder` tạo file kết quả; `submission.validator` kiểm tra schema, đủ case, cặp điều luật tồn tại và mọi `chunk_id` đều xuất hiện trong raw cache của đúng vụ.
6. Mỗi lần chạy sinh manifest chứa cấu hình và metadata backend. Manifest đi kèm SHA-256 của file submission để phát hiện file bị thay đổi sau khi tạo.

## Rào chắn Retrieval API

- Cache là JSON đọc được trực tiếp, ghi theo kiểu atomic để tránh file dở dang.
- Hạn mức cứng là tối đa 2 network attempt cho mỗi `case_id`.
- Ledger ghi trạng thái `intent` trước khi POST. Vì vậy cả timeout hoặc lỗi không rõ server đã nhận hay chưa vẫn tiêu thụ ngân sách an toàn.
- Không tự retry POST. Người chạy phải xem ledger và quyết định thủ công.
- Rate limiter dùng trạng thái và file lock chung giữa các tiến trình, giữ ít nhất 6 giây giữa hai attempt toàn project.
- Lock theo từng vụ ngăn hai tiến trình cùng gọi lại một cache miss.

Ở mốc Quality v1, ledger có tổng cộng 100 attempt cho 50 vụ: 99 hoàn tất và 1 attempt cũ nhận HTTP 429. Mỗi vụ đã chạm hard cap 2; hiện không còn lượt Retrieval API cục bộ để thử thêm. Khoảng cách toàn cục 6 giây vẫn là cấu hình vận hành bắt buộc nếu ban tổ chức cấp ngân sách mới.

## Backend và tính hợp lệ

- `deterministic_v0` là backend thuật toán chính thức của MVP và được phép tạo submission.
- Adapter Codex CLI và Claude CLI chỉ phục vụ phát triển. Đây là model độc quyền nên registry luôn đánh dấu `eligible_for_submission=false`; official validator sẽ từ chối output của chúng.
- `naive_bayes_v1` dùng nhãn Public trong leave-one-out để đo tín hiệu có thể học được. Nó cũng bị đánh dấu `eligible_for_submission=false` cho đến khi xác nhận quy tắc thi cho phép dùng nhãn Public để huấn luyện/chọn mô hình.
- Backend nộp bài tiếp theo phải tuân thủ luật cuộc thi, gồm yêu cầu model open-weight dưới 10B nếu dùng LLM.

## Artifact phát triển

- `run-draft` và `run-cv-draft` chỉ ghi vào `data/runs/<run_id>/`; chúng không ghi vào `submissions/`.
- `run-cv-draft` huấn luyện từng fold bằng 49 mẫu và giữ mẫu còn lại hoàn toàn ngoài tập học. Metric này dùng để so sánh nội bộ, không thay thế leaderboard.
- Backend dev-only không thể đi qua official submission validator, dù caller tự truyền cờ eligibility khác.

## Vị trí mã nguồn

- `src/alqac2026/private_view.py`: rào chắn chống rò dữ liệu Public.
- `src/alqac2026/retrieval/`: cache, ledger ngân sách, rate limiter và HTTP client.
- `src/alqac2026/law/`: nạp corpus, lập chỉ mục và truy hồi điều luật.
- `src/alqac2026/reasoning/`: chọn bằng chứng, dự đoán và adapter backend.
- `src/alqac2026/submission/`: tạo artifact, manifest và kiểm tra bài nộp.
- `src/alqac2026/evaluation/`: metric offline và khung phân tích lỗi.
- `tests/`: kiểm thử contract, an toàn retrieval và pipeline offline.

Không đưa token, dữ liệu tải về, cache, ledger, trace chạy hay submission lên Git.
