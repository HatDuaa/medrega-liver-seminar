# Nhật ký dự án — Seminar MedRegA

> Ghi lại các quyết định + việc đã làm, để cả nhóm theo dõi. Cập nhật dần.
> Cập nhật gần nhất: 2026-06-27 (sau khi train Gemma 4 + full vision, có kết quả Hướng 1).

---

## 1. Bối cảnh & quyết định chốt
- **Paper:** MedRegA (ICLR 2025) — MLLM y khoa region-centric (sinh báo cáo + định vị bằng bounding box dạng text `<ref>...</ref><box>[[x1,y1,x2,y2]]</box>`, toạ độ [0,1000)). Base gốc: InternVL (~40B). Code tác giả đã clone về `code_tac_gia/MedRegA/`.
- **Backbone nhóm chọn:** **Gemma 4 E4B** (`google/gemma-4-E4B-it`) — ĐÃ XÁC MINH có thật trên HF (ra sau 1/2026). Trước đó dùng `gemma-3n-e4b-it`, đã đổi sang Gemma 4.
  - ⚠️ Gemma 4 đổi kiến trúc: lớp attention bọc trong `Gemma4ClippableLinear` → LoRA phải nhắm `q_proj.linear` (inner) chứ không phải `q_proj`.
- **Hướng cải tiến CHÍNH:** Hướng 1 — **selective prediction / abstention** ("dạy AI biết khi nào nên im lặng"). Post-hoc trên model đã fine-tune.
  - Phụ (nếu dư): Hướng 2 (kiểm định nhân quả Regional CoT), Hướng 3 (meta-evaluation).
- **Phần cứng:** Colab **A100** (bf16, không cần 4-bit). bf16 LoRA + (tuỳ) full vision.

## 2. Dữ liệu (LiTS u gan CT)
- **LiTS** (Kaggle `andrewmvd/liver-tumor-segmentation` + `-part-2`, 131 ca) = data CHÍNH (ảnh + mask → sinh box).
- **data_liver** (cũ): 2 lát/ca → 249 mẫu. **ĐÃ NÂNG CẤP →**
- **data_multi** (đang dùng): **5 lát dương (u lớn nhất) + 5 lát âm/ca → 1238 mẫu** (585 dương / 653 âm, 131 ca). Cắt local bằng `code/prep_data_multi_local.py`, zip up Drive `medrega/data_multi/`.
  - Split THEO BỆNH NHÂN: **train 746 / cal 235 / test 257** (78/26/27 ca, **không trùng → không lộ dữ liệu**).
- Windowing HU (WL=40, WW=400); box [0,1000). MedRegInstruct chỉ mượn format (ảnh nặng, không chạy).

## 3. Notebook & code
- **`code/medrega_finetune.ipynb`** (CHÍNH, train + eval, chạy A100): setup → data_multi → load Gemma4 bf16 → format (prompt 2-opt cho train, có công tắc test 2-opt/3-opt) → train → eval Hướng 1.
- **`code/medrega_pipeline.ipynb`**: bản baseline zero-shot (PHẦN A) — đã chạy, dùng làm "before".
- **`code/prep_data_multi_local.py`**: cắt nhiều lát/ca (chạy local, ra 1238 mẫu).
- **`code_tac_gia/MedRegA/`**: code gốc tác giả (đối chiếu): box chia **999**, inference greedy+beam5, **KHÔNG có abstain** ở task detection (chỉ "No Finding" ở task chẩn đoán) → **Hướng 1 lấp đúng khoảng trống này**.

## 4. KẾT QUẢ (cập nhật 2026-06-27)
### Hành trình (câu chuyện cho báo cáo)
1. **Zero-shot** (chưa train): mù task — 3 cách prompt cho 3 hành vi vô dụng (luôn-có / luôn-không / luôn-"Uncertain"). IoU≈0.
2. **LoRA-LLM 150 mẫu**: **collapse** — model luôn nói "No tumor" (né task). IoU≈0.015.
3. **LoRA-LLM 1238 mẫu**: **hết collapse** — chịu vẽ box + biết im trên ca âm, nhưng định vị còn kém (IoU 0.015, vision đóng băng).
4. **Gemma 4 + full vision fp32 (1238 mẫu)**: **ĐỊNH VỊ ĐƯỢC** — box bám sát u (~0.3 IoU ở ví dụ), abstain đúng ca âm. ⭐ kết quả tốt nhất.

