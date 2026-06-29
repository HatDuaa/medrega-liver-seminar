# PLAN — Sửa RECALL (model lười detect) qua loss + chọn checkpoint

> Gốc (đã review): model lười detect vì (1) token quyết định `<ref>` vs `No` bị **pha loãng** trong CE-trung-bình,
> (2) **exposure bias**, (3) **best-checkpoint theo eval_loss = chọn model nhát nhất**.
> Triệu chứng: recall 54%, nhưng khi vẽ box thì IoU 0.62 + FP 1% (định vị tốt, chỉ nhát).
> Mục tiêu: kéo recall lên mà KHÔNG bùng FP. **1 lần train.**

## Làm CẢ 2 trong 1 lần train (tiết kiệm GPU):

### A. W_POS 3 → 4 (rẻ, 1 số)
- Nhích trọng số ca dương 1 nấc. (Review: W_POS đã 2.5:1 nghiêng dương → chỉ nhích nhẹ, đừng kỳ vọng nhiều.)

### B. BCE head — phạt THẲNG quyết định detect (độc lập số box)
- Thêm số hạng: `loss = CE_đáp_án (như cũ) + λ × BCE(detect_decision)`.
- **detect_decision** lấy ở token ĐẦU của đáp án (label != -100 đầu tiên):
  - `p_detect = sigmoid(logit[detect_token] − logit[no_token])` tại vị trí đó.
  - `y = 1` (ca dương) / `0` (ca âm). `BCE = −[w₊·y·log p + (1−y)·log(1−p)]`.
- **Xác định token ĐÚNG (bẫy lớn — review cảnh báo):**
  - `<ref>` có thể bị tách (`<`,`ref`,`>`). Phải lấy **token id đầu tiên của đáp án dương** (tokenize 1 đáp án dương) làm `detect_token`, và token đầu của `"No liver tumor is found."` làm `no_token`.
  - **IN RA kiểm bằng mắt** 20 mẫu +/−: token đầu phần đáp án phải là detect_token / no_token. Nếu sai → fix trước khi train.
- **Hệ số khởi đầu (review):** `λ` NHỎ = **2–3** (KHÔNG 8); `w₊` (pos_weight) ≈ **3**. Bắt đầu nhẹ, tăng nếu recall còn thấp.
- **Weight cả 2 chiều** (dương→detect, âm→no) — thực ra an toàn FP hơn 1 chiều (BCE âm kéo model nói No đúng trên ca âm).

### C. Lưu MỌI epoch + giữ best-by-loss (mặc định)
- `save_strategy="epoch"`, `save_total_limit=5` (hoặc callback lưu trainable-state mỗi epoch).
- GIỮ best-by-eval_loss làm **mặc định** (skip cell lọc vẫn có model dùng).
- In loss mỗi epoch để tham khảo (KHÔNG dùng để chọn cuối).

## Cell CHỌN checkpoint (offline, sau train — TÙY CHỌN, skip được)
- Tập val = **bốc NGẪU NHIÊN theo BỆNH NHÂN** từ cal (seeded, vd 15-18 bệnh nhân) → lấy lát của họ. KHÔNG bốc lát lẻ.
- Load TỪNG checkpoint đã lưu → infer NHẸ (box only) trên val đó → in bảng:
  **detection-recall | recall@IoU0.25/0.5 | precision | FP | mean-IoU**.
- **Chọn best theo F1@IoU + guardrail FP ≤ 3-4%** (KHÔNG recall trần → kẻo lấy model "luôn detect").
- Skip cell này → dùng best-by-loss mặc định.

## Eval cuối
- Checkpoint đã chọn → PREDICT full test (pipeline có sẵn) → JSON `gemma4_v4` (RUN_NAME mới).

