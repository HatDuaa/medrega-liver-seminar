# PLAN — Notebook EVAL/VISUALIZE (`eval_visualize.ipynb`)

> Mục tiêu: notebook trực quan hoá kết quả + phân tích. **Chạy LOCAL, KHÔNG cần GPU/model**
> (chỉ cần: ảnh `data_liver_multi_v3/images/` + file `eval_pred_*.json`).
> Theo yêu cầu: (1) ảnh gốc + box GT theo 3 cỡ u; (2) model predict vs gốc theo 3 cỡ; (3) các phân tích.

## Cơ sở kỹ thuật (đã verify)
- JSON không lưu `image_path` → **link bằng cách replicate split** (SEED=0, default_rng) → `test[i] ↔ JSON.test[i]`.
  Đã verify **255/255 khớp** (pid+gt_boxes theo thứ tự). → mỗi prediction ghép được `image_path` + `gt_boxes`.
- Cỡ u = **diện tích GT box** (proxy). Chia 3 nhóm theo **tertile** (33/67 percentile) của TẤT CẢ ổ u test.

## Cấu trúc notebook

### Cell 0 — Setup & link data
- Import: json, numpy, PIL, matplotlib, scipy.optimize.
- Config path: `DATA_DIR=data_liver_multi_v3`, `JSON_PATH=eval/eval_pred_*.json`.
- Đọc data.jsonl → replicate split (SEED=0) → `test` rows (có image_path + gt_boxes).
- Đọc JSON → `preds`. **Zip theo thứ tự** + assert gt_boxes khớp → `records` = list:
  `{image_path, gt_boxes, pred_boxes, pid, is_pos, logprob, spatial, selfconf}`.
- Hàm: `iou`, `match_boxes` (Hungarian), `load_img(path)`.
- Tính **cỡ mỗi ổ** + ngưỡng tertile (q1,q2) → hàm `size_cat(area) -> 'nhỏ'/'vừa'/'lớn'`.

### Cell 1 — GT box theo 3 CỠ (ảnh gốc + box xanh)
- Lọc lát DƯƠNG **1-ổ** (cho ảnh sạch), nhóm theo cỡ ổ.
- Lưới **3 hàng (nhỏ/vừa/lớn) × 4 ảnh**: ảnh gốc CT + box GT (xanh) + tiêu đề "cỡ X% ảnh".
- Mục đích: cho thấy u nhỏ ~10px (gần vô hình) vs u lớn rõ ràng.

### Cell 2 — PREDICT vs GỐC theo 3 CỠ
- Cũng 3 hàng (nhỏ/vừa/lớn), mỗi hàng vài ví dụ ĐẠI DIỆN (mix: có ca trúng + ca sót).
- Mỗi ảnh: GT (xanh) + pred (đỏ) + tiêu đề `IoU=.. | cỡ ..%` hoặc `SÓT (không box)`.
- Mục đích: thấy rõ **u lớn → box đỏ bám sát; u nhỏ → thường không có đỏ (sót)**.

### Cell 3 — PHÂN TÍCH (inline, tự chứa)
- **3a Metrics:** recall/precision@IoU + mean-IoU + per-patient + CI + FP ca âm.
- **3b Recall theo cỡ u:** bảng nhỏ/vừa/lớn (số đã có: 35%/54%/74%).
- **3c Hướng-1:** bảng 3 tín hiệu (cal chọn) + chart risk-coverage (logprob 0.32→0.57).
- (Tái dùng logic từ `scripts/analyze_eval.py`, copy inline cho notebook tự chứa.)

## === CHỐT SAU REVIEW NHÓM (R1 kỹ thuật + R2 trình bày) ===

### Sửa kỹ thuật (R1 — bắt buộc, kẻo chạy sai/hình xấu):
1. **Replicate split CHÍNH XÁC**: copy y nguyên code cell `split` (đọc data.jsonl theo THỨ TỰ DÒNG; `sorted(set(pid))` rồi `np.random.default_rng(SEED).shuffle(pids)` — CẤM legacy `np.random.seed`; `int(n*0.6)` truncation; test = filter giữ thứ tự dòng). **Assert per-row cả 255 (pid+gt_boxes) + `len==255`**.
2. **Cỡ u = theo Ổ, không theo lát**: tertile (q1,q2 = 33/67 percentile) tính trên **TẤT CẢ ổ test dương** (giống `analyze_eval.by_size`), dùng CHUNG cho mọi cell. Cell GT lọc 1-ổ chỉ để ảnh sạch; Cell predict KHÔNG lọc 1-ổ (mỗi ổ best-IoU riêng).
3. **Hàm vẽ chuẩn**: `imshow(img, cmap='gray')` (mode L), `Rectangle((x1,y1), x2-x1, y2-y1)` với `W,H=img.size` (không hardcode 512), `origin='upper'`. 1 helper `draw_box` dùng chung.
4. **U nhỏ ~10px → ZOOM**: crop bằng `set_xlim/set_ylim` quanh tâm box (ylim đảo vì origin upper), 2 panel (full + zoom) cho hàng nhỏ.
5. **Path đúng**: `DATA_DIR = code/data/data_liver_multi_v3/`; lọc ca âm trước khi tính area; cal đọc thẳng `JSON.cal` (không replicate); FP chỉ 2/135 → ghi số, đừng vẽ lưới.
6. **Chọn ảnh xác định**: `rng_viz = default_rng(42)` riêng; sort theo IoU lấy percentile cố định + ca sót → tái lập, ghi seed.

### Sửa trình bày (R2 — story + trung thực):
- **Story arc**: Bài toán/Data → GT theo cỡ → Predict theo cỡ (KÈM sót) → Failure cases → Selective prediction → Limitations. Mỗi cell mở bằng **1 câu thông điệp bold**.
- **Cell mở đầu** + **histogram cỡ u** (median 0.14%, vạch tertile) → đặt vấn đề "data ngập u nhỏ".
- **Cell 2 ghi tỉ lệ sót thật mỗi hàng** (nhỏ recall 35% → nhiều ô SÓT hơn lớn 74%). Không được toàn ca đẹp.
- **Cell Failure cases**: tìm ca sót thật từ JSON v3 (pred rỗng / IoU thấp, ưu tiên vị trí lạ) — thẳng thắn.
- **Selective prediction**: chart + ví dụ "trả lời (logprob cao, đúng)" vs "im (logprob thấp, đáng ra sai)".
- **Caveat TẠI HÌNH**: n=25 + CI [0.235,0.415] + "AUROC=1.0 cal là artifact n nhỏ" + "cỡ=box 2D proxy" + "abstain ca âm = intra-patient discrimination, KHÔNG phải specificity".
- **Cell Limitations + Đóng góp** (kết): gom mọi caveat + nhấn đóng góp (selective prediction paper gốc không có).
- **before/after (zero-shot vs fine-tune)**: R2 đề xuất nhưng **CHƯA có data zero-shot** → để **placeholder markdown** "Phase 4 — cần chạy baseline", không bịa.
- **n nhất quán = 25 bệnh nhân dương** (số "~13" cũ là ước lượng sai, bỏ).

### Cân đối: ~70% chứng minh đóng góp / ~30% giới hạn (dồn vào caption + failure + limitations).