### Số liệu Hướng 1 (Gemma4 + full vision, test 40 ảnh, N_SAMPLES=5)
- **IoU TB: 0.073** | IoU max ~0.3 | đúng @IoU≥0.5: 0% (box gần nhưng chưa đạt ngưỡng chặt).
- **Gate (tín hiệu dự báo IoU):** spatial **Spearman +0.761** (rất mạnh!), logprob −0.344, selfconf nan.
- **Risk-coverage:** selective IoU TĂNG khi giảm coverage: 0.073 (100%) → 0.091 (80%) → 0.121 (60%) → **0.182 (40%)** → **gate HOẠT ĐỘNG** (spatial xếp hạng ca đúng/sai tốt).
- **Train:** loss giảm mượt 0.91→0.3 (không nổ nhờ vision fp32 + LR 2 nhóm: LoRA 2e-4 / vision 1e-5). Model full đã lưu Drive `model/checkpoints/gemma4_vision_full`.

### Nhận xét (đã chỉnh theo review subagent)
- ✅ Chứng minh được **chuỗi before→after**: fine-tune (đặc biệt mở vision) giúp model định vị; tín hiệu spatial CÓ vẻ dự báo độ đúng (Spearman 0.761).
- ⚠️ **KHÔNG được khẳng định "spatial rất mạnh"**: số liệu chạy trên **EVAL_LIMIT=40 → chỉ 20 ca dương**, mà 5 lát/bệnh nhân **tương quan** (lát kề gần trùng) → n hiệu dụng = số bệnh nhân (~vài ca), CI rất rộng. Phải **chạy full test (257) + report PER-PATIENT + bootstrap CI** mới đưa vào báo cáo.
- ⚠️ EVAL_LIMIT=40 lấy **40 mẫu ĐẦU** (không shuffle) → thiên lệch vài bệnh nhân đầu. Cần lấy mẫu ngẫu nhiên/full.
- ⚠️ IoU tuyệt đối thấp (0.073, 0% đạt 0.5) — box đúng vùng nhưng chưa khít.

## 5. CẦN SỬA / CẢI THIỆN (ưu tiên — đã rà bằng subagent review 2026-06-27)

### A. LỖI PHƯƠNG PHÁP (sửa TRƯỚC khi đưa số vào báo cáo)
1. **[Cao] Conformal ngưỡng=0 — nguyên nhân THẬT (worklog cũ ghi sai):** KHÔNG phải "thiếu cal". Mà do (a) phân nhóm theo `modality` **vô nghĩa** (mọi mẫu = "ct_liver"), (b) phân phối `conf_spatial` **degenerate dồn về 0** (ca khó/âm → box rời → IoU cặp=0) → quantile(30%)=0 → trả lời tất. **Fix:** bỏ nhóm modality; calibrate ngưỡng trên **độ tự tin của ca ĐÚNG** ở cal (không lấy quantile trên cả ca sai); dùng full cal dương; nếu tín hiệu dồn 0 thì báo trung thực "không tách được ở coverage 70%". **Vẽ histogram spatial cal/test để xác nhận.**
2. **[Cao] Cỡ mẫu + tương quan (xem mục 4 Nhận xét):** chạy **full test (EVAL_LIMIT=None)**, report **per-patient** (gộp lát cùng bệnh nhân) + **bootstrap CI** theo bệnh nhân. EVAL_LIMIT=40 → 20 ca dương thuộc **rất ít bệnh nhân** (phải đếm `len(set(patient_id))` thực tế); full test 257 có khoảng ~13 bệnh nhân dương → ghi rõ là **pilot/PoC**, không phải bằng chứng mạnh.
3. **[TB] Risk-coverage:** đúng công thức, nhưng cần **đường baseline ngẫu nhiên** (shuffle tín hiệu) + CI để chứng minh gate hơn random (đang tính trên 20 điểm phụ thuộc).

