---
title: ALQAC 2026 Competition Scout
date: 2026-07-15
status: initial
sources: public-website-and-email-screenshot
---

# Scout cuộc thi ALQAC 2026

## Tóm tắt

ALQAC 2026 là bài toán dự đoán kết quả vụ án pháp lý tiếng Việt có kèm truy hồi bằng chứng. Hệ thống phải vừa chọn đúng một trong bốn kết quả, vừa chỉ ra đoạn chứng cứ trong hồ sơ vụ án và điều luật Việt Nam làm căn cứ.

Điểm quan trọng nhất về chiến lược: lượt gọi Retrieval API được ghi nhận cộng dồn và gọi quá nhiều sẽ làm giảm điểm truy hồi. Vì vậy cần cache mọi kết quả và thiết kế truy vấn trước khi chạy quy mô lớn.

## Nhiệm vụ

Bốn nhãn dự đoán được chấm khớp chính xác:

| Nhãn | Nghĩa thường |
|---|---|
| `A_WIN` | Nguyên đơn thắng |
| `PARTIAL_A_WIN` | Nguyên đơn thắng một phần |
| `B_WIN` | Bị đơn thắng |
| `PARTIAL_B_WIN` | Bị đơn thắng một phần |

Public Test tại thời điểm scout có **50 vụ**.

### Khác biệt Public và Private

- Public Test được cung cấp đầy đủ nội dung, phán quyết, lập luận và nhãn để thử framework.
- Private Test chỉ cung cấp `case_id` và `case_query`; đây là format quyết định.
- Mùa thi này không có training set riêng.
- Khi xây pipeline phải mô phỏng Private bằng cách chỉ đưa `case_id + case_query` cho agent; các trường đầy đủ của Public chỉ dùng làm nhãn đánh giá offline.

### Giới hạn model

- Chỉ dùng model open-weight dưới 10 tỷ tham số.
- Không dùng ChatGPT, Claude, Gemini hoặc hệ thống proprietary trong hệ thống dự thi.

## Cách tính điểm

```text
FinalScore = 0.70 × OutcomeAccuracy
           + 0.20 × PenalizedCaseRecall
           + 0.10 × LawF1_micro
```

- `OutcomeAccuracy`: tỷ lệ chọn đúng tuyệt đối một trong bốn nhãn.
- `PenalizedCaseRecall`: tỷ lệ tìm lại đúng chứng cứ vụ án, sau khi bị trừ vì gọi API quá nhiều.
- `LawF1_micro`: điểm cân bằng giữa tìm đủ và tìm đúng điều luật, gộp trên toàn bộ tập test.

Hệ số hiệu quả API cho vụ `i`:

```text
E_i = max(0, 1 - max(0, c_i - 2n_i) / (3n_i))
```

Trong đó `n_i` là số đoạn của vụ và `c_i` là tổng lượt gọi API mà server ghi nhận. Không bị phạt đến `2n_i`; điểm hiệu quả giảm dần và về 0 tại `5n_i`.

### Cảnh báo vận hành

- `c_i` được cộng dồn qua mọi thí nghiệm và mọi lần nộp của đội; log không được reset.
- Lượt gọi ở Public Test cũng có thể được tính khi đánh giá Private Test.
- Không đặt `c_i` trong file nộp; server tự lấy từ log.
- Bắt buộc cache kết quả truy hồi theo `case_id + query`.

## Định dạng nộp bài

Nộp một file `submission.json`, là một mảng JSON. Mỗi vụ test có đúng một object:

```json
[
  {
    "case_id": "case_4101",
    "prediction": "A_WIN",
    "case_evidence": ["case_4101_seg_<hash>"],
    "law_evidence": [
      {"law_id": "47/2010/QH12", "aid": 270}
    ]
  }
]
```

Quy tắc đã xác minh:

