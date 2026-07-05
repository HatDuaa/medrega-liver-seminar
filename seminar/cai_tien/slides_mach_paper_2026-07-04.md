# Slides — Cải tiến MedRegA: fine-tune Gemma 4 E4B phát hiện u gan (LiTS)
### Bản trình bày mạch paper: Gốc → Cải tiến → Kết quả → So sánh → Tương lai

> Nguồn nội dung: [bao_cao_mach_paper_2026-07-04.md](bao_cao_mach_paper_2026-07-04.md). Nguyên tắc: TRUNG THỰC — caveat đặt NGAY trên slide có số liệu. Mỗi slide có gợi ý HÌNH (🖼️) + "câu nói khi trình bày".
> Ký hiệu: 🖼️ = ảnh cần chèn; đường dẫn `../code/...` là ảnh THẬT đã có trong repo; `[HÌNH GỢI Ý: ...]` = ảnh cần lấy từ slide PDF paper hoặc tự dựng.

---

## PHẦN A — PHƯƠNG PHÁP GỐC (MedRegA)

---

### Slide 1 — Vấn đề lâm sàng: vì sao cần "biết vùng"

- Bác sĩ đọc phim theo trình tự: **nhìn toàn ảnh → khoanh vùng nghi ngờ → mô tả vùng → chẩn đoán kèm vị trí**.
- Model **region-agnostic** (không biết vùng): nén cả ảnh thành 1 vector rồi sinh chữ → **bỏ mất bước khoanh vùng** → sai vị trí kéo theo **sai chẩn đoán**, và bác sĩ **không kiểm chứng được** câu trả lời.
- MedRegA vá đúng chỗ này: bắt model **sinh kèm toạ độ vùng** để mỗi nhận định neo vào đúng pixel.
- 🖼️ `../baocao_dich/figures/fig2.png` — *panel (a): MedDr sai vùng (region-agnostic) vs MedRegA đúng vùng (region-centric) trên MRI não (Fig.2 paper)*
- *Câu nói:* "Sai vùng không phải lỗi nhỏ về câu chữ — nó đổi luôn chẩn đoán. Đó là lý do 'region-centric' ra đời."

---

### Slide 2 — Kiến trúc MedRegA (4 khối)

- Xây trên **InternVL 1.2 (~40B tham số)** — 4 khối nối tiếp:
  - **Vision Encoder** ("mắt"): InternViT-6B, ảnh 448×448 → lưới token 32×32.
  - **Pixel Shuffle** (dồn/nén token ảnh, sắp lại để giữ cấu trúc 2D mà giảm số token): nén token ảnh, giữ cấu trúc 2D.
  - **MLP Connector** ("cầu"): chiếu đặc trưng ảnh sang không gian LLM.
  - **LLM** ("não"): Nous-Hermes-2-Yi-34B, sinh chữ + suy luận.
- **Mấu chốt — box viết thành CHỮ:** `<ref>liver tumor</ref><box>[x1,y1,x2,y2]</box>`, toạ độ chuẩn hoá **0–1000**. → biến "khoanh vùng" thành "sinh chữ" quen thuộc của LLM (không cần đầu phát hiện riêng).
- 🖼️ `../baocao_dich/figures/fig4.png` — *luồng Vision Encoder→Alignment→LLM; toạ độ box thành Coordinate/`<ref>`/`<box>` token (Fig.4 paper). Lưu ý fig4 không vẽ khối Pixel Shuffle riêng.*
- *Câu nói:* "Thay vì gắn thêm 'đầu phát hiện', MedRegA dạy model *viết* toạ độ ra như một câu chữ — tận dụng thẳng sức mạnh ngôn ngữ."

---

### Slide 3 — Huấn luyện MedRegA (2 giai đoạn) + 3 task