### B. BUG CODE
4. **[Cao] Cell phân tích (`1JZwDbmBDdnw`) CRASH** — dùng `cal_rows` **chưa định nghĩa ở đâu** → NameError (nên không có output). Phải tạo `cal_rows` (predict conf_spatial trên cal 1 lần, cache) trước khi phân tích conformal.
5. **[Cao] `conf_self` ra nan** — `build_infer_inputs` dùng `INSTRUCT_PROMPT_TEST` cố định, **bỏ qua** `rec["question"]` → câu hỏi tự tin không tới model; `re.findall(\d+)` bắt nhầm **toạ độ box**. **Fix:** thêm tham số `prompt` vào `build_infer_inputs`, truyền `CONF_PROMPT` riêng yêu cầu **CHỈ 1 số 0-100, không kèm box**; parse cho đúng.
6. **[TB] `BEST` không nhất quán + LỖI DẤU:** `sec10` hardcode "spatial" còn sec9 auto-chọn theo |Spearman|. Nguy: `logprob` Spearman **−0.344 (ÂM)** — nếu chọn theo trị tuyệt đối rồi `argsort(-sig)` sẽ **xếp hạng ngược** → gate phản tác dụng. **Fix:** 1 biến BEST tính 1 chỗ, **xử lý dấu** (chỉ nhận ρ dương hoặc lật dấu tín hiệu âm).
7. **[TB] AUROC nan:** đa ngưỡng @0.1/0.25/0.5 hợp lý, nhưng n=20 + spatial dồn 0 → AUROC bất ổn. **Dùng Spearman + risk-coverage làm chính, AUROC phụ.**
8. **[Thấp] `parse_box`** lấy 4 số đầu — rủi ro nếu output lẫn số khác; nên ưu tiên regex bắt riêng `<box>[[...]]`.

### C. CẢI THIỆN / REPRODUCIBILITY
9. **[TB] Overfit:** train **không** `load_best_model_at_end` → lưu epoch CUỐI (dễ overfit 170M/746). **Fix:** `load_best_model_at_end=True, metric_for_best_model="eval_loss"` (hoặc tốt hơn: chọn theo IoU trên cal).
10. **[Thấp] Reproducibility:** `conf_spatial` dùng `do_sample=True temp=0.7` **không seed** → Spearman dao động mỗi lần chạy. Seed generation / tăng N_SAMPLES / báo cáo trung bình nhiều seed.
11. **[Thấp] Cache ra ĐĨA** (không chỉ RAM) — kernel Colab dễ mất; tách "predict (chậm, cache file)" vs "analyze (nhanh, đọc cache)".
12. **[Thấp] merge_and_unload:** lý do đúng (PEFT chỉ lưu LoRA, vision full không lưu). Lưu ý vision cast **fp32** lúc train → kiểm dtype khi lưu/reload cho khớp.