- Không lặp `case_id`; `case_id` phải thuộc tập test.
- `case_evidence` bắt buộc nhưng có thể là `[]`.
- `law_evidence` hiện là danh sách object `{law_id, aid}`, không còn là chuỗi tự do.
- `aid` là ID điều trong corpus luật, không phải số thứ tự tự suy đoán hay nội dung văn bản.
- ID đoạn chứng cứ hiện là ID hash/ẩn và chỉ lấy được qua Case Content API; không thể đoán dạng `_chunk_0`.
- ID đoạn ổn định qua các lần chạy.
- Public leaderboard giữ lần chạy tốt nhất của mỗi đội.
- Giới hạn công khai hiện thấy: 20 lần nộp/đội/24 giờ.

## Retrieval API

- Base URL: `https://alqac-api.ngrok.pro`
- Endpoint: `POST /retrieve`
- Header: `X-API-Key: TEAM_TOKEN`
- Rate limit: 1 request mỗi 5 giây cho một đội.

Ví dụ body:

```json
{"query": "từ khóa tiếng Việt", "case_id": "case_4101"}
```

Mỗi lượt gọi trả về đúng top-1 đoạn, gồm điểm BM25, nội dung và ID đoạn. Điểm BM25 cao hơn thường nghĩa là phù hợp hơn về từ khóa.

Mã phản hồi chính: `200` thành công; `403` token thiếu/sai; `422` body không hợp lệ; `429` gọi quá nhanh; `503` cơ sở dữ liệu đội tạm lỗi.

## Thông báo cập nhật quan trọng

Website đang yêu cầu các đội nộp lại Public Test do hai thay đổi:

1. `law_evidence` đổi sang danh sách object `{law_id, aid}`.
2. ID chứng cứ vụ án đổi sang ID hash/ẩn, lấy qua API.

## Snapshot leaderboard

Thời điểm kiểm tra: **2026-07-15, múi giờ Việt Nam**. Đây là dữ liệu động.

- 32 đội được xếp hạng.
- Hạng 1: `6 Con Sâu`, Final Score khoảng `0.9918`.
- Hạng 2: `HCMUS-Speed`, khoảng `0.9912`.
- Hạng 3: `Agenticlabs`, khoảng `0.8527`.

Không dùng snapshot này làm dữ liệu cố định; xem leaderboard trực tiếp để cập nhật.

## Thông tin chưa xác minh

Website công khai chưa cho thấy rõ:

- deadline đăng ký;
- lịch kết thúc Public Test và mở Private Test;
- deadline nộp cuối;
- ngày đóng/mở chính xác của từng phase;
- yêu cầu paper/report;
- giải thưởng và điều kiện tham dự.

Các mục này nhiều khả năng nằm trong chuỗi email ban tổ chức và cần đọc đầy đủ trước khi lập kế hoạch.

## Khuyến nghị bước tiếp theo

1. Theo dõi email mới để lấy timeline chính thức khi Ban tổ chức công bố.
2. Dữ liệu đã tải; tiếp tục giữ ngoài Git và theo dõi checksum trong `docs/data-manifest.md`.
3. Làm bộ kiểm tra schema `submission.json` trước khi huấn luyện.
4. Xây baseline chỉ cho `prediction` bằng dữ liệu local.
5. Thiết kế truy vấn, ngân sách lượt gọi và cache trước khi dùng Retrieval API.
6. Đánh giá riêng ba thành phần: dự đoán kết quả, chứng cứ vụ án, điều luật.

## Nguồn

- Leaderboard: <https://alqac2026-leaderboard.ngrok.app/>
- Rules: <https://alqac2026-leaderboard.ngrok.app/about>
- API guide: <https://alqac2026-leaderboard.ngrok.app/api-docs>
- Submit: <https://alqac2026-leaderboard.ngrok.app/submit>
- OpenAPI: <https://alqac-api.ngrok.pro/docs>
- Metadata: <https://alqac2026-leaderboard.ngrok.app/api/task-info>

Ngày truy cập: 2026-07-15.
