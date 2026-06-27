# AUDIT ĐỘ TIN CẬY kết quả gemma4_v2 (2026-06-27)

> Nguồn: workflow 13 agent (scout verify số + đọc code, 5 panel, cross-exam, tổng hợp).
> Kết quả gốc: IoU per-slice 0.301 / per-patient 0.294 (n=25 ca dương), FP 2%, recall 62%,
> tín hiệu Hướng-1: logprob -0.865/AUROC0.013, spatial +0.924/0.974, selfconf +0.860/0.974.

## TIN TỚI ĐÂU
**DÁM BÁO (đứng vững):**
- FP 2% (3/135 lát âm) — số SẠCH nhất (không dính nhãn đa ổ, không gộp per-patient). Mạnh nhất.
- Recall detect 62% (76/122) — kèm caveat sót 38%.
- "Có tín hiệu confidence" (Spearman |rho| 0.86-0.92, p≪0.001) — cấu trúc THẬT, kể cả logprob (chỉ ngược chiều).
- eval_loss giảm đều 0.336→0.251, CHƯA plateau → train thêm có thể còn lợi.

**KÈM CAVEAT NẶNG:**
- IoU 0.30 — chỉ báo khi kèm (a) CI bootstrap (~[0.17,0.42], rộng gần 3× mức "cải thiện"), (b) ghi n=25 KHÔNG phải 257, (c) cảnh báo 35% lát đa ổ = nhãn rác → 0.30 là số LAI 2 phân bố.
- "per-patient" = mean-of-slice, KHÔNG phải IoU 3D → đổi tên/ghi chú.

**BỎ / chỉ là minh hoạ phương pháp (KHÔNG làm bằng chứng):**
- AUROC 0.974 = 150/154 do n=25; đổi 2-3 ca biên tụt còn 0.90.
- "BEST=spatial" — spatial 0.924 vs selfconf 0.860 chênh 0.064 trên 25 điểm = KHÔNG có ý nghĩa thống kê.
- Risk-coverage 0.294→0.664 — coverage 25% = 6/25 ca, đường mượt là ảo giác mẫu nhỏ.
- Conformal selIoU 0.408/Cost 0.88 — hiệu chỉnh + đánh giá cùng cỡ mẫu n=25 → bảo hành coverage không tin được. (Cost 0.88 = 11/17 ca trả lời bị sai → gate gần vô dụng ở ngưỡng IoU 0.5.)

## 🐞 BUG CHẮC CHẮN PHẢI SỬA
1. **logprob mean toàn chuỗi** (cell sec8): `np.mean(lps)` gồm cả token khuôn mẫu (`<ref>...<box>[[`) logprob≈0 → length bias → tương quan NGƯỢC -0.865. KHÔNG phải đảo dấu code. Sửa: chỉ lấy logprob token TỌA ĐỘ (chữ số), hoặc min/sum.
2. **Bảng AUROC không flip-per-signal** (cell sec11): in `roc_auc_score(c25, v)` thô → logprob hiện 0.013 (≈1-0.987) trông "vô dụng" trong khi phân tách gần hoàn hảo, chỉ ngược chiều. Sửa: `roc_auc_score(c25, v if rho>=0 else -v)`. ⚠️ Sau sửa "BEST=spatial" CÓ THỂ ĐỔI (logprob lật về ≈0.987).
3. **Pipeline đơn-box trên 35% data đa ổ** (fmt/util): GT box bao trùm = rác. Sửa: tách IoU đơn-ổ (n_box==1) vs đa ổ (>=2), báo RIÊNG; đa ổ dùng best-IoU matching per-GT-box.

**KHÔNG phải bug (đừng sửa nhầm):**
- Conformal "im8/sai11/trả lời17": `sai 11` là TẬP CON của `trả lời 17` (6 đúng+11 sai); `trả lời17+im8=25`. Chỉ đổi nhãn cho rõ.
- spatial=selfconf=0.974: artefact AUROC rời rạc trên n=25 (150/154), 2 hàm độc lập, KHÔNG leak.

## ❌ "Cải tiến 0.07→0.30" CHƯA BẢO VỆ ĐƯỢC
- 0.07 đo trên EVAL_LIMIT=40 (~4 bệnh nhân) ; 0.30 trên full 257 → KHÁC tập đo, so vô nghĩa.
- Đổi 5 thứ cùng lúc (data v2+augment+w_pos+5epoch+tắt GC) → confounded.
- → BỎ mệnh đề "cải tiến 4×" tới khi chạy lại model CŨ trên full 257.

## ✅ VIỆC LÀM (ưu tiên, rẻ trước)
1. **Bootstrap CI** (n=25, resample BỆNH NHÂN, ≥2000 lần, ~20p) → CI cho IoU/Spearman/AUROC/risk-coverage. Rẻ nhất, bắt buộc. CI các AUROC chồng nhau → ngừng nói "BEST=spatial".
2. **Sửa bug 1+2** (logprob token tọa độ + flip AUROC per-signal) → đo lại.
3. **Tách IoU đơn-ổ vs đa ổ** → trước khi tách đừng trích "0.30".
4. **Chạy lại model CŨ trên full 257** → mới có số so sánh.
5. **Baseline Gemma4 zero-shot** trên cùng 257.
6. **Tách cal (235, đã có) để chọn BEST+conformal, test để báo cáo** → bỏ bias lựa chọn.

**Một dòng:** DÁM đứng trước thầy = FP 2% + recall 62% + "có tín hiệu confidence". Còn lại (IoU 0.30, AUROC, conformal, "cải tiến 4×") = PILOT n=25, chỉ báo kèm CI + caveat.