### D. PHÁT HIỆN THÊM (review vòng 2 — phương pháp, dễ bị phản biện)
13. **[Cao] Data "5 lát U LỚN NHẤT" làm DỄ HOÁ test:** chỉ lấy lát quanh u to nhất/bệnh nhân → test thiên về u to/dễ, mỗi bệnh nhân ~1 u ở vị trí gần cố định (5 GT box ~ trùng nhau) → IoU/Spearman **bị thổi phồng** so với lâm sàng (u nhỏ/đa ổ/ranh giới mờ bị loại); model có thể học "vị trí trung bình" thay vì nhìn ảnh. **Bắt buộc ghi vào mục Limitations báo cáo**; lý tưởng thêm vài lát u nhỏ/đa ổ.
14. **[TB] Prompt train 2-opt vs eval 3-opt:** train chưa từng thấy nhãn "Uncertain" → nếu báo số chạy prompt 3-opt là **out-of-distribution**, abstain kiểu đó không phản ánh năng lực đã học. **Phải nói rõ số nào chạy prompt nào.** Thêm: hệ toạ độ tác giả /999 vs nhóm /1000 — nhất quán nếu so trực tiếp số paper.
15. **[Cao] CHỈ đánh giá ca DƯƠNG — bỏ trống năng lực abstain trên ca ÂM:** toàn bộ gate/risk-coverage/Spearman chạy trên `pos`. Thiếu **metric định lượng cho ca âm**: model im đúng / bịa box (false positive) trên 653 ca âm. Đây là **nửa quan trọng của Hướng 1** ("biết khi nào im"). **Thêm:** confusion matrix có-u/không-u + FP rate trên ca âm + selective metric tính cả âm lẫn dương.
16. **[Thấp] Beam search:** KHÔNG đổi — greedy (box chính) + sampling temp=0.7 (spatial) là lựa chọn HỢP LÝ cho Hướng 1 (beam làm logprob khó diễn giải + mâu thuẫn đo consistency). Chỉ thử beam5 như dòng so sánh "khớp setup tác giả" nếu dư thời gian.

### Điểm LÀM ĐÚNG (giữ): split theo bệnh nhân (có assert), `conf_spatial` KHÔNG rò rỉ GT, công thức risk-coverage đúng, lý do merge_and_unload, greedy+sampling cho Hướng 1.

### ĐÃ SỬA VÀO FILE `medrega_finetune.ipynb` (2026-06-27):
- ✅ **B2 conf_self**: `build_infer_inputs` thêm tham số `prompt`; conf_self dùng `CONF_PROMPT` riêng hỏi tự tin.
- ✅ **B1 cal_rows**: định nghĩa trong cell EVAL 3/4 (predict nặng).
- ✅ **B4 BEST + dấu**: auto chọn theo |Spearman|, lật dấu nếu ρ âm (cell EVAL 4/4).
- ✅ **A1 conformal**: bỏ nhóm modality, calibrate toàn cục trên cal (CAL_LIMIT=60), báo "degenerate" nếu ngưỡng dồn min.
- ✅ **#15 metric ca ÂM**: cell EVAL 2/4 in FP rate (bịa u) + im đúng trên ca âm.
- ✅ Gate @0.1/0.25/0.5 + AUROC@.25 (giữ). Eval tách 4 cell: predict nhẹ → phân tích → predict nặng → phân tích đầy đủ (cache RAM).
- ✅ **Train cell = bản chốt** (full vision+connector, LoRA LLM r=32, best-by-val). Thêm cell load-from-checkpoint cho eval sau reconnect.
- CÒN LẠI (việc CHẠY, không phải sửa code): #A2 chạy full test 257 + per-patient + bootstrap CI; #13/#14 viết mục Limitations.

### ⏳ CHƯA LÀM — phát hiện 2026-06-27 (sau khi review run gemma4_final):
- **[Cao] Model học THUỘC VỊ TRÍ, không định vị thật.** Bằng chứng: box luôn quanh thuỳ trên-trái gan (vị trí u phổ biến trong train); u ở chỗ lạ (pid=77 góc dưới-phải) → **bỏ sót**. Thực tế u gan **đa dạng vị trí** (8 phân thuỳ, 2 thuỳ) → prior 1-vị-trí là SAI lâm sàng. Gốc = data-bias #13.
  - **→ SỬA cell cắt data (`prep_data_multi_local.py`): lấy lát u NGẪU NHIÊN + lát u LỚN NHẤT** (thay vì chỉ top-5 lớn nhất) → đa dạng vị trí u. CHƯA LÀM.
- **[TB] (tuỳ) Box-overlap loss (soft-coordinate GIoU)** — token-loss ≠ IoU; cân nhắc thêm box-loss. CHƯA LÀM. Lưu ý: phải dùng GIoU (không raw IoU) vì box thường KHÔNG overlap → raw IoU gradient = 0. Và data đa vị trí quan trọng hơn loss.

