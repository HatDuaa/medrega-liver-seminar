# TODO CHÍNH (gom mọi quyết định, 2026-06-28)

> Chi tiết lý do: xem `methodology_todo.md` + `results_audit.md`. File này = checklist hành động.
> Đã chốt: bỏ GIoU loss (để sau), bỏ "điểm công bằng" tự chế, dùng metric chuẩn paper.

## 🟢 NHÓM 1 — Sửa code eval (RẺ, không cần train lại)
### Kiến trúc MỚI: tách PREDICT khỏi ANALYZE (dễ bảo trì)
- [ ] **Cell PREDICT** (chạy nặng 1 lần): đoán hết test + cal → lưu mỗi mẫu
  `{pid, is_pos, gt_boxes[], pred_boxes[], logprob, spatial, selfconf, n_gt, n_pred}` ra **1 file JSON** trên Drive (multi-box).
- [ ] **Cell(s) ANALYZE** (nhẹ, đọc JSON): tính metric/CI/chart — KHÔNG predict lại → chỉnh thoải mái không tốn ~45p.
### Metric (multi-box theo đường B)
- [ ] **Bỏ cell `ev_metric`** ("điểm công bằng") — đồ tự chế, không chuẩn.
- [ ] **IoU qua Hungarian matching** (ghép box đoán↔box thật theo IoU, không theo thứ tự) → **precision/recall/f1 +
  IoU cặp khớp** (giống `SingleRegionMultiObjectEvaluator` tác giả) + **acc@0.1/0.25/0.5/0.75**.
- [ ] **Giữ FP% + recall** trên lát âm (phần thêm của mình).
- [ ] **Phân tầng theo SỐ Ổ (1 ổ vs nhiều ổ) = độ khó** — báo riêng (giờ là độ khó, không còn "rác").
- [ ] **Bootstrap CI** (n=25, resample BỆNH NHÂN ≥2000 lần) cho mọi số.
### Hướng-1 (tín hiệu tự tin)
- [ ] **Bug logprob**: chỉ lấy logprob **token toạ độ** (đang lấy cả token khuôn mẫu → ra −0.865).
- [ ] **Bug AUROC**: flip per-signal `roc_auc_score(c25, v if rho>=0 else -v)`. ⚠️ "BEST" có thể đổi.
- [ ] **Vẽ chart cả 3 tín hiệu** (logprob/spatial/selfconf), KHÔNG chỉ "BEST" → hết bias tự chọn.
- [ ] **Dùng cal (26 bệnh nhân) chọn tín hiệu + ngưỡng conformal; test CHỈ để báo cáo** (bỏ bias lựa chọn).
- [ ] ⚠️ **spatial với multi-box**: mỗi lần đoán giờ là 1 TẬP box → "nhất quán giữa 5 lần" phải ghép tập
  (mean matched-IoU giữa 2 lần) → chỉnh `conf_spatial`.

## 🟠 NHÓM 2 — Sửa DATA + MULTI-BOX (✅ ĐÃ CHỐT: ĐƯỜNG B)
35% lát đa ổ → 1 box bao trùm cả 2 ổ + gan lành = rác → chuyển MULTI-BOX (đúng tinh thần MedRegA multi-region):
- [ ] **Re-prep**: mỗi lát `scipy.ndimage.label` tách từng ổ → **1 box/ổ** (lọc ổ <N px = nhiễu). GT = list box.
- [ ] **Đổi PROMPT** (train + test): "có thể 1 HOẶC NHIỀU u, trả TẤT CẢ box" → `<ref>liver tumor</ref><box>[[..],[..],..]</box>`.
- [ ] **`build_train_example`**: đáp án = multi-box dựng từ list ổ.
- [ ] **Train lại 1 lần** (gộp với W_POS=3 ở nhóm 3).

## 🟡 NHÓM 3 — Sửa LOSS/train (gộp vào 1 lần train lại với data mới)
- [ ] **Tăng W_POS = 3** (ca dương đắt hơn → bớt sót). ⚠️ FP sẽ tăng — chấp nhận (ung thư: sót tệ hơn báo nhầm).

## 🔵 NHÓM 4 — Chạy thêm để SO SÁNH (inference, KHÔNG train)
- [ ] **Baseline Gemma4 zero-shot** (chưa fine-tune) trên ĐÚNG test 257 + ĐÚNG metric → mốc dưới.
- [ ] **Chạy lại model CŨ trên full test** (EVAL_LIMIT=None) → mới có số so sánh thật (số 0.07 cũ vô nghĩa, chỉ 4 ca).

## ⚪ ĐỂ SAU (future work — ghi slide, không làm seminar này)
- GIoU/box-overlap loss (cần kiểm tokenizer Gemma per-digit + test).
- K-fold CV (tốn 5× train), Ablation (tốn train), FROC full-volume.
- Phân tầng IoU theo kích thước u (nếu kịp).

## 📝 FRAMING lúc viết slide
- "Specificity" → gọi đúng "không bịa u trên lát âm (bệnh nhân có u)", đừng nói đặc hiệu lâm sàng.
- Hướng-1 (conformal/risk-coverage) → kèm caveat "n=25, pilot", đừng kết luận mạnh.
- Mọi metric báo **n theo bệnh nhân**.

---
## Luồng thực thi gợi ý
1. NHÓM 2 (sửa data multi-focal) → re-prep.
2. NHÓM 3 (W_POS=3) → **train lại 1 lần** trên data mới.
3. NHÓM 1 (sửa code eval) → eval model mới.
4. NHÓM 4 (baseline + model cũ full test) → bảng so sánh.
