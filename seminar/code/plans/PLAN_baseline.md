# PLAN — Baseline Gemma 4 ZERO-SHOT (trước fine-tune)

> Mục tiêu: chạy Gemma 4 **gốc (CHƯA train)** trên ĐÚNG test set → lưu JSON cùng format
> → có **before/after** so với gemma4_v3. Đây là thứ audit đánh giá "bắt buộc" để chứng minh fine-tune giúp gì.

## Nguyên tắc CỐT LÕI: phải SO ĐƯỢC (apples-to-apples)
Baseline PHẢI dùng **y hệt** với lần fine-tune, chỉ khác MODEL:
- **Cùng split** (SEED=0, replicate y nguyên) → cùng 255 lát test.
- **Cùng `predict_boxes` / `parse_boxes` / prompt** (INSTRUCT_PROMPT_TRAIN) / MAX_NEW_TOKENS=192.
- **Cùng định dạng JSON** (pid, is_pos, pred_boxes, gt_boxes, signals) → `analyze_eval.py` chạy được luôn.
- Khác DUY NHẤT: `model` = Gemma 4 **gốc** (không LoRA, không train, không load checkpoint).

## Thiết kế: notebook RIÊNG `baseline_zeroshot.ipynb`
Tự chứa, **trích Y NGUYÊN** các cell từ `medrega_finetune.ipynb` để đảm bảo logic giống hệt:
- `pip` (cài thư viện) → `imp` → `cfg` (**đặt `RUN_NAME="gemma4_zeroshot"`**) → `mount` → `getdata` → `split`
  → `load` (model GỐC) → `fmt` → `util` → `sec8` (hàm predict) → **PREDICT** (lưu JSON).
- **BỎ:** train, load-checkpoint, các cell analyze. → user Run-All là ra, không lỡ train.

## Quyết định cần REVIEW: predict NHẸ hay ĐẦY ĐỦ?
| | NHẸ (box + logprob) | ĐẦY ĐỦ (như fine-tune) |
|---|---|---|
| Tín hiệu | logprob; spatial/selfconf = 0 (dummy) | đủ 3 (spatial 5 lần đoán) |
| Thời gian | **~15-20 phút** | ~1.5 giờ |
| Đủ cho before/after? | ✅ (so localization: IoU/recall/precision chỉ cần pred_boxes) | ✅ nhưng dư |
| Hướng-1 trên zero-shot | bỏ (model chưa biết task → tín hiệu vô nghĩa) | có nhưng vô nghĩa |

→ **Đề xuất: NHẸ** (zero-shot signals vô nghĩa; before/after là về ĐỊNH VỊ). Cần PREDICT cell rút gọn:
chỉ `predict_boxes` (box + logprob), set `spatial=selfconf=0.0`, vẫn lưu đủ field cho format khớp.

## Sau khi có JSON baseline
1. Chạy `scripts/analyze_eval.py eval_pred_gemma4_zeroshot_*.json` → số zero-shot.
2. Thêm **bảng/hình before-after** vào `eval_visualize.ipynb` (placeholder Phase 4 đang chờ): nạp 2 JSON,
   so IoU/recall/precision + vài cặp ảnh "zero-shot (box loạn) vs fine-tune (box sát)".

## Rủi ro (cho review soi):
- Model gốc **có thể không xuất đúng format `<box>[[...]]`** zero-shot → `parse_boxes` rỗng → IoU≈0.
  Đây là **baseline HỢP LỆ** (cho thấy fine-tune dạy task), nhưng cần xác nhận prompt vẫn ép thử format.
- Model gốc dễ **lảm nhảm dài** → MAX_NEW_TOKENS=192 có đủ/không cắt giữa box? (box đầu vẫn parse được).
- Phải chắc split + predict giống HỆT bản fine-tune (trích cell, không viết lại tay).
- cal: có cần không cho baseline? (chỉ cần test cho before/after; cal để format khớp — predict cal nhẹ luôn).

## Câu hỏi mở:
- Nhẹ hay đầy đủ? (đề xuất nhẹ)
- Có cần predict cal cho baseline, hay chỉ test?
- before/after để trong eval_visualize hay notebook riêng?

## === CHỐT SAU REVIEW ===
- **NHẸ** (box + logprob; spatial=selfconf=**0.0 float**, KHÔNG để thiếu key → analyze KeyError).
- **VẪN predict cal** (cal dương, dùng CAL_LIMIT) — bỏ cal → `huong1` crash `np.quantile([])`. Chỉ tắt spatial/selfconf.
- **CẤM trích cell `train`** (nó get_peft_model ghi đè model → hết zero-shot). Bỏ luôn diag/viz/load_ckpt/analyze.
- **RUN_NAME="gemma4_zeroshot"** (khỏi trộn JSON gemma4_v3). Giữ BF16 (không 4-bit), prompt + MAX_NEW_TOKENS=192 Y NGUYÊN.
- Khi phân tích: truyền path JSON tường minh (đừng auto-glob).
- logprob zero-shot hay = -10 (model không ra số) → bỏ qua, không diễn giải Hướng-1 cho baseline.