### 💡 Ý TƯỞNG CẢI THIỆN (thảo luận 2026-06-27 — CHƯA làm, để cải tiến vòng sau)

**Chẩn đoán gốc:** model học **PRIOR VỊ TRÍ** (box quanh thuỳ trên-trái gan = vị trí u phổ biến trong train), **sót u ở vị trí lạ** (pid=77 góc dưới-phải). Thực tế u gan đa dạng vị trí (8 phân thuỳ, 2 thuỳ). → 0% bịa u (tốt) NHƯNG recall thấp (sót u) + box lệch (token-loss ≠ IoU).

**A. DATA (đòn gốc, quan trọng nhất):**
1. Cắt lát u **NGẪU NHIÊN + LỚN NHẤT** (thay vì chỉ top-5 lớn nhất) → đa dạng vị trí. *(Lưu ý: random slice 1 mình CHƯA đủ phá prior vì 1 bệnh nhân ≈ 1 vị trí u; đa dạng vị trí chủ yếu từ số bệnh nhân.)*
2. **Augmentation** (biến đổi cả ảnh LẪN box): **flip ngang + dịch (translation) + xoay NHẸ ±10-15°** → phá prior vị trí, ép định vị thật. **KHÔNG xoay lớn/90°** (CT hướng chuẩn, xoay nhiều = phi lâm sàng).

**B. LOSS (sau khi sửa data, nếu box vẫn lệch):**
3. **Box-overlap loss = soft-coordinate + GIoU**:
   - Soft-coordinate: tại token toạ độ, tính **kỳ vọng** từ phân phối chữ số (vd 3×0.7+4×0.2=3.1) → toạ độ liên tục → KHẢ VI (backprop được). (Box sinh dạng token rời rạc thì KHÔNG khả vi → phải làm mềm.)
   - Dùng **GIoU (KHÔNG raw IoU)**: box thường KHÔNG overlap → raw IoU gradient=0 (vô dụng); GIoU phạt theo khoảng cách → có gradient kể cả khi lệch → kéo box về GT.
   - Gộp: `loss = CE + λ·(1−GIoU)` (GIoU chỉ ca dương).
4. **Cân bằng dương/âm (chống model lười nói "no tumor"):**
   - **LOSS:** `w_pos > w_neg` (vd 2:1) → ca dương đáng giá hơn → model không ăn điểm rẻ bằng cách toàn nói no-tumor.
   - **METRIC (báo cáo, chống gaming):** ca dương = 0.5 (phát hiện đúng) + 0.5×GIoU (box) → tới 1.0; ca âm đúng = **cap 0.5-0.75** (KHÔNG full 1.0) → "phát hiện+định vị u" đáng hơn "im trên ảnh khoẻ".

**C. TRAIN (vặt):**
5. Hiện loss **từng STEP**: đổi `eval_strategy="steps", eval_steps=93` (≈1 epoch).
6. **5 epoch** chỉ hợp với DATA MỚI (data cũ overfit ở epoch 2). Best-by-val tự lưu epoch tốt nhất → train dư epoch không hại (chỉ tốn giờ); thấy overfit dừng sớm cũng được.

**Thứ tự đề xuất:** sửa data (random+augment) → train lại (5 epoch, best-by-val) → EVAL full (EVAL_LIMIT=None) → nếu box vẫn lệch thì thêm GIoU loss + w_pos → thêm metric 0.5/0.5 cho báo cáo.