- **GĐ1 — Alignment (căn chỉnh):** dạy Connector "phiên dịch" ảnh↔chữ trên cặp ảnh–caption, **KHÔNG có box**; Vision + LLM đóng băng.
- **GĐ2 — Instruction tuning:** dạy làm mọi tác vụ theo lệnh trên **MedRegInstruct (790K mẫu = 550K region–text + 240K grounded report, 8 modality, song ngữ Anh–Trung)**; chỉnh LLM, Connector đóng băng lại.
- **3 task region-centric:** (1) Region→Text (box→tên vùng), (2) **Text→Region (phát hiện/định vị)** ← *đồ án mình làm task này*, (3) Grounded Report (báo cáo gắn box).
- **Đặc điểm quan trọng:** loss = **cross-entropy ngôn ngữ thuần** (không có loss hình học riêng cho box); ảnh 3D chỉ lấy **1 lát trung tâm**; tài nguyên **16× H800, vài ngày**.
- 🖼️ `../baocao_dich/figures/fig4.png` — *3 định dạng task region-centric: Region→Text, Text→Region (đồ án làm task này), Grounded Report (Fig.4 paper) — nên khoanh cột Text-to-Region để nhấn task nhóm làm*
- *Câu nói:* "Hai giai đoạn: đầu tiên dạy 'cầu' nối ảnh–chữ, sau đó dạy 'não' làm việc theo lệnh. Box chỉ là chữ, nên vẫn dùng loss ngôn ngữ bình thường."

---

### Slide 4 — Hạn chế của paper gốc (chỗ để mình lấp)

- Dồn gần hết gánh nặng lên **LLM 40B**; **"mắt" và "cầu" gần như bất động** → định vị "được nhưng không sắc" (IoU thấp, hay bỏ sót vùng ở ca nhiều ổ). *IoU (Intersection over Union — độ chồng lấn giữa box dự đoán và box thật, 0–1; càng cao càng khít).*
- **Không có** cơ chế **từ chối khi không chắc** (abstain); **không dùng ca âm** (ảnh không u) → không đo được model có **bịa box** không.
- Đánh giá **per-image** (theo từng lát), **IoU@0.5** (tính là đúng nếu độ chồng lấn ≥ 0.5) — nhiều lát cùng bệnh nhân bị tính như mẫu độc lập (**pseudoreplication** — đơn vị thống kê sai); **không khoảng tin cậy**.
- Chi phí **ngoài tầm** một đồ án sinh viên.
- 🖼️ `../baocao_dich/figures/fig2.png` — *panel (b) radar: w/ Region vs w/o Region — vùng đóng góp lớn (minh hoạ vì sao "mở vùng" quan trọng)*
- *Câu nói:* "Paper mạnh về quy mô và benchmark. Chúng em không nói nó thiếu metric vùng — nó có 4 hạn chế để mình lấp; slide sau là bản đồ vá đúng từng chỗ."

---

### Slide 4b — Khoảng trống & bản đồ cải tiến *(bản lề A→B)*

- **4 đóng góp vá 1-1 các hạn chế trên** — mỗi hạn chế gốc có đúng 1 cải tiến, trỏ sang slide tương ứng ở Phần B:

| Hạn chế gốc | Cải tiến của nhóm (→Slide) |
|---|---|
| Mắt/cầu bất động (định vị không sắc) | **Mở khoá vision** (→Slide 5) |
| 1 lát trung tâm, không ca âm (không đo bịa box) | **Đa lát + ca âm + multi-box** (→Slide 6) |
| Chi phí 16× H800 ngoài tầm | **LoRA 1 GPU** (→Slide 7) |
| Per-image, không CI, không abstain | **Per-patient + CI + selective prediction** (→Slide 8) |

- *Câu nói:* "Đây là bản lề: 4 hạn chế bên trái, 4 lớp vá bên phải — mở khoá thị giác, dữ liệu đa lát + ca âm, huấn luyện 1 GPU, và lớp đánh giá gần lâm sàng. Giờ đi vào từng cái ở Phần B."

---

## PHẦN B — CẢI TIẾN CỦA NHÓM

---

### Slide 5 — Cải tiến (1): đổi backbone — nhỏ hơn 5×, chạy 1 GPU

| | MedRegA gốc | Của nhóm |
|---|---|---|
| Backbone (mô hình xương sống) | InternVL 1.2 (~40B) | **Gemma 4 E4B** (E4B = biến thể ~8B tham số, hiệu dụng ~4B mỗi lượt chạy) |
| Vision (khối thị giác — phần xử lý ảnh) | InternViT-6B (đóng băng) | **SigLIP — nhóm MỞ KHOÁ fine-tune** |
| Chạy trên | 16× H800 | **1×A100 / Colab–Kaggle** |

