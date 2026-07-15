---
title: ALQAC 2026 Email Notes
date: 2026-07-15
status: verified-from-full-thread
source: outlook-thread
---

# Ghi chú email ALQAC 2026

## Phạm vi

Đã đọc toàn văn thông báo của Ban tổ chức trong chuỗi Outlook ngày 2026-07-15. Token đội đã được trích nhưng chỉ lưu trong `.env` cục bộ và không xuất hiện trong tài liệu này.

Không lưu mã xác nhận, token đội, địa chỉ email cá nhân hoặc thông tin nhạy cảm vào repo.

## Chuỗi email nhìn thấy

Chủ đề: **`[ALQAC-2026] Competition Registration`**.

| Thời điểm hiển thị | Người gửi | Nội dung nhìn thấy | Trạng thái |
|---|---|---|---|
| 2026-06-29 20:50 | Le Vy | Email đăng ký đội gửi Thầy Trung Vo và Ban tổ chức; phần xem trước nhắc ALQAC 2026 gắn với KSE 2026 tại Kanazawa, Japan và bắt đầu liệt kê thông tin đội. | Cần đọc toàn văn |
| 2026-06-29 20:58 | Trung Vo | Giải thích vai trò Public Test và định dạng tối giản, nghiêm ngặt của Private Test. | Đã đọc |
| 2026-06-30 09:08 | Le Vy | Chuyển tiếp thông báo tài nguyên, token, giới hạn model/API, dữ liệu và submission. | Đã đọc |

Danh sách thư bên trái còn cho thấy một thư chủ đề bắt đầu bằng `[ALQAC-2026] Competiti...` từ Lê Thị Tường Vy vào ngày 2026-06-28, nhưng ảnh không hiển thị đủ chủ đề/nội dung để kết luận đó là thư riêng hay cùng chuỗi.

## Thông tin đã xác nhận

- Đội đã có trao đổi đăng ký với Ban tổ chức.
- Public Test có đủ 50 vụ và chủ yếu dùng để minh họa format, thử retrieval/reasoning và benchmark framework.
- Private Test là giai đoạn quyết định và chỉ cung cấp `case_id` cùng `case_query`.
- Không có training data trong mùa thi này; chỉ có Public Test và Private Test.
- Model dự thi phải là **open-weight dưới 10 tỷ tham số**.
- Cấm sử dụng hệ thống proprietary như ChatGPT, Claude hoặc Gemini trong hệ thống dự thi.
- Retrieval API bị giới hạn 1 request mỗi 5 giây cho một đội.
- Email ngày 2026-06-30 nói tối đa 3 submission/ngày/đội. Website hiện tại hiển thị giới hạn khác, nên cần theo giới hạn đang được server thực thi và hỏi Ban tổ chức nếu cần.
- Bộ nhãn chính thức đã được mở rộng từ 2 lên 4 nhãn.
- Public Test từng có lỗi trùng `case_id`; bản Drive hiện tại là bản đã sửa. Kiểm tra local xác nhận 50 ID duy nhất.
- Lịch thi vẫn đang được Ban tổ chức xem xét tại thời điểm gửi email.

## Checklist cần trích từ email đầy đủ

- [x] Tên đội đã đăng ký: `Out of tokens`.
- [x] Nhận thư dành cho các đội tham dự và token riêng của đội.
- [ ] Deadline Public Test, Private Test và final submission.
- [x] Link dữ liệu và token đội đã được tiếp nhận; token không ghi trong Markdown.
- [x] Giới hạn model và Retrieval API.
- [ ] Yêu cầu paper, báo cáo kỹ thuật hoặc tham dự KSE 2026.
- [x] Quy định model: open-weight dưới 10B; cấm ChatGPT/Claude/Gemini.
- [ ] Kênh hỗ trợ chính thức và cách liên hệ Ban tổ chức.

## Bảo mật

Khi đọc lại email, chỉ lưu thông tin phục vụ cuộc thi. Token/API key, mã xác nhận và thông tin cá nhân phải để ngoài Git, tốt nhất trong biến môi trường cục bộ.