### THỨ TỰ SỬA (review chốt — sau đây coi như hội tụ):
1. Sửa bug code **B1 (cal_rows)** + **B2 (conf_self)** + **B4 (BEST dấu)** + **A1 (conformal)** → để chạy lại được.
2. Chạy **full test (257) per-patient + bootstrap CI** (A2).
3. Thêm **metric ca âm** (#15: confusion matrix + FP rate).
4. Chốt số + viết mục **Limitations** (#13 data u-lớn-nhất, #14 prompt/scale).

## 6. Việc tiếp theo
1. Sửa `conf_self` → chạy lại eval → bảng đủ 3 tín hiệu.
2. Đổi gate sang đa ngưỡng (@0.1/0.25/0.5) → AUROC ra số.
3. Tách cell predict/analyze (cache RAM) cho gọn + chạy lại nhanh.
4. Chạy eval đầy đủ (EVAL_LIMIT=None, 257 ảnh) cho số liệu báo cáo.
5. Viết phần kết quả + biểu đồ vào báo cáo (before/after + risk-coverage).

## 7. Điểm cần nhớ / cảnh báo
- ⚠️ **Gemma 4**: LoRA nhắm `*.linear` (inner của Gemma4ClippableLinear), không phải `q_proj` trực tiếp.
- ⚠️ **Full vision train**: phải **cast fp32** + LR thấp (1e-5) + 2 nhóm LR, nếu không **nổ số (NaN)**. bf16 raw train vision = nổ.
- ⚠️ **Overfit**: full vision 170M / 746 mẫu dễ overfit — chỉ biết qua **eval test**, không nhìn loss train.
- ⚠️ **Eval test ≠ train data**: eval không cập nhật weights (model không học từ eval). Monitor overfit bằng **cal**, để test cho số cuối.
- Split LUÔN theo `patient_id`.
- Box [0,1000) (tác giả 999, lệch 0.1% kệ được).

---

## 2026-06-27 — Cải tiến vòng 2 (implement + review loop)

**Đã làm (theo `plan_cai_tien.md`):**
- **P1 data v2** (`prep_data_multi_v2.py`): 2 lát u lớn nhất + 3 lát NGẪU NHIÊN (thay top-5). 1238 mẫu (585+/653-).
  - ⚠️ Random slice KHÔNG tăng đa dạng vị trí (std v1 x116/y145 → v2 x113/y154 ≈ bằng): 1 bệnh nhân ≈ 1 vị trí u, đổi lát không đổi (x,y). **Augment dịch mới là đòn phá prior.** v2 vẫn lợi: đa dạng CỠ/HÌNH u.
- **P2 augment on-the-fly** (cell `fmt`): dịch ±18% / xoay ±12° / scale ±10% / sáng nhẹ. KHÔNG flip/xoay90 (CT gan). Box biến đổi theo (test hình học PASS). CHỈ train (val `aug=False`).
- **P3 loss** (cell `train`): `WeightedTrainer` — CE ×W_POS(2) ca dương / ×W_NEG(1) ca âm → chống lười no-tumor. Helper `_giou_loss` sẵn (soft-coordinate = bước sau, cần verify tokenizer Gemma trên Colab).
- **P4 metric** (cell `ev_metric`): điểm công bằng — dương khít=0.3+0.7×IoU, sót=0, âm đúng=0.5, bịa=0 + recall/loc25/FP.
- **P5 config**: EPOCHS=5, eval theo step (hiện loss).

**Review vòng 1 (subagent) → đã sửa 4 lỗi:**
1. eval_loss méo do W_POS → KHÔNG weight lúc eval (`if model.training`).
2. Augment đẩy u ra ngoài → trước biến nhãn dương→âm (nhiễm) → nay GIỮ ảnh+box gốc.
3. Dịch ±12% yếu → tăng ±18%.
4. Metric box-bừa ăn 0.5 quá rộng → 0.3+0.7×IoU.
(Reviewer nhầm MODEL_ID gemma-4 — không biết Gemma 4 đã ra; đã verify thật.)

**User cần làm trước khi chạy:** (a) zip + upload `data_liver_multi_v2.zip` lên Drive; (b) đặt `EVAL_LIMIT=None` cho eval full.

---

## 2026-06-27 — PANEL METHODOLOGY (14 agent: scout→5 quan điểm→cross-exam→tổng hợp)

**Câu hỏi:** eval per-slice có sai không, có nên đổi sang per-patient "có u/không"? Toàn workflow đúng methodology chưa?

**PHÁN QUYẾT: user đúng 60% (chẩn đoán), sai 40% (phương thuốc).**
- ĐÚNG (5/5 nhất trí): per-slice IoU = **pseudoreplication** (5 lát/bn tương quan → n thật ≈ số BỆNH NHÂN ~13 ca dương, không phải số lát). Lát rìa z u-vài-pixel = **label noise** (IoU 0.07 thấp một phần do DATA bẩn). Train per-slice + eval cấp cao hơn = hợp lệ.
- SAI (4/5 phản đối): hạ xuống **binary per-patient "có u/không" = đánh tráo bài toán** → (1) giết localization (cốt lõi MedRegA), (2) LiTS toàn ca dương → bão hòa ~100%, (3) game được (OR trên trăm lát), (4) "đúng" chưa định nghĩa.

**ĐÍCH ĐÚNG = EVAL ĐA CẤP (báo song song, không thay thế):**
- (A) **Per-lesion detection FROC** (sensitivity/lesion @ FP/scan, "hit"=tâm box trong lesion 3D) — METRIC CHÍNH, chuẩn radiology.
- (B) **Localization** IoU CHỈ trên lát u rõ, per-patient median + cluster-bootstrap CI.
- (C) **Abstain/specificity** trên 653 lát ÂM (đây là chỗ DUY NHẤT per-slice đúng đơn vị).

**Lỗi workflow xếp nặng→nhẹ:** [1-DATA] nhãn dương rác (tumor[z]>0 + 3 lát random) → sửa TRƯỚC. [2-EVAL] pseudoreplication + "per-patient" giả (mean-of-slice-IoU, không 3D). [3-EVAL] conformal/risk-coverage/Spearman trên ~10 ca = trang trí, treo lại. [4-TRAIN] GIoU loss đang tắt. [5] train/test đều trên lát tiền-chọn (chưa đo phân phối thật).

**QUYẾT ĐỊNH SCOPE LỚN NHẤT (chờ chủ dự án):** FROC thật cần TOÀN VOLUME, nhưng data là lát rời tiền-chọn → **phải prep lại từ NIfTI** nếu muốn FROC + FP/scan thật; HOẶC chấp nhận chỉ localization trên lát-đã-lọc. Hai cái loại trừ nhau.

**Đánh đổi chưa chốt:** lọc lát rìa diệt noise NHƯNG bỏ luôn u nhỏ <1cm (early HCC, lâm sàng cần nhất). ~13 ca dương → FROC vẫn CI rộng, có thể cần tăng test set. 2.5D có thể bất khả thi nếu lát đã lưu không liền kề.

⚠️ Hướng 1 (selective prediction/conformal) — novelty của nhóm — bị panel đánh giá **thống kê quá yếu trên 27 ca test**; nên trình bày kèm caveat "n nhỏ" hoặc validate trên tập lớn hơn.

---

## 2026-06-27 — AUDIT panel (5 agent soi lỗ hổng panel trước)

**1. Panel ĐÁNH BÙ NHÌN:** phán quyết "user sai 40%" → rút xuống ~0%. Ý THẬT của user (thêm pipeline per-patient GIỮ overlap = IoU TB các lát + chấm dương/âm) ≈ TRÙNG mục (B) panel tự đề xuất. 3 lý do panel bác (giết localization / bão hòa / game) đều sụp khi user giữ overlap. Phần "sai" thật còn lại: mean-IoU-2D per-patient vẫn yếu thống kê (~13 ca) — đó là giới hạn ĐO LƯỜNG, không phải user hiểu sai.

**2. Panel BỎ SÓT (nặng→nhẹ):**
- **[NẶNG NHẤT] KHÔNG có BASELINE** — Gemma zero-shot vs sau fine-tune trên cùng eval. Thiếu thì không chứng minh được "cải tiến". Bảng 2 dòng, bắt buộc.
- **K-FOLD CV theo bệnh nhân** (thay split cố định 27 ca) — chấm ~131 ca, cứu trực tiếp "thống kê yếu". Panel chỉ than mà quên giải pháp này.
- **GT multi-focal SAI** — 1 lát ≥2 khối rời → box min/max bao trùm cả gan lành ở giữa = nhãn rác. Vô hiệu hóa chính đóng góp multi-region của MedRegA. Sửa: connected-components (scipy.ndimage.label) → 1 box/ổ; báo % lát multi-focal.
- **KHÔNG có ABLATION** (w_pos on/off, augment on/off) — chứng minh pipeline hoạt động.
- **"Specificity" GIẢ** — 653 lát âm lấy từ chính bệnh nhân CÓ u → gọi đúng là "intra-patient slice discrimination", không phải specificity lâm sàng.

**3. Panel TỰ MÂU THUẪN / over-engineer:**
- Bất nhất đơn vị: kết tội per-slice dương pseudoreplication nhưng khen 653 lát âm "mạnh" — lát âm cùng bệnh nhân CŨNG tương quan. → dùng 1 chuẩn cluster theo bệnh nhân cho cả 2.
- "Drop lát nhỏ" vs "lát nhỏ = early HCC cần nhất" — chưa giải → STRATIFY theo kích thước, đừng drop.
- **FROC over-engineer** cho seminar: tự thừa nhận CI rộng trên 13 ca → không mạnh hơn per-patient, mà đòi prep lại volume + 3D. Hạ xuống "future work".

**4. LÀM KHÁC:** công nhận ý user đúng + thêm BASELINE + K-FOLD CV + sửa box đa ổ + ablation. KHÔNG cần FROC.

---

## 2026-06-28 — IMPLEMENT Phase 1-3 (multi-box + eval rewrite)

**Phase 1 (data multi-box):** `prep_data_multi_v3.py` — `scipy.ndimage.label` tách từng ổ → 1 box/ổ, lọc ổ <30px. Data v3: 1211 mẫu (558+/653-), **35.5% lát ≥2 box** (sửa lỗi đa ổ). Zip `data_liver_multi_v3.zip` (112MB) sẵn ở code/data/.
**Phase 1 (notebook):** cell `fmt` multi-box (prompt nhiều box + `augment` map list + `_answer_from_boxes`); `util` thêm `parse_boxes`+`match_boxes`(Hungarian)+`box_metrics`; `diag`/`viz_after` vẽ nhiều box.
**Phase 2:** `train` W_POS=3, ckpt `gemma4_v3`, getdata→v3.
**Phase 3 (eval rewrite, PREDICT/ANALYZE):**
- `sec8`: predict_boxes multi-box; **bug logprob fix** (chỉ token chữ số); conf_spatial = set-IoU 2 tập box; conf_self.
- `sec9` = **PREDICT** (test+cal 1 lần) → lưu JSON **tên timestamp duy nhất** vào Drive `checkpoints/eval_runs/` (KHÔNG ghi đè), seed cố định, đọc lại verify.
- `1JZwDbmBDdnw` = **METRICS**: Hungarian → recall/precision@0.1/0.25/0.5/0.75 + mean-IoU + per-patient + **bootstrap CI** + phân tầng 1-ổ/nhiều-ổ + FP lát âm.
- `sec11` = **HƯỚNG-1**: **cal chọn** tín hiệu+ngưỡng / **test báo cáo**, **flip AUROC per-signal**, vẽ **cả 3 tín hiệu**.
- XOÁ `ev_metric` (điểm công bằng) + `sec10`. Metric chuẩn paper (acc=%IoU>thr).

**Review (subagent):** "OK treo máy chạy được" — không crash. Đã sửa thêm: guard `RUN_OLD_CKPT=False` cho cell load model cũ (tránh OOM/nhầm), seed eval, MAX_NEW_TOKENS=192, comment W_POS.
**Local test PASS:** slice_to_boxes, parse_boxes/match_boxes (Hungarian đúng cả sai thứ tự), ANALYZE logic, JSON save (tên duy nhất + reload).

**USER cần:** upload `data_liver_multi_v3.zip` lên Drive → chạy notebook 1 lần (train gemma4_v3 + eval). JSON tự lưu Drive tên riêng mỗi lần.