- *Chú thích: **SigLIP** (bộ mã hoá ảnh — "mắt" của model, dạng CLIP dùng loss sigmoid); **vision tower** (khối thị giác); **fine-tune** (huấn luyện tinh chỉnh lại model).*
- ↩ **Vá hạn chế #1** (mắt/cầu bất động → MỞ KHOÁ vision) **+ #4** (chi phí → 8B, 1 GPU). *(chi tiết hạn chế xem Slide 4.)*
- **Triết lý:** đổi "rộng" (8 modality) lấy "sâu" (1 task, đào kỹ dữ liệu + đánh giá + độ tin cậy).
- **Kết quả nền tảng:** **mở vision tower là bước tạo khác biệt** — đóng băng vision thì IoU ≈ 0.015 (gần như không định vị được), mở khoá thì lên ≈ 0.27. *(cùng cỡ mẫu n=25, CI rộng như Slide 10; đây là 1 lần cấu hình minh hoạ vai trò vision, KHÔNG phải ablation nhiều seed.)*
- ⚠️ *Thủ phản biện "chênh ~18× sao biết không phải may rủi seed":* đây là **1 cặp cấu hình, chưa lặp nhiều seed** nên chỉ minh hoạ **HƯỚNG** tác động của việc mở vision, KHÔNG phải hiệu ứng đo chính xác — cần ablation nhiều seed để chốt.
- 🖼️ `../code/iou_frozen_vs_unfrozen.png` — *bar pIoU: đóng băng vision (0.015) vs mở khoá fine-tune (0.27) — minh hoạ "mở vision tower là bước tạo khác biệt" (1 cặp cấu hình, chưa lặp seed).*
- ⚠️ *KHÔNG* nói "Gemma 4 giỏi hơn MedRegA": Gemma mạnh trên ảnh thường; ở ảnh y khoa phải fine-tune mới cạnh tranh được.
- *Câu nói:* "Đóng góp đầu tiên là chứng minh khả thi: tái tạo năng lực khoanh vùng trên mô hình nhỏ hơn nhiều, chỉ 1 GPU."

---

### Slide 6 — Cải tiến (2): dữ liệu — đa lát, ca âm, multi-box

- **Đa lát** (khác paper chỉ 1 lát trung tâm): mỗi bệnh nhân **2 lát u lớn nhất + 3 lát ngẫu nhiên** → phủ nhiều mức cắt/kích thước u.
- **Ca ÂM (không u):** đưa lát không-u vào để model học "khi nào KHÔNG vẽ box" — paper hoàn toàn thiếu.
- **Multi-box** bằng connected-components (tách các cụm pixel u **DÍNH NHAU** thành từng ổ riêng — dùng `scipy.ndimage.label`): **1 box/ổ**, lọc ổ <30px → sửa nhãn rác (một box gộp bao cả gan lành). **35.5% lát dương có ≥2 ổ** → xử lý đúng multi-focal (đa ổ) là quan trọng, đụng thẳng vào đóng góp "multi-region" của paper.
- **Augment hợp CT gan** (biến đổi ảnh + box cùng lúc): dịch/xoay nhẹ ±12°/scale — **KHÔNG lật, KHÔNG xoay 90°** (gan có hướng giải phẫu). Chỉ augment ở train.
- **Data v3:** 1211 mẫu (558 dương / 653 âm), **split theo bệnh nhân** (không rò rỉ).
- *Thủ sẵn câu hỏi hội đồng:* ca **đa ổ khó hơn** ca đơn ổ (recall thường thấp hơn) — đây là giới hạn đã biết, phân tích chi tiết ở phần lỗi (Slide 10).
- 🖼️ `../code/data/data_liver/images/liver_002_pos_z457.png` + `../code/data/data_liver/images/liver_002_neg_z389.png` — *một cặp lát CÓ u / KHÔNG u của cùng bệnh nhân*
- *Câu nói:* "Paper chỉ dùng lát trung tâm, không có ca âm. Chúng em thêm cả hai — nhưng 5 lát của một người thì tương quan cao, nên đếm bằng bệnh nhân, không đếm bằng lát."

