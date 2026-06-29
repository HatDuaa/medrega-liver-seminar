# TỔNG HỢP — Vì sao v4 (BCE-head) sập, và cách cứu

**Ngày:** 2026-06-29 · **Người soi:** 3 subagent độc lập (xem 3 file review cùng thư mục)

## Hiện tượng
v4 eval (model khôi phục từ `best_trainable.pt`) so với v3:

| Chỉ số | v3 | v4 | |
|---|---|---|---|
| per-patient mean-IoU | 0.32 | **0.071** | ↓ |
| recall@0.25 | 54% | **10%** | ↓ |
| recall@0.5 | ~38% | **1%** | ↓ |
| FP per-patient | ~1% | **26%** | ↑ |

Model vẫn xuất đúng format, vẽ box đại khái đúng vùng nhưng lệch → **hành vi ≈ base/zero-shot**.

## Kết luận đồng thuận 3/3 reviewer
**Model train KHÔNG hỏng. Bị NẠP SAI lúc khôi phục.**

1. **[recovery]** Cell khôi phục dựng lại model bằng `get_peft_model` + `load_state_dict(strict=False)` rồi `assert unexpected_keys == 0`. Nhưng assert đó **bỏ qua `missing_keys`**. Runtime mới cài `peft/transformers` version khác (cell `pip` dùng `-U`, không ghim) → tên key LoRA lệch ở infix `.default` → trọng số đã-train rơi vào `missing_keys` **im lặng** → adapter giữ giá trị khởi tạo (`lora_B = 0` = vô hiệu) → `merge_and_unload` gộp adapter rỗng vào base → **model = base**.
2. **[training-loss]** `eval_loss ≈ 0.33` (CE thuần trên cả token toạ độ) **không thể** cùng tồn tại với IoU 0.071 nếu cùng 1 bộ trọng số → loại trừ "train hỏng". Code loss đúng (off-by-one, dấu BCE, assert token). λ=2 hơi mạnh (rủi ro FP, không phải nguyên nhân sập IoU).
3. **[eval-pipeline]** Tự tính lại từ JSON v3 → **tái lập chính xác** số v3 (IoU 0.324). Cùng code chạy v4 → v4 sập là do model, không phải metric. Không có lỗi scale/parse/linkage/aggregation.

## Bằng chứng quyết định
- `neg detect-rate` lúc train = 0–2/10, nhưng FP lúc eval = 26% → trọng số eval ≠ trọng số train.
- Toạ độ hỏng (IoU 0.07) mà BCE **chỉ** đụng token detect, không đụng toạ độ → hỏng toạ độ không thể do BCE → do nạp-sai.

## Cách cứu (KHÔNG train lại)
Nạp lại `best_trainable.pt` cho ĐÚNG:
1. **Remap key**: bỏ infix `.default` để khớp tên giữa version peft.
2. **Hard-fail**: bắt buộc mọi key đã-train được nạp + `tổng |lora_B| > 0` mới cho merge (chống lại merge ra base).
3. Merge + lưu model hoàn chỉnh → lần sau load thẳng.

## Phòng ngừa
- Ghim version trong cell `pip` (`peft==`, `transformers==`) để không drift.
- Lần train tới: chờ `mergesave` lưu xong + Drive đẩy file (thấy `config.json` + `*.safetensors`) **rồi mới** tắt runtime — đừng để `unassign` tự chạy.
