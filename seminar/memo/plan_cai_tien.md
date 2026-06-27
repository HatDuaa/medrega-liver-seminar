# PLAN cải tiến vòng 2 — MedRegA / Gemma 4 (2026-06-27)

## Mục tiêu
Sửa **prior vị trí** (model học "u luôn ở trên-trái" → sót u chỗ khác) + **box lệch** (token-loss ≠ IoU) + **lười nói no-tumor** (recall thấp). Giữ ưu điểm 0% bịa u.

## 5 phần (P1-P5)

### P1. DATA — cắt lát u NGẪU NHIÊN + LỚN NHẤT
- **File:** `code/prep_data_multi_local.py` (chạy local → tạo data mới).
- **Đổi:** thay "top-N lát u lớn nhất" → **1-2 lát u LỚN NHẤT + (N-2) lát u NGẪU NHIÊN** (trong các lát có u). → đa dạng vị trí u theo trục z (u to/nhỏ, vị trí khác).
- **Giữ:** windowing, box từ mask, split theo bệnh nhân, ca âm.
- **Output:** folder mới `data_liver_multi_v2/` (KHÔNG đè bản cũ).
- **Verify:** in phân bố vị trí tâm box (x,y) — phải rải hơn bản cũ.

### P2. AUGMENTATION — on-the-fly, CHỈ train, biến đổi cả box
- **File:** thêm hàm `augment(img, box)` + tích hợp vào `build_train_example` (notebook).
- **Phép (an toàn cho CT gan, giữ 512×512):**
  - Dịch (translation) ±12%, xoay nhẹ ±12°, scale ±10%, sáng/tương phản nhẹ.
  - **KHÔNG flip ngang** (gan→situs inversus), **KHÔNG xoay 90°** (CT hướng chuẩn).
- **Box biến đổi theo** ảnh (dịch/xoay/scale 4 góc → hộp bao → clip biên [0,1000)).
- **Chỉ train** (cờ `augment=True`); val/test `augment=False` (giữ gốc).
- **Vùng trống** điền đen (nền CT vốn đen). u ra ngoài khung nhiều → bỏ augment đó.
- **Verify:** vẽ vài ảnh augment + box → box vẫn ôm u.

### P3. LOSS — soft-coordinate GIoU + cân bằng w_pos (KHÓ NHẤT, làm cẩn thận)
- **File:** custom `Trainer.compute_loss` (notebook).
- **Soft-coordinate:** tại token toạ độ trong target, tính **kỳ vọng giá trị** từ logits. ⚠️ **PHỤ THUỘC tokenizer:** phải kiểm Gemma token số theo từng chữ số hay không. Nếu per-digit → E[coord]=Σ digit×P. Nếu KHÔNG → khó, fallback chỉ dùng CE + w_pos.
- **GIoU (KHÔNG raw IoU):** vì box hay không overlap → raw IoU grad=0. `loss_box = 1 − GIoU`.
- **Cân bằng:** `loss = w_pos·(CE + λ·loss_box)` [ca dương] hoặc `w_neg·CE` [ca âm], với `w_pos>w_neg` (vd 2:1) → chống lười no-tumor.
- **Verify:** loss giảm mượt; box test khít hơn (IoU lên) so với CE thuần.
- **Rủi ro cao** → nếu soft-coordinate không khả thi với tokenizer Gemma, **CHỈ làm w_pos weighting** (vẫn chống lười), bỏ GIoU.

### P4. METRIC — điểm công bằng (chống gaming bằng no-tumor)
- **File:** thêm vào cell EVAL (notebook).
- **Công thức:**
  - Ca dương: nói no-tumor (sót)=0; nói có u box sai=0.5; có u box khít=0.5+0.5×GIoU (tới 1.0).
  - Ca âm: im đúng=0.6 (cap 0.5-0.75); bịa u=0.
- Báo cáo **điểm trung bình** + recall/precision riêng.
- **Verify:** điểm phản ánh đúng (model toàn no-tumor → điểm thấp).

### P5. TRAIN config (vặt)
- `eval_strategy="steps", eval_steps≈steps/epoch` (hiện loss từng step).
- `EPOCHS=5` (data mới khó hơn → overfit muộn; best-by-val tự lưu epoch tốt).
- Giữ best-by-val callback + 2 nhóm LR + full vision + LoRA LLM r=32.

## Thứ tự implement
1. P1 data (script local) → chạy tạo data v2.
2. P2 augment (notebook) → verify hình.
3. P5 config (notebook).
4. P4 metric (notebook).
5. P3 loss (notebook, cẩn thận) — kiểm tokenizer trước; fallback w_pos nếu cần.
6. Subagent review toàn bộ → sửa → lặp.

## Nguyên tắc
- Augment/loss CHỈ train; val/test sạch.
- Không đè data/model cũ (đặt tên mới: data v2, ckpt mới).
- Mỗi phần verify riêng trước khi gộp.