---

### Slide 7 — Cải tiến (3): huấn luyện + một thí nghiệm thất bại

- **LoRA trên LLM** (Low-Rank Adaptation — chèn ma trận nhỏ, giữ nguyên trọng số gốc) **+ full-finetune Vision tower** (fp32, LR 1e-5); 2 nhóm LR (LoRA 2e-4 / vision 1e-5) để không nổ số.
- **Loss:** cross-entropy tiêu chuẩn.
- **Bài học thất bại (v4 — BCE-head):** thêm 1 **nhánh loss BCE** (Binary Cross-Entropy — loss phân loại nhị phân, dạy quyết định "vẽ/không vẽ" box) để tăng recall → localization **SẬP** (IoU 0.32→0.071, **recall@0.25** — tỉ lệ bắt được u tính là đúng nếu IoU ≥ 0.25 — 54%→10%). Hai nguyên nhân chồng nhau: (1) **λ_BCE** (trọng số cân giữa loss BCE và loss toạ độ) **quá lớn lấn át loss toạ độ**; (2) **bug nạp lại checkpoint** (bản lưu trọng số model — lệch key LoRA giữa version peft → trọng số rơi vào `missing_keys` im lặng). → bài học: cân λ cẩn thận + **hard-fail khi thiếu key**.
- *Câu nói:* "Chúng em kể cả cái hỏng: v4 vừa có rủi ro cân loss vừa có lỗi checkpoint nên bị loại. Bài học là phải kiểm soát cả loss lẫn quy trình load/merge."

---

### Slide 8 — Cải tiến (4): ĐÁNH GIÁ chặt hơn *(đóng góp mạnh nhất)*

- **Per-patient + bootstrap CI** (khoảng tin cậy bằng cách lấy mẫu lại nhiều lần để ước lượng độ dao động) thay per-image → sửa pseudoreplication; cỡ mẫu thật **~25 bệnh nhân dương** → CI rộng, **nói thẳng**.
- **Tách "PHÁT HIỆN" khỏi "ĐỊNH VỊ":**
  - *Detection* = có box **chồng GT** (IoU>0); vẽ box không chạm u = **không** tính bắt được.
  - *False-positive* (ca âm) = lát không u nhưng model vẽ box.
  - *Localization* = box khít đến đâu → báo **IoU riêng**.
  - → model có thể **phát hiện tốt** nhưng **định vị trung bình** — tách mới thấy.
- **Selective prediction** (biết khi nào không nên tin): 2 tín hiệu **miễn phí** từ chính lần sinh — **logprob token toạ độ** (độ chắc chắn của model khi sinh ra con số toạ độ) + **nhất quán không gian** (sinh nhiều lần, box có trùng nhau không). → đường **risk–coverage** (đánh đổi: càng trả lời nhiều ca thì càng dễ sai) + ngưỡng **conformal** (cách đặt ngưỡng có bảo đảm thống kê về tỉ lệ sai) → **triage** (gắn cờ cho bác sĩ xem lại).
- ⚠️ *CAVEAT conformal:* ở đây là **minh hoạ quy trình (proof-of-concept)** — với n nhỏ (~25 ca dương), bảo đảm thống kê còn rất lỏng, cần calibration set (tập ca riêng dùng để dò ngưỡng, tách khỏi tập test) lớn hơn tách riêng để có ý nghĩa thực.
- 🖼️ `../code/eval/risk_coverage.png` — *đường risk–coverage 3 tín hiệu (logprob/nhất quán không gian/self-confidence): coverage giảm thì selective mean-IoU tăng — cơ sở cho triage.*
- **Bắc cầu sang Phần C:** 4 cải tiến này cho ra **3 nhóm kết quả — PHÁT HIỆN (Slide 9), ĐỊNH VỊ (Slide 10), KHÔNG QUÊN (Slide 11)**; mỗi cái đo bằng đúng khung đánh giá vừa dựng.
- *Câu nói:* "Đóng góp lớn nhất ở phương pháp đánh giá: có/không có u, khoanh ở đâu, và khi nào nên đưa bác sĩ xem lại — tất cả rút thẳng từ lần sinh, không thêm mạng phụ. Conformal ở đây là chứng minh quy trình, chưa phải bảo đảm chặt vì n còn nhỏ."

