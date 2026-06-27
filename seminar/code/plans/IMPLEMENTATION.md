# PLAN TRIỂN KHAI — multi-box + eval restructure + W_POS (2026-06-28)

> Nguồn: `TODO.md` + `methodology_todo.md` + `results_audit.md`. Notebook: `medrega_finetune.ipynb`.
> Luồng: **Phase 1 (data+prompt) → Phase 2 (train lại) → Phase 3 (eval) → Phase 4 (so sánh)**.
> Mục tiêu: data nhãn đúng (multi-box), model bớt sót (W_POS=3), eval đáng tin (Hungarian + CI + sửa bug + cal/test tách).

## Phases
| # | Tên | Nhóm TODO | Cần train? | Trạng thái |
|---|-----|-----------|-----------|-----------|
| 1 | Data + multi-box + prompt | Nhóm 2 | không | ⬜ pending |
| 2 | W_POS=3 + train lại | Nhóm 3 | **CÓ (1 lần)** | ⬜ pending |
| 3 | Eval restructure (PREDICT/ANALYZE) | Nhóm 1 | không | ⬜ pending |
| 4 | Baseline + so sánh | Nhóm 4 | không | ⬜ pending |

---

## PHASE 1 — Data multi-box + prompt
**Deliver:** data v3 với GT = nhiều box/lát (1 box/ổ u), prompt + format đáp án multi-box.

### File
- Tạo: `code/prep_data_multi_v3.py` (copy v2, sửa phần chọn box).
- Sửa: notebook cell `fmt` (`INSTRUCT_PROMPT_*`, `_answer_from_box`→`_answer_from_boxes`, `augment` map nhiều box, `build_train_example`).
- Sửa: cell `getdata` (trỏ `data_liver_multi_v3`).

### Bước
1. **prep v3 — tách ổ thành nhiều box:**
   ```python
   from scipy import ndimage
   MIN_LESION_PX = 30   # bỏ ổ nhiễu < 30px
   def slice_to_boxes(mask, W, H):           # mask = seg[:,:,z]==2
       lbl, n = ndimage.label(mask)
       boxes = []
       for k in range(1, n+1):
           ys, xs = np.where(lbl == k)
           if len(xs) < MIN_LESION_PX: continue
           boxes.append([int(xs.min()/W*1000), int(ys.min()/H*1000),
                         int(xs.max()/W*1000), int(ys.max()/H*1000)])
       boxes.sort(key=lambda b: (b[1], b[0]))   # sort y rồi x (thứ tự ổn định để train)
       return boxes                              # list (có thể rỗng nếu toàn ổ < MIN)
   ```
   - `make_record`: `gt_box`(đơn) → `gt_boxes`(list). Nếu list rỗng (u quá nhỏ) → coi như **bỏ lát** (không thành mẫu dương rác).
   - Đáp án: `<ref>liver tumor</ref><box>[[x1,y1,x2,y2], [x1,y1,x2,y2], ...]</box>`.
   - In thống kê: phân bố số ổ/lát (xác nhận khớp ~35% đa ổ).
2. **Prompt** (`INSTRUCT_PROMPT_TRAIN`): đổi "If a tumor is present: ...1 box..." → "If one or more tumors are present, output **ALL** their boxes: `<ref>liver tumor</ref><box>[[x1,y1,x2,y2], ...]</box>`". Giữ lựa chọn no-tumor.
3. **fmt cell:**
   - `_answer_from_boxes(boxes)`: rỗng→"No liver tumor is found."; ngược lại join nhiều box.
   - `augment(img, boxes)`: map phép affine lên **từng box**, lọc box ra ngoài khung; nếu hết box → giữ ảnh gốc + boxes gốc (không đổi nhãn).
   - `build_train_example`: dùng `gt_boxes`, lưu `_gt_boxes` (list) thay `_gt_box`.
4. **Chạy v3 local + verify** (vẽ 3-4 lát đa ổ + nhiều box → box ôm đúng từng ổ). Zip + upload Drive.

### Success
- [ ] data v3 có lát với ≥2 box, vẽ ra box ôm đúng từng ổ.
- [ ] đáp án train đúng format `[[..],[..]]`.
- [ ] augment giữ đúng tất cả box sau biến đổi (test local).

### Rủi ro
- Sort thứ tự box: dùng (y,x) cố định → train ổn định; eval KHÔNG phụ thuộc thứ tự (Hungarian).
- u quá nhỏ < MIN_LESION_PX bị bỏ → giảm vài mẫu, chấp nhận (đó là lát noise).

---

## PHASE 2 — W_POS=3 + train lại
**Deliver:** model mới train trên data v3 multi-box, W_POS=3.

### File
- Sửa: cell `train` (`W_POS=3`; `WeightedTrainer.compute_loss` pop `_gt_boxes` thay `_gt_box`; `LiverDS`).
- Output ckpt mới: `gemma4_v3`.

### Bước
1. `W_POS = 3` (W_NEG=1).
2. `compute_loss`: `inputs.pop("_gt_boxes", None)` (chỉ cần `_is_pos` cho weight; box chưa vào loss — GIoU để sau).
3. Train 5 epoch, best-by-val (giữ callback cũ), lưu `gemma4_v3`.
4. Theo dõi: eval_loss giảm; diag sau train in vài lát đa ổ xem model có ra nhiều box không.

### Success
- [ ] train chạy không lỗi format multi-box.
- [ ] diag: lát đa ổ → model ra ≥2 box (ít nhất thử).
- [ ] best-by-val lưu được `gemma4_v3`.

