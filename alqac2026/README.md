# ALQAC 2026

Thư mục làm việc cho cuộc thi **ALQAC 2026 — Legal Case Outcome Prediction with Evidence Retrieval**.

## Bắt đầu

- [Báo cáo scout cuộc thi](docs/competition-scout.md)
- [Ghi chú email ban tổ chức](docs/email-notes.md)
- [Kiểm kê dữ liệu đã tải](docs/data-manifest.md)
- [Kiến trúc và rào chắn an toàn](docs/architecture.md)
- [Trạng thái MVP và roadmap](docs/mvp-status.md)
- Trang cuộc thi: <https://alqac2026-leaderboard.ngrok.app/>
- Tài liệu API: <https://alqac2026-leaderboard.ngrok.app/api-docs>

## Chạy baseline

Yêu cầu Python 3.11 trở lên. Package chỉ dùng thư viện chuẩn, không cần cài model hay dependency ngoài.

```powershell
$env:PYTHONPATH = (Resolve-Path 'src').Path
python -m alqac2026.cli inspect-data
python -m unittest discover -s tests -v
```

Retrieval mặc định bị khóa mạng. Khi chủ động lấy cache, chạy theo batch nhỏ; mỗi vụ có hard cap 2 network call. Client chờ 6 giây giữa hai POST để có biên an toàn so với giới hạn server 5 giây:

```powershell
python -m alqac2026.cli retrieve-public --start 0 --limit 5 --max-queries 2 --allow-network
```

Sau khi cache đã sẵn sàng, tạo và kiểm tra bài nộp hoàn toàn offline:

```powershell
python -m alqac2026.cli run-public
python -m alqac2026.cli validate-submission --input submissions/submission.json
```

`submission.json` chỉ được tạo bởi backend `deterministic_v0` hoặc backend hợp lệ khác trong registry. Codex/Claude CLI là adapter phát triển, luôn bị official validator từ chối.

## Cấu trúc hiện tại

- `docs/`: luật thi, thông báo, quyết định và ghi chú.
- `src/`: mã nguồn hệ thống dự thi.
- `data/`: dữ liệu cục bộ; không đưa dữ liệu nhạy cảm hoặc dữ liệu lớn lên Git.
- `submissions/`: file nộp cục bộ; không commit token hay bản nộp chứa thông tin riêng.

## Trạng thái

- [x] Scout website, luật, API và bảng xếp hạng ngày 2026-07-15.
- [x] Ghi nhận các email nhìn thấy trong ảnh Outlook.
- [x] Đọc đầy đủ chuỗi email `[ALQAC-2026] Competition Registration`.
- [x] Tải Public Test và corpus luật; kiểm tra JSON, schema và checksum.
- [x] Lưu token đội trong `.env` cục bộ, không đưa lên Git.
- [ ] Xác minh deadline, lịch Public/Private Test và yêu cầu báo cáo cuối kỳ.
- [x] Thiết kế và chạy baseline trước khi gọi Retrieval API thật.
- [x] Có MVP Private-view, cache/budget/rate limiter, BM25 luật và strict submission validator.

## Mốc Public đầu tiên

MVP Phase 1–4 đã qua **35 kiểm thử** và được nộp Public đúng **một lần** bằng backend chính thức `deterministic_v0`. Điểm tổng là **0.3040**, gồm Accuracy **40%**, Case Recall **5.3%**, Law F1 **13.5%**, Precision **26%** và Recall **9.1%**.

Retrieval ledger ghi nhận **50 lượt hoàn tất** và **1 lượt HTTP 429**. Đây là số lượt gọi Retrieval API, không phải số lần nộp bài; client hiện giữ khoảng cách toàn cục 6 giây và không tự retry.

Đây mới là mốc baseline. Phase 5 sẽ tập trung cải thiện chất lượng truy hồi, bằng chứng và dự đoán; dự án chưa hoàn thành cuộc thi.

## An toàn vận hành

- Không đưa raw Public row vào predictor; predictor chỉ nhận `PrivateCase(case_id, case_query)`.
- Không retry POST tự động. Timeout được ghi `unknown_delivery` vì server có thể đã tính lượt.
- Cache là JSON quan sát được theo từng `case_id`; evidence chỉ hợp lệ nếu xuất hiện trong raw response của đúng vụ.
- `.env`, dữ liệu, run trace và submission đều bị Git ignore.

> Cảnh báo: số lượt gọi Retrieval API bị cộng dồn qua các lần thử và có thể làm giảm điểm. Không chạy thử hàng loạt trước khi có chiến lược truy hồi và cache.