---

## PHẦN C — KẾT QUẢ

---

### Slide 9 — Kết quả: Phát hiện (có/không u) — TỐT

> Model = **v3** (bản fine-tune tốt). **Cỡ mẫu: n=25 bệnh nhân dương / 2 âm** — mọi số detection dưới đây gắn với cỡ mẫu này.

| Chỉ số | Zero-shot | Sau fine-tune |
|---|---|---|
| **Detection F1** (bệnh nhân) | 0.33 | **0.89** |
| **Sensitivity** (bắt u) | 20% | **80%** (20/25) |
| **False-positive** | — | **lát 1.5%** (2/135) **· bệnh nhân 7.4%** (2/27) |
| **Specificity/Precision** (bệnh nhân, ca âm) | — | **100%** (2/2 ca âm — n=2, KHÔNG phải specificity lâm sàng) |

- *Zero-shot (chưa fine-tune — model gốc chưa học task này). **F1** (điểm cân bằng giữa độ bắt đúng và độ không báo nhầm, 0–1); **Precision** (tỉ lệ box/ca báo ra là đúng); **Specificity** (tỉ lệ ca âm được nhận đúng là âm).*
- Cấp lát: Sensitivity 59% · Precision 97% · **F1 0.74**. ⚠️ FP: lát **1.5%** (2/135) NHƯNG bệnh nhân **7.4%** (2/27) — n rất nhỏ (chỉ 2/27), **đừng đọc như tỉ lệ ổn định**; không diễn giải 2.2%→1.5% như "giảm FP có ý nghĩa" (n lát tương quan).
- Zero-shot gần như luôn trả "No liver tumor is found." → fine-tune **dạy được task từ số 0**.
- ⚠️ **CAVEAT (bắt buộc):** Specificity/Precision cấp bệnh nhân = **100% nhưng tựa trên chỉ 2 bệnh nhân hoàn toàn không-u** → **rất yếu thống kê**, và là **phân biệt lát nội-bệnh-nhân, KHÔNG phải specificity lâm sàng**.
- 🖼️ `../code/detect_before_after.png` — *grouped bar zero-shot vs fine-tune (F1 0.33→0.89 · Sens 20%→80% · FP 2.2%→1.5%; ↓ FP thấp hơn = tốt hơn).*
- *Câu nói:* "Bắt đúng 20/25 bệnh nhân, FP thấp. Nhưng 100% kia đứng trên 2 người — chúng em không dùng nó để claim specificity lâm sàng."

---

### Slide 10 — Kết quả: Định vị + vì sao model SÓT u

- **Localization TRUNG BÌNH (đã tách, không giấu):** per-patient penalized **pIoU ≈ 0.27** (penalized IoU — IoU có phạt khi vẽ dư/thiếu box), **CI95** (khoảng tin cậy 95%) **[0.19, 0.36]**, n=25. recall@IoU>0.25 ≈ **54%**; theo cỡ tăng đều: nhỏ 35% → vừa 54% → lớn 74%.
- **Vì sao SÓT — KHÔNG chỉ do u nhỏ (phân biệt rõ HAI mức đo):** xét **TỪNG ổ u** thì ổ sót nhỏ hơn ~2 lần (median area 0.087% vs 0.193%) VÀ tương phản kém hơn (**contrast_z** — độ tương phản chuẩn hoá, u nổi bật bao nhiêu so với mô xung quanh — 0.39 vs 0.48); nhưng xét **THEO BỆNH NHÂN (u lớn nhất)** thì gần bằng nhau (1.28% vs 1.32%) — nên kích thước **KHÔNG phải yếu tố duy nhất**. Trong 83 tổn thương sót hoàn toàn có cả nhỏ/vừa/lớn. **Low-contrast/isointense** (đồng tỉ trọng — u sáng gần bằng gan lành nên rất khó phân biệt trên phim) **mới là chìa khoá phân biệt được cả u to** (bằng chứng: pid116 u 5.63% vẫn sót). Thông điệp thống nhất: **nhỏ + tương phản thấp cùng góp; tương phản là yếu tố phân biệt được cả u lớn.**
- Nghi cửa sổ CT rộng (**WL40/WW400** — cửa sổ hiển thị CT: mức 40, độ rộng 400 HU) làm ca isointense khó → **cửa sổ gan hẹp** là hướng thử tiếp (→ Future).
- 🖼️ `../code/pid116_contrast.png` — *ca pid116: u chiếm 5.63% diện tích vẫn khó thấy vì isointense*
- 🖼️ `../code/missed_patients_v3.png` — *tổng quan các ca bị sót*
- 🖼️ `../code/missed_zoom_v3.png` — *zoom cận cảnh vùng u bị sót (u nhỏ/tương phản thấp) — củng cố luận điểm "sót không chỉ do kích thước"*
- ⚠️ CAVEAT: "kích thước" = **diện tích box 2D (proxy)**, không phải thể tích thật; contrast là proxy thô từ ảnh đã windowed.
- *Câu nói:* "Định vị mới trung bình, chúng em không giấu. Ca sót nghiêng về u nhỏ VÀ tương phản thấp — cả hai cùng góp; không chỉ do kích thước, nhưng kích thước vẫn là yếu tố mạnh (median nhỏ hơn ~2 lần). Phân tích lỗi chỉ đường cải thiện dữ liệu/cửa sổ ảnh."

