# ALQAC 2026

Thư mục làm việc cho cuộc thi **ALQAC 2026 — Legal Case Outcome Prediction with Evidence Retrieval**.

## Bắt đầu

- [Báo cáo scout cuộc thi](docs/competition-scout.md)
- [Ghi chú email ban tổ chức](docs/email-notes.md)
- [Kiểm kê dữ liệu đã tải](docs/data-manifest.md)
- Trang cuộc thi: <https://alqac2026-leaderboard.ngrok.app/>
- Tài liệu API: <https://alqac2026-leaderboard.ngrok.app/api-docs>

## Cấu trúc dự kiến

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
- [ ] Thiết kế baseline trước khi gọi Retrieval API thật.

> Cảnh báo: số lượt gọi Retrieval API bị cộng dồn qua các lần thử và có thể làm giảm điểm. Không chạy thử hàng loạt trước khi có chiến lược truy hồi và cache.