## GUARDRAIL / GIÁM SÁT (review nhấn):
- **FP rate** = guardrail cứng (đang 1%, đừng để vượt 3-4%).
- Log riêng 2 thành phần loss (CE box vs BCE detect) — đảm bảo box không xấu đi (mean IoU trên TP không tụt).
- Theo dõi **precision + F1**, KHÔNG chỉ recall (chống recall giả "luôn detect").
- Validate bằng **detection-recall trên val** (model bớt lười chưa), độc lập train loss.

## Câu hỏi mở (cho review):
- BCE head: tính `p_detect` từ 2 token (detect vs no) đủ chưa, hay cần softmax nhiều token?
- λ=2-3 + w₊=3 + W_POS=4 có chồng chéo (cùng đẩy dương) gây over-correct FP không? Bỏ bớt cái nào?
- Lưu mọi epoch (full trainable ~1GB × 5) — Drive chịu nổi? load lại để infer có rườm rà?
- F1 hay Fβ (β>1 nghiêng recall) cho chọn checkpoint y tế?

## === CHỐT SAU REVIEW NHÓM (kỹ thuật + over-correction) ===

### 🔧 2 BUG CHẶN phải sửa:
1. **Off-by-one logits:** logit quyết định ở `logits[0, pos-1, :]` (logit vị trí t đoán token t+1), KHÔNG phải `pos`. + compute_loss chưa biết vị trí → thêm `out["_detect_pos"] = first index label != -100` trong build_train_example, **pop** trong compute_loss.
2. **Thứ tự merge:** lưu trainable-state PEFT rồi load SAU `merge_and_unload` → key lệch → mọi checkpoint thành model cuối (bảng chọn vô nghĩa). → **Cell chọn checkpoint chạy TRƯỚC merge, trên PeftModel.** Chọn xong mới merge cái thắng.

### 🎛️ ĐỔI THIẾT KẾ: chỉ 1 NÚM điều khiển (chống over-correction)
Review: W_POS=4 + w₊=3 + λ = **3 lực chồng cùng đẩy dương → FP bùng + không biết thủ phạm.** Rút còn 1 núm:
| Thành phần | Plan cũ | CHỐT |
|-----------|---------|------|
| **W_POS** | 3→4 | **1.5** (gần trung tính, đừng về 1.0 kẻo lệch batch) |
| **BCE head** | giữ | **GIỮ — cơ chế CHÍNH** |
| **λ (BCE)** | 2-3 | **2** ← núm điều khiển DUY NHẤT (FP bùng thì hạ λ) |
| **w₊ (trong BCE)** | 3 | **1.5** (FP đã 1%, không cần ép nói No) |
| **Vế âm BCE** | — | **GIỮ — van an toàn FP** (phạt bịa u trên ca âm) |

### 🛠️ Chi tiết implement (review):
- detect_token_id/no_token_id: lấy từ **token đầu đáp án TRONG batch đã qua chat template** (không tokenize chuỗi trần). **IN 20 mẫu +/− kiểm bằng mắt — BẮT BUỘC** (token sai → BCE học nhiễu, tưởng over-correct mà thực ra bug).
- Dùng `F.binary_cross_entropy_with_logits(diff, y)` (ổn định) × hệ số thủ công (không pos_weight vì batch=1).
- **Guard `if model.training`** cho BCE (giữ eval_loss sạch cho SaveBestFull).
- BCE 2-token CHỈ đúng với prompt **2-opt** (3-opt "Uncertain" thì lệch).
- Gỡ mâu thuẫn `save_total_limit` vs `save_strategy="no"`.

### 🎯 Mục tiêu + guardrail:
- Recall **68%±** (đừng tham 85%+; quan hệ recall-FP có "đầu gối" ~70-75%). FP ≤ **4% cứng**. mean-IoU/TP ≥ **0.58**.
- Chọn checkpoint: **Fβ (β≈1.5, nghiêng recall) + guardrail cứng FP≤4% + IoU≥0.58**.
- **Cảnh báo SỚM (log mỗi epoch):** detect-rate trên ca ÂM + #box/ảnh trên ca âm → bật lên TRƯỚC khi FP kịp phản ánh.