---

### Slide 11 — Kết quả: Fine-tune KHÔNG làm "quên"

- **Lo ngại:** fine-tune hẹp (chỉ khoanh u gan) có làm mất khả năng nói chuyện/theo lệnh? → kiểm bằng **hội thoại đa lượt** (lượt 1 = prompt DETECT như train; lượt sau = yêu cầu tự do), lưu JSON làm bằng chứng.

| Lượt | Yêu cầu | Model trả lời |
|---|---|---|
| 1 | prompt DETECT | `<ref>liver tumor</ref><box>[[438,211,469,241],…]</box>` → vẽ nhiều box |
| 5 | *JSON đúng 3 key* | `{"lesion_seen":"Yes","confidence_caveat":"…","next_step":"…"}` |
| 7 | *thơ 2 câu về mưa* | "Mưa rơi tí tách trên mái hiên, / Gột rửa phố phường, lòng thêm dịu êm." |
| 8 | *17 × 23 = ?* | **391** ✓ |

- **Nhất quán đa lượt:** ca CÓ u → "lesion_seen: Yes"; ca âm → "No liver tumor". Model phản ánh đúng kết quả nó vừa detect.
- **Vì sao giữ được:** **LoRA giữ nguyên trọng số gốc** → thêm kỹ năng mà không xoá kỹ năng cũ. *Điểm cộng ngoài dự kiến.*
- ⚠️ *Đây là kiểm tra **ĐỊNH TÍNH** (một số ca hội thoại), **CHƯA phải benchmark tổng quát có số** (MMLU/task cũ) — chỉ đủ để nói LoRA không phá hỏng rõ rệt, không đủ để tuyên bố bảo toàn hoàn toàn năng lực.*
- 🖼️ `../code/chat_test_multiturn.png` — *bảng hội thoại đa lượt (lượt 1 detect + 5 JSON + 7 thơ + 8 toán) render từ dữ liệu thật `chat_test_gemma4_v3_0703_*.json`.*
- **Bắc cầu sang Phần D:** vậy là **nhỏ hơn mà vẫn khoanh được u VÀ không mất năng lực tổng quát** — giờ đặt cạnh gốc cho công bằng (Slide 12).
- *Câu nói:* "Model vừa khoanh được u, vừa theo lệnh chính xác, giải thích song ngữ, làm thơ, tính 17×23=391. Nhờ LoRA giữ nguyên trọng số gốc — gợi ý LoRA không phá hỏng RÕ RỆT năng lực cũ (kiểm định tính, chưa đo benchmark như MMLU nên chưa dám nói bảo toàn hoàn toàn). Giờ ta đặt nó cạnh paper gốc cho công bằng."

---

## PHẦN D — SO SÁNH & TƯƠNG LAI

---

### Slide 12 — So sánh với paper gốc

> Nguyên tắc: **KHÔNG so số trực tiếp** (khác data/task/metric/scale). So **tính chất** + **thứ mỗi bên có/không**.