### Rủi ro
- Model có thể vẫn ra 1 box trên lát đa ổ (chưa học multi) → đo recall đa ổ ở Phase 3, không kỳ vọng cao ngay.
- W_POS=3 → FP có thể tăng; theo dõi ở eval.

---

## PHASE 3 — Eval restructure (PREDICT → JSON → ANALYZE)
**Deliver:** eval tách 2 tầng, metric multi-box (Hungarian), sửa bug, bootstrap CI, cal/test tách.

### File
- Sửa: cell `sec8` (`predict_box` parse **nhiều** box; `conf_logprob` chỉ token toạ độ; `conf_spatial` so 2 TẬP box).
- Thay: cell `sec9` → **PREDICT** (đoán test+cal, lưu JSON). Cells `1JZwDbmBDdnw/ev_metric/sec10/sec11` → **ANALYZE** đọc JSON.

### Bước
1. **PREDICT cell:** vòng qua test + cal, mỗi mẫu lưu:
   ```python
   {pid, is_pos, gt_boxes, pred_boxes, logprob, spatial, selfconf, n_gt, n_pred}
   ```
   ghi `eval_predictions.json` trên Drive. (Chạy nặng 1 lần.)
2. **Sửa bug logprob** (`conf_logprob`): chỉ lấy logprob token là **chữ số** (lọc theo decode token ∈ '0123456789'), `mean` trên đó; rỗng→fallback.
3. **conf_spatial multi-box:** 5 lần đoán → mỗi lần 1 tập box. Độ nhất quán = trung bình "matched-IoU giữa từng cặp lần" (Hungarian giữa 2 tập, lấy mean IoU cặp khớp).
4. **ANALYZE — metric (đọc JSON, không predict):**
   - IoU/precision/recall/f1 per-slice qua **Hungarian matching** (mượn `hungarian_matching` của `evaluator_reg.py`): match pred↔gt theo IoU, "đúng" = IoU≥ngưỡng.
   - `acc@0.1/0.25/0.5/0.75` = %(matched-IoU > ngưỡng).
   - FP%/recall trên lát âm (n_gt=0).
   - Per-patient: gộp theo `pid` (mean các chỉ số), n=số bệnh nhân.
   - **Phân tầng 1-ổ vs nhiều-ổ** (n_gt==1 vs >=2): báo riêng.
   - **Bootstrap CI:** resample bệnh nhân (with replacement) ≥2000 lần → CI cho IoU/acc/Spearman/AUROC.
     ```python
     def boot_ci(per_patient_vals, n=2000):
         arr = np.array(per_patient_vals); idx = np.arange(len(arr))
         means = [np.mean(arr[np.random.choice(idx, len(idx), replace=True)]) for _ in range(n)]
         return np.percentile(means, [2.5, 97.5])
     ```
5. **ANALYZE — Hướng-1:**
   - **Bug AUROC:** flip per-signal `roc_auc_score(c25, v if rho>=0 else -v)`.
   - **cal chọn:** trên `cal_rows` (per-patient) tính Spearman/AUROC 3 tín hiệu → chọn tín hiệu + ngưỡng conformal **trên cal**.
   - **test báo cáo:** áp tín hiệu+ngưỡng đã chọn lên `test_rows`, báo risk-coverage/conformal trên test.
   - **Vẽ chart cả 3** tín hiệu (logprob/spatial/selfconf), không chỉ BEST.

### Success
- [ ] PREDICT chạy 1 lần → JSON; ANALYZE chạy lại nhiều lần không cần GPU nặng.
- [ ] logprob Spearman lật về **dương** sau sửa (kỳ vọng).
- [ ] metric có precision/recall/f1 + acc@4 ngưỡng + CI, tách 1-ổ/nhiều-ổ.
- [ ] cal chọn ngưỡng, test báo cáo (không trùng).

### Rủi ro
- Hungarian + multi-box parse dễ sai → test trên vài mẫu tay trước.
- conf_spatial multi-box phức tạp → nếu kẹt, tạm để spatial = consistency của box ĐẦU TIÊN, note lại.

---

## PHASE 4 — Baseline + so sánh
**Deliver:** bảng so sánh zero-shot vs fine-tuned trên cùng test + metric.

### Bước
1. Load Gemma4 **chưa fine-tune** → chạy **PREDICT cell** (cùng code) → `eval_predictions_baseline.json`.
2. ANALYZE trên baseline JSON → bảng: |IoU|acc25/50/75|recall|FP| cho **zero-shot vs gemma4_v3**.
3. (tùy) chạy lại `gemma4_v2` cũ trên full test nếu muốn so "trước/sau sửa data".

### Success
- [ ] bảng 2 dòng (zero-shot vs fine-tuned), cùng test, cùng metric.

---

## Câu hỏi mở / cần chú ý
- **MIN_LESION_PX**: chọn 30px (~? cm²) — chạy 2 giá trị xem kết luận đổi không (sensitivity).
- **conf_spatial multi-box**: cách ghép tập box giữa các lần đoán — nếu phức tạp quá thì giản lược + note.
- **Train có thật sự học multi-box không**: nếu model cố chấp 1 box → recall đa ổ thấp, là phát hiện đáng báo cáo (không phải lỗi code).
- Mọi số báo **n theo bệnh nhân** + CI.

## Thứ tự thực thi
Phase 1 (local + upload) → Phase 2 (Colab train) → Phase 3 (Colab predict 1 lần + analyze) → Phase 4 (baseline).
