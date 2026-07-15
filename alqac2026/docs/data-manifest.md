# ALQAC 2026 Data Manifest

## Trạng thái tải dữ liệu

Ngày tải: 2026-07-15.

Nguồn: thư mục Google Drive **ALQAC 2026 Public Test** được Ban tổ chức gửi trong email.

| File cục bộ | Kích thước | Số phần tử | SHA-256 |
|---|---:|---:|---|
| `data/public/ALQAC2026_public_test.json` | 3,573,025 byte | 50 vụ | `ce0e85ff32c7b3157288b4b778640c8ff30045512528e87bb3dda68845cdfeea` |
| `data/public/corpus_law_pub.json` | 4,192,527 byte | 18 luật, 3.352 điều | `7e6c7c63dbdce53f96311a5e35fd0801715e6037f78a5118eaba5a70a2d550de` |

Hai file đọc được bằng JSON parser. Public Test có 50 `case_id` duy nhất.

Tài liệu công khai bổ sung đã lưu:

| File | Nội dung |
|---|---|
| `docs/reference/alqac-api-openapi.json` | OpenAPI 3.1.0 của Case Evidence Retrieval API; có `GET /` và `POST /retrieve` |
| `docs/reference/task-info.json` | Tên task, 4 nhãn, trọng số chấm điểm và 50 gold cases |

## Schema Public Test

Mỗi vụ hiện có các trường:

```text
court, A_role, B_role, case_id, case_fact, case_type, case_query,
raw_sha256, court_level, A_description, B_description, annotation_id,
court_verdict, judgment_date, judgment_text, verdict_label,
court_reasoning, judgment_number, source_filename,
related_law_provisions
```

Phân bố nhãn:

| Nhãn | Số vụ |
|---|---:|
| `PARTIAL_A_WIN` | 19 |
| `A_WIN` | 16 |
| `B_WIN` | 10 |
| `PARTIAL_B_WIN` | 5 |

## Schema corpus luật

```json
{
  "id": 9,
  "law_id": "47/2010/QH12",
  "content": [
    {
      "aid": 270,
      "content_Article": "Nội dung điều luật..."
    }
  ]
}
```

Corpus có 18 `law_id`, tổng cộng 3.352 `aid` duy nhất.

## Cảnh báo Public–Private

Public Test chứa thông tin đầy đủ, bao gồm nội dung bản án và `verdict_label`, nhằm giúp đội thử framework. Theo email Ban tổ chức, Private Test chỉ cung cấp dạng tối giản:

```json
{
  "case_id": "0001",
  "case_query": "Mô tả ngắn và câu hỏi cần dự đoán..."
}
```

Không xây hệ thống phụ thuộc vào `judgment_text`, `court_reasoning`, `court_verdict`, `verdict_label` hoặc `related_law_provisions` ở đầu vào. Các trường đó không tồn tại trong Private Test và chỉ được dùng để phát triển/đánh giá offline trên Public Test.

## Bảo mật

- Token đội nằm trong `alqac2026/.env`, không nằm trong manifest.
- `.env` và toàn bộ dữ liệu dưới `data/` được Git bỏ qua.
- Không gọi Retrieval API chỉ để kiểm tra token vì mỗi request có thể được tính vào ngân sách chấm điểm.