| Khía cạnh | MedRegA gốc | Của nhóm |
|---|---|---|
| Quy mô | ~40B, 16× H800 | **~8B, 1×A100** |
| Vào 3D | 1 lát trung tâm | **đa lát + ca âm** |
| Nhãn vùng | box lỏng (không cần khít) | **box khít từng ổ (multi-box)** |
| Đơn vị đánh giá | per-image | **per-patient + CI** |
| Detect vs Localize | gộp | **tách riêng** |
| Ca âm / FP | không | **có** |
| Bất định / triage | không | **selective prediction** |
| Grounded report | **có** | chưa (→ Future) |

- Định vị: IoU 0.23 của họ (Algorithm 1, Appendix D) tính **MATCHED-only — KHÔNG phạt miss** (miss do Region F1 gánh), trên đích chủ yếu **cấu trúc LỚN + box LỎNG** (paper tự nói "không cần khít"). **Cùng chuẩn matched: mình ~0.32 vs 0.23.** *pIoU 0.27 của mình CÓ PHẠT nên khắt khe hơn. Vẫn khác dataset → chỉ tham khảo, KHÔNG tuyên bố "mình hơn". LƯU Ý: MedRegA cũng dùng multi-box (Figure 8) — KHÔNG phải "box gộp 1 khối".*
- *pIoU của nhóm **ĐÃ TRỪ điểm** khi thiếu/dư box nên **khắt khe hơn** IoU thường của paper; nếu tính IoU cùng kiểu (matched-pair — ghép từng box dự đoán với box thật gần nhất rồi mới tính IoU, bỏ qua phần thừa/thiếu, nên lạc quan hơn pIoU) nhóm ~**0.32** — nhưng vẫn KHÔNG so trực tiếp vì khác data. Nói cả hai để không bị bắt bẻ "sao không đưa 0.32" lẫn "pIoU phạt thì bất lợi cho ai".* **KHÔNG dùng 0.32 để nói hơn 0.23 — hai bên khác dataset/metric, đặt cạnh chỉ để thấy CÙNG khoảng định vị thô.**
- **Đóng góp thật:** không phải điểm số — mà là **khung đánh giá trung thực + độ tin cậy** bổ sung cho benchmark của paper.
- *Câu nói:* "Chúng em không claim đánh bại MedRegA. Đóng góp là biến benchmark định vị thành workflow đánh giá gần lâm sàng: có/không u, khoanh ở đâu, khi nào không nên tin."

---

### Slide 13a — Hướng tương lai (1): ảnh giàu hơn + đáng tin hơn *(①②③⑤)*

> Nhãn nguồn: **[ĐO ĐƯỢC]** = nối thẳng số Slide 9–10; **[PHẠM VI/GIẢ ĐỊNH]** = suy từ thiết kế, CHƯA đo trực tiếp.

| # | Hạn chế (nguồn) | → Hướng đi tiếp | Chi phí |
|---|---|---|---|
| ① | Sót u **isointense**, cửa sổ rộng — **[ĐO ĐƯỢC, Slide 10]** | **Multi-window** (cửa sổ gan hẹp + rộng + tối vào 3 kênh) | 🟢 rất thấp |
| ② | **3D→2D mất thông tin**, u lẫn mạch máu — **[PHẠM VI/GIẢ ĐỊNH]** | **2.5D stack** (ghép 3 lát z−1/z/z+1 thành 3 kênh RGB) | 🟢 thấp |
| ③ | *(gốc rễ)* LiTS **đơn pha** — **[PHẠM VI/GIẢ ĐỊNH]** | **CT đa pha** — u tách mạch bằng động học ngấm–thải; đơn pha là **trần của DỮ LIỆU, không phải model** | 🔴 cần data |
| ⑤ | **2 ca âm, 1 dataset** — **[ĐO ĐƯỢC, Slide 9/12]** | **External validation** (IRCADb/MSD) + thêm ca âm + **FROC** + **calibration** | 🟡 inference |

- *Footnote thuật ngữ:* **External validation** = kiểm chứng trên bộ dữ liệu KHÁC (IRCADb/MSD là các bộ CT gan công khai) để chắc không overfit; **FROC** = đường cong đánh giá phát hiện đa tổn thương theo số FP mỗi ảnh; **calibration** = hiệu chỉnh độ tự tin cho khớp xác suất đúng thật.
- *Câu nói:* "Mạch 1 — làm ảnh giàu hơn (multi-window, 2.5D, đa pha) và kết quả đáng tin hơn (external validation, thêm ca âm). Hướng ①⑤ nối thẳng số Kết quả nên ghi [ĐO ĐƯỢC]; ②③ suy từ thiết kế nên ghi rõ CHƯA đo trực tiếp."

---

### Slide 13b — Hướng tương lai (2): nói-có-dẫn-chứng, generalist + bài học loss *(④⑥⑦⑧)*

> Nhãn nguồn: **[ĐO ĐƯỢC]** = nối thẳng số Slide 10; **[THÍ NGHIỆM HỎNG]** = từ Slide 7; **[PHẠM VI/GIẢ ĐỊNH]** = suy từ thiết kế.

| # | Hạn chế (nguồn) | → Hướng đi tiếp | Chi phí |
|---|---|---|---|
| ④ | **pIoU chỉ 0.27** (box thô) — **[ĐO ĐƯỢC, Slide 10]** | **MedSAM khoanh khít + polygon-as-token** (tận dụng mask LiTS) | 🟡 vừa |
| ⑥ | **Chỉ detect** (chưa có report) — **[PHẠM VI]** | **Grounded report** (mỗi câu neo 1 box) | 🟡 vừa |
| ⑦ | **Chỉ u gan** — **[PHẠM VI/GIẢ ĐỊNH]** | **Generalist đa cơ quan** (công thức region-centric không phụ thuộc cơ quan) | 🔴 dài hạn |
| ⑧ | **BCE-head fail** — **[THÍ NGHIỆM HỎNG, Slide 7]** | **Cân bằng loss thông minh** (uncertainty weighting + GIoU qua soft-argmax; bật phụ-loss muộn) | 🟢 thấp |

- *Footnote thuật ngữ:* **MedSAM** = mô hình phân vùng ảnh y tế tạo mask khít; **polygon-as-token** = viết đường viền u thành chuỗi toạ độ như chữ, thay box thô; **uncertainty weighting** = tự học trọng số từng loss theo độ bất định; **GIoU** (Generalized IoU) = IoU tổng quát, phạt được cả khi 2 box không chồng nhau; **soft-argmax** = cách lấy toạ độ khả vi để huấn luyện được bằng gradient.
- *Câu nói:* "Mạch 2 — từ chỉ-chỗ tiến tới nói-có-dẫn-chứng (khoanh khít hơn, báo cáo neo box) rồi generalist đa cơ quan. Và kể cả thí nghiệm hỏng ⑧ BCE-head cũng đẻ ra một hướng: cân loss thông minh hơn. Tên tool tương lai (MedSAM/FROC/IRCADb) cần tự xác minh nguồn."

---

### Slide 14 — Kết luận

- **Chứng minh một cơ chế:** region-centric (khoanh-rồi-đọc) **khả thi ở quy mô ~8B, 1 GPU**.
- **Đóng góp cốt lõi (v3):** Detection F1 **0.89** · pIoU **0.27** · FP **1.5%** — nhưng giá trị nằm ở **khung đánh giá trung thực + selective prediction**, không phải điểm số.
- **Trung thực:** PoC trên 1 dataset/1 task; n nhỏ, CI rộng (2 ca âm — xem caveat đầy đủ ở Slide 9); không tuyên bố hệ thống lâm sàng.
- **Bản đồ mở rộng:** ảnh giàu hơn (multi-window, 2.5D) → đáng tin hơn (external validation, calibration) → nói-có-dẫn-chứng & generalist.
- *Câu nói chốt:* "Chúng em không hứa đã tới đích — chỉ ra con đường và nói rõ chỗ nào còn dốc."

---

*Nguồn số liệu: `eval_baseline.ipynb` + deck [trinh_bay_cai_tien_2026-06-30.md](trinh_bay_cai_tien_2026-06-30.md). Hình paper (Slide 1–3) lấy từ slide PDF của nhóm — cần chèn tay. Tên tool tương lai (MedSAM/FROC/IRCADb) cần tự xác minh nguồn.*
