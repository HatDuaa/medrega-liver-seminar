# Cải tiến trên MedRegA — Fine-tune Gemma 4 E4B cho phát hiện u gan (LiTS)

> Bài trình bày seminar · Học sâu · 2026-06-30
> Chủ đề: đi SÂU trên một mô hình NHỎ (một task), so với paper gốc là mô hình 40B tổng quát.
> Nguyên tắc xuyên suốt: TRUNG THỰC — không thổi phồng; mọi caveat đặt NGAY trên slide có số liệu.

---

## Slide 1 — Bối cảnh: MedRegA gốc (ICLR 2025)

- **Ý tưởng chính:** MLLM y khoa "region-centric" — bắt chước bác sĩ: nhìn toàn ảnh rồi khoanh vùng cụ thể. Sinh báo cáo + định vị bằng **bounding box viết dưới dạng text**: `<ref>đối tượng</ref><box>[x1,y1,x2,y2]</box>`, toạ độ chuẩn hoá về `[0,1000)`.
- **Quy mô cực lớn (~40B):** base là InternVL 1.2 = InternViT-6B (vision) + Nous-Hermes-2-Yi-34B (LLM). Là generalist **song ngữ** (Anh–Trung) trên **8 modality**.
- **3 task region-centric:** (1) Region→Text (đọc tên vùng trong box), (2) **Text→Region (phát hiện/định vị)**, (3) Grounded Report Generation (báo cáo gắn box).
- **Huấn luyện 2 giai đoạn:** (1) alignment — chỉ chỉnh connector; (2) instruction tuning — chỉnh LLM. **Loss = CE ngôn ngữ thuần** (dự đoán token kế tiếp), không có loss hình học riêng. Dữ liệu: MedRegInstruct 550K cặp region–text + 240K report gắn box.
- **Ảnh 3D:** chỉ lấy **1 lát trung tâm** làm input 2D.
- *Câu nói khi trình bày:* "MedRegA là mô hình khổng lồ, biết-tuốt, nhiều modality. Chúng em chọn hướng ngược lại: một mô hình nhỏ, một bệnh, nhưng đào sâu về phương pháp đánh giá và độ tin cậy."

---

## Slide 2 — Khoảng trống của paper (chỗ để mình lấp)

- **Chưa tập trung vào bất định / abstention cho task detection.** Model luôn cố vẽ box, chưa có cơ chế rõ ràng để nói "khi nào nên im lặng" hay "khi nào nên đưa cho người kiểm".
- **Không có ca ÂM (không u).** Không đo được model có bịa box trên ảnh không bệnh hay không (false positive).
- **Chỉ thống kê per-IMAGE (micro).** Nhiều lát của cùng một bệnh nhân bị tính như các mẫu độc lập → **pseudoreplication** (đơn vị thống kê sai).
- **Metric vùng chưa được đặt trong workflow lâm sàng.** MedRegA đã có region-aligned eval (matching, IoU, precision/recall/F1), nhưng chủ yếu vẫn là benchmark theo ảnh. Khoảng trống của mình là tách rõ câu hỏi lâm sàng: có bắt được u không, có bịa box trên ca âm không, và báo cáo theo bệnh nhân.
- **Chưa có hiệu chuẩn (calibration) / selective prediction cho triage.** Paper chưa hỏi: dự đoán nào nên đưa bác sĩ xem lại trước?
- *Câu nói khi trình bày:* "Paper mạnh về quy mô và benchmark region-grounding. Chúng em không nói paper thiếu metric vùng; chúng em bổ sung lớp đánh giá gần lâm sàng hơn: ca âm, FP, triage, và báo cáo trung thực trên từng bệnh nhân."

---

## Slide 3 — Bài toán của mình

- **Backbone:** **Gemma 4 E4B** (~8B tham số) — nhỏ hơn rõ so với MedRegA ~40B. Mô hình mở, chạy được trên 1×A100.
- **Một task duy nhất:** Text→Region detection cho **u gan trên CT** (dataset **LiTS**, 131 ca).
- **Triết lý:** đổi "rộng" lấy "sâu" — thay vì phủ 8 modality, ta đào sâu **kỹ thuật dữ liệu + phương pháp đánh giá + độ tin cậy** trên đúng một bài toán.
- **Khả thi hoá trên mô hình nhỏ:** bf16; **LoRA trên LLM** (nhắm đúng `*.linear` bên trong `Gemma4ClippableLinear`) + **fine-tune TOÀN BỘ vision tower ở fp32, LR thấp (1e-5)** với 2 nhóm LR (LoRA 2e-4 / vision 1e-5) để không nổ số.
- **Kết quả nền tảng:** tái tạo được khả năng định vị vùng trên mô hình ~8B — **mở vision tower là bước tạo khác biệt** (đóng băng vision thì IoU ≈ 0.015, gần như không định vị được).
- *Câu nói khi trình bày:* "Đóng góp đầu tiên: chứng minh khả thi. Reproduce được năng lực region-detection trên mô hình nhỏ hơn nhiều, chỉ 1 GPU."

---

## Slide 4 — Cải tiến DỮ LIỆU (1): đa lát + ca âm

- **Đa lát thay vì chỉ lát trung tâm (khác paper):** mỗi bệnh nhân lấy **2 lát u lớn nhất + 3 lát ngẫu nhiên** → phủ nhiều mức cắt theo trục z, nhiều kích thước/diện mạo u hơn, và có thêm lát không-u.
- **Thêm ca ÂM (không u):** đưa vào các lát không có u để model học "khi nào KHÔNG vẽ box" — điều paper hoàn toàn thiếu.
- **Data v3:** 1211 mẫu (558 dương / 653 âm), split **theo bệnh nhân** (không trùng bệnh nhân giữa train/cal/test → không rò rỉ dữ liệu).
- **Giới hạn tự nhận (đặt ngay đây):** lấy "quanh u lớn nhất" khiến test thiên về u to/dễ; đa dạng vị trí u chủ yếu đến từ **số bệnh nhân**, không phải từ số lát (các lát kề của một bệnh nhân gần trùng nhau). → đây là lý do phải augment (slide 5) và phải báo cáo per-patient (slide 6).
- *Câu nói khi trình bày:* "Paper chỉ dùng lát trung tâm và không có ca âm. Chúng em thêm cả hai — nhưng cũng thẳng thắn: 5 lát của một người thì tương quan cao, nên chúng em đếm bằng bệnh nhân, không đếm bằng lát."

---

## Slide 5 — Cải tiến DỮ LIỆU (2): multi-box + augmentation

- **Multi-box bằng connected components:** dùng `scipy.ndimage.label` tách từng ổ tổn thương → **1 box/ổ**, lọc ổ quá nhỏ (<30px). Sửa lỗi nhãn đa ổ (trước đây một box min/max bao cả gan lành ở giữa = nhãn rác).
  - **35.5% lát dương có ≥2 ổ** → xử lý đúng multi-focal là quan trọng, và trực tiếp đụng vào đóng góp "multi-region" của paper.
- **Augmentation hợp CT gan (biến đổi ẢNH + BOX cùng lúc):** dịch (±18%) / xoay **nhẹ ±12°** / scale ±10% / chỉnh sáng nhẹ.
  - **KHÔNG lật (flip) và KHÔNG xoay 90°:** CT gan có hướng giải phẫu chuẩn (gan bên phải, lách bên trái) — lật/xoay lớn là phi lâm sàng và phá cấu trúc.
  - Mục đích: **phá "prior vị trí"** — ép model nhìn ảnh để định vị thật, thay vì học thuộc vị trí u phổ biến.
  - Augment **chỉ ở train**; validation/test giữ ảnh gốc.
- *Câu nói khi trình bày:* "Đây là kỹ thuật dữ liệu 'đúng miền' — augment thứ hợp lý với CT gan, và tách đúng từng khối u thay vì gộp thô."

---

## Slide 6 — Cải tiến ĐÁNH GIÁ (1): per-patient + CI, và tách detection/localization

- **Per-patient thay per-image (sửa pseudoreplication):** gộp các lát cùng bệnh nhân, báo cáo cấp **bệnh nhân** kèm **bootstrap CI**. Cỡ mẫu thật = **~25 bệnh nhân dương**, không phải hàng trăm lát → **CI rộng, và ta nói thẳng điều đó**.
- **Tách "PHÁT HIỆN" khỏi "ĐỊNH VỊ" theo góc nhìn lâm sàng:**
  - **Detection trên ca dương** = có ít nhất một box **chồng lên GT** (IoU > 0; IoU là phần giao giữa box đoán và box thật chia cho phần hợp). Vẽ box nhưng không chạm u thì **không** tính là bắt được u.
  - **False positive trên ca âm** = lát thật sự không có u nhưng model vẽ bất kỳ box nào.
  - **Localization** = box khít đến đâu → báo **IoU** RIÊNG.
  - Ý nghĩa: model có thể **phát hiện tốt** nhưng **định vị chỉ trung bình** — phải tách mới thấy, không được giấu trong một con số.
- **IoU "phạt thiếu box" (penalized):** chia cho `max(#gt, #pred)` để phạt cả box sót lẫn box thừa; báo song song với IoU "chỉ tính cặp ghép" (Hungarian, lạc quan — chỉ để tham chiếu).
- *Câu nói khi trình bày:* "Đóng góp mạnh nhất của chúng em là ở phương pháp đánh giá. Từ metric vùng của paper, chúng em tách ra các câu hỏi gần lâm sàng hơn: model bắt được bệnh nhân/lát có u không, có bịa u trên lát âm không, và bắt rồi thì khoanh có khít không."

---

## Slide 7 — Cải tiến ĐÁNH GIÁ (2): metric cho ca ÂM (false positive / abstain)

- **Đo trực tiếp năng lực "im lặng đúng lúc"** — nửa còn thiếu của paper:
  - **False-positive rate:** tỉ lệ lát âm mà model bịa box.
  - **Abstain đúng:** tỉ lệ lát âm model im lặng đúng.
- **Confusion matrix có-u / không-u** ở CẢ hai cấp (lát và bệnh nhân).
- **Caveat quan trọng (đặt ngay đây):** trong test chỉ có **2 bệnh nhân HOÀN TOÀN không u** (pid 38, 119). Đa số "lát âm" là lát không-u **lấy từ chính bệnh nhân CÓ u** → đây là "**phân biệt lát trong cùng bệnh nhân**", **KHÔNG phải specificity lâm sàng** (người khoẻ vs người bệnh). Do đó "Spec 100%" thực chất tựa trên n=2 → **yếu về mặt thống kê**, phải nói rõ.
- *Câu nói khi trình bày:* "Chúng em đo được cả 'biết vẽ' lẫn 'biết im'. Nhưng specificity ở đây là phân biệt lát nội-bệnh-nhân, không phải sàng lọc người khoẻ — con số 100% đứng trên n=2, chúng em không giấu."

---

## Slide 8 — Đóng góp MỚI (1): Selective prediction — độ tin cậy từng dự đoán

- **MedRegA chưa tập trung vào bất định/triage cho task Text→Region.** Chúng em bổ sung một nhánh selective prediction hậu nghiệm cho bài toán u gan; đây là proof-of-concept, **không phải thuật toán selective prediction mới**.
- **Hai tín hiệu độ tin cậy, đều "miễn phí" từ cùng lần sinh:**
  1. **Log-prob của token toạ độ** — model tự tin đến đâu khi in ra các con số của box.
  2. **Nhất quán không gian (spatial consistency):** sinh nhiều lần có sampling (temp=0.7), đo các box có trùng nhau không (set-IoU giữa các lần). Box ổn định = đáng tin.
- **Cách vận hành:** mỗi ảnh sinh N_PRED=3 lần — lần 1 **greedy** = đáp án chính (kèm log-prob); lần 2–3 sampled (để đo nhất quán). JSON lưu **toàn bộ token + logprob raw** → mọi tín hiệu tính LẠI sau, đổi công thức không cần chạy lại model.
- **Phát hiện:** trên v3, **log-prob (token toạ độ) là tín hiệu mạnh nhất** (Spearman với độ đúng ≈ **+0.86** trên tập calibration).
- *Câu nói khi trình bày:* "Chúng em không thêm mạng phụ nào — độ tin cậy rút thẳng từ chính lần sinh box: model tự tin cỡ nào, và nó có nói y như vậy khi hỏi lại nhiều lần không."

---

## Slide 9 — Đóng góp MỚI (2): risk–coverage + conformal → khung TRIAGE

- **Đường risk–coverage:** sắp xếp dự đoán theo độ tin cậy; bỏ dần các ca kém tin nhất (giảm coverage) → chất lượng phần còn lại (selective-IoU) **tăng lên** → chứng minh tín hiệu tin cậy thật sự xếp hạng được ca đúng/sai.
- **Ngưỡng conformal:** chọn ngưỡng trên **tập calibration**, báo cáo kết quả trên **tập test** (không nhìn trộm test).
- **Đóng khung là TRIAGE, không phải "im lặng âm thầm":** ca độ tin cậy thấp được **gắn cờ để bác sĩ xem lại**, chứ không phải model tự ý bỏ. Đây là cách dùng đúng của bất định trong lâm sàng.
- **Caveat (đặt ngay đây):** calibration chỉ ~13 bệnh nhân → đây là **proof-of-concept**, cần tập lớn hơn để khẳng định. Trình bày như "hướng đi + bằng chứng sơ bộ", không phải "đã giải quyết".
- *Câu nói khi trình bày:* "Ý tưởng: đưa những ca model không chắc cho người xem lại. Số liệu ủng hộ hướng này, nhưng chúng em nói rõ n nhỏ — đây là PoC, không phải kết luận cuối."

---

## Slide 10 — KẾT QUẢ: Detection (nhận biết có/không u) — TỐT

> Model = **v3** (bản fine-tune tốt, đã kiểm số khớp JSON eval).

- **Cấp BỆNH NHÂN:** **Sensitivity 80% (20/25)** · **F1 = 0.89**. **Spec/Prec 100% chỉ là số minh hoạ trên n=2 bệnh nhân hoàn toàn không-u**, không dùng làm kết luận mạnh.
- **Cấp LÁT:** Sensitivity 59% · Specificity ~99% · Precision 97% · **F1 = 0.74**.
- **False positive rất thấp:** **1.5% lát âm (2/135)** · **7.4% bệnh nhân (2/27)**. → model hiếm khi bịa u.
- **CAVEAT (bắt buộc trên slide):**
  - "Specificity 100% / Precision 100%" tựa trên **chỉ 2 bệnh nhân hoàn toàn không u** → **rất yếu về thống kê**; và là **phân biệt lát nội-bệnh-nhân, KHÔNG phải specificity lâm sàng**. Ở cấp lát vẫn có FP: **2/135 lát âm**; ở cấp bệnh nhân có lát âm: **2/27**.
  - Chỉ ~25 bệnh nhân dương → mọi con số đi kèm CI rộng.
- *Câu nói khi trình bày:* "Tin tốt: bắt đúng 20/25 bệnh nhân và FP thấp. Nhưng 100% kia đứng trên 2 người — chúng em không dùng nó để claim specificity lâm sàng."

---

## Slide 11 — KẾT QUẢ: Localization (khít đến đâu) + phân tích ca sót

- **Localization chỉ TRUNG BÌNH (đã tách, không giấu):**
  - **per-patient penalized mean-IoU ≈ 0.27**, CI95 ≈ **[0.19, 0.36]**, n=25. *(Đây là con số headline — KHÔNG dùng 0.32.)*
  - IoU cặp-ghép (lạc quan, chỉ để tham chiếu) ≈ 0.32.
  - recall@IoU>0.25 ≈ **54%** (cấp lát); recall theo cỡ tăng đều: nhỏ 35% → vừa 54% → lớn 74%.
- **PHÁT HIỆN QUAN TRỌNG — vì sao model SÓT u:** miss không chỉ là chuyện "u bé". Audit theo từng tổn thương cho thấy nhóm **no-overlap miss** nhỏ hơn nhóm bắt được (median area **0.087% vs 0.193%**) và cũng kém tương phản hơn (contrast_z **0.39 vs 0.48**).
  - Trong **83/206** tổn thương bị miss hoàn toàn, phân bố kích thước là **nhỏ:39 · vừa:28 · lớn:16**; khoảng **55/83 (66%)** thuộc nhóm image-hard (nhỏ hoặc tương phản thấp).
  - → **Low-contrast/isointense** là một nguyên nhân quan trọng, nhưng không phải nguyên nhân duy nhất; có cả u nhỏ, u vừa, và một số u lớn bị bỏ sót.
  - Nhiều khả năng **cửa sổ CT rộng (WL40/WW400)** làm ca isointense khó hơn; **cửa sổ gan hẹp** có thể là hướng thử tiếp theo.
- **CAVEAT:** "kích thước" u = **diện tích box 2D (proxy)**, không phải thể tích thật; chỉ số tương phản là **proxy thô** từ ảnh PNG đã windowed → dùng để soi xu hướng, không kết luận chắc.
- *Câu nói khi trình bày:* "Định vị mới ở mức trung bình, chúng em không giấu. Ca sót là hỗn hợp: nhiều u nhỏ, nhiều u tương phản thấp, và vẫn có vài u lớn khó nhìn — nên phân tích lỗi giúp biết nên cải thiện dữ liệu/cửa sổ ảnh hay model."

---

## Slide 12 — Bài học từ một thí nghiệm THẤT BẠI (BCE-head)

- **Ý định (v4):** thêm một **loss BCE ở đầu quyết định "vẽ/không vẽ"** để tăng recall (model v3 hơi lười detect trên u nhỏ đơn lẻ).
- **Điều xảy ra:** so v3, localization **SẬP**: mean-IoU 0.32 → 0.071; recall@0.25 54% → 10%; FP tăng vọt. Hành vi model gần như quay về base.
- **Chẩn đoán hậu kiểm:** thực ra có **HAI vấn đề chồng nhau**, và ta rút ra bài học từ cả hai:
  1. **Cân bằng loss:** λ_BCE quá lớn có nguy cơ **lấn át CE toạ độ** → hiểu rõ rằng thêm loss phụ phải cân λ cẩn thận (token-loss cho toạ độ rất dễ bị nhiễu).
  2. **Bug nạp lại checkpoint:** cú sập v4 không sạch để quy hết cho BCE-head, vì hậu kiểm phát hiện nguy cơ **nạp sai trọng số khi khôi phục** (lệch tên key LoRA giữa các version peft → trọng số đã-train rơi vào `missing_keys` im lặng → merge ra ~base). → bài học kỹ thuật: **ghim version, hard-fail khi thiếu key**, đừng chỉ assert `unexpected_keys==0`.
- **Vì sao vẫn kể:** cho thấy hiểu **loss balance** và **kỷ luật MLOps** — và cho thấy v3 là mốc báo cáo sạch hơn (v4 bị loại vì lỗi, không phải bị chọn lọc).
- *Câu nói khi trình bày:* "Chúng em kể cả cái hỏng, nhưng không quy chụp quá mức: v4 vừa có rủi ro cân loss, vừa có lỗi checkpoint/load nên bị loại khỏi kết quả chính. Bài học là phải kiểm soát cả loss lẫn quy trình load/merge."

---

## Slide 13 — Fine-tune KHÔNG làm "quên": vẫn là trợ lý y khoa tổng quát

- **Lo ngại:** fine-tune hẹp (chỉ dạy khoanh box u gan) có làm model mất khả năng nói chuyện / theo lệnh không? → **kiểm bằng hội thoại đa lượt**: lượt 1 = prompt DETECT (như train), các lượt sau = yêu cầu tự do; lưu JSON làm bằng chứng.
- **Bằng chứng — 1 ca đa ổ (model VỪA khoanh u VỪA trả lời):**

| Lượt | Yêu cầu | Model trả lời |
|---|---|---|
| 1 | prompt DETECT (như train) | `<ref>liver tumor</ref><box>[[438,211,469,241], ...]</box>` → vẽ nhiều box |
| 2 | *2 câu, không chẩn đoán* | "Several small, scattered lesions are visible throughout the liver tissue. These masses appear in various locations." (đúng 2 câu) |
| 4 | *tiếng Việt cho bệnh nhân, ≤60 từ* | "Bức ảnh này chỉ là một lát cắt nhỏ của gan. Chúng tôi thấy có một vài điểm bất thường nhỏ trên gan. Để kết luận chính xác, bác sĩ cần xem thêm nhiều ảnh khác..." |
| 5 | *JSON đúng 3 key, không thừa chữ* | `{"lesion_seen": "Yes", "confidence_caveat": "Single slice limitation...", "next_step": "Review full scan and patient history."}` |
| 7 | *thơ 2 câu tiếng Việt về mưa* | "Mưa rơi tí tách trên mái hiên, / Gột rửa phố phường, lòng thêm dịu êm." |
| 8 | *17 × 23 = ? (chỉ số)* | **391** ✓ |

- **Nhất quán đa lượt:** ca CÓ u → JSON `"lesion_seen": "Yes"` + "several lesions"; ca sót/âm → "No liver tumor". Model **phản ánh đúng kết quả nó vừa detect ở lượt 1**.
- **Vì sao giữ được:** dùng **LoRA** (giữ nguyên trọng số gốc, chỉ cộng delta nhỏ). Task detection **kích hoạt bởi prompt riêng**; câu hỏi khác → model dùng lại năng lực Gemma gốc → **thêm kỹ năng mà không mất trí nhớ**.
- *Câu nói khi trình bày:* "Lo ngại tự nhiên: fine-tune hẹp có làm model 'ngu' đi việc khác không? Model vừa khoanh được u, vừa theo lệnh chính xác (JSON đúng key, đếm câu), giải thích song ngữ cho bệnh nhân, làm thơ, và tính 17×23=391. Nhờ LoRA — thêm kỹ năng mà không quên. Đây là điểm cộng ngoài dự kiến."

---

## Slide 14 — Hạn chế (nói thẳng)

- **Cỡ mẫu nhỏ:** ~25 bệnh nhân dương, **chỉ 2** bệnh nhân hoàn toàn không u → mọi CI rộng; Spec/Prec 100% rất yếu về thống kê.
- **"Specificity" chưa phải specificity lâm sàng đầy đủ:** chủ yếu là phân biệt lát nội-bệnh-nhân, không phải sàng lọc người khoẻ vs người bệnh.
- **"Kích thước" u = proxy 2D** (diện tích box), không phải thể tích 3D; chỉ số tương phản là proxy thô.
- **Data thiên lệch:** lấy quanh u lớn nhất → test dễ hơn lâm sàng; đa dạng vị trí u chủ yếu do số bệnh nhân (ít).
- **Selective prediction là PoC:** calibration ~13 bệnh nhân — cần tập lớn hơn / k-fold theo bệnh nhân để khẳng định.
- **Một dataset, một task, một modality (CT gan):** chưa chứng minh tổng quát hoá.
- *Câu nói khi trình bày:* "Đây là pilot/PoC trên một dataset. Giá trị nằm ở phương pháp và tính trung thực, không phải ở việc tuyên bố một hệ thống lâm sàng đã sẵn sàng."

---

## Slide 15 — Kết luận + so sánh với paper

| Khía cạnh | MedRegA (paper gốc) | Công trình của mình |
|---|---|---|
| Quy mô | ~40B (InternViT-6B + Yi-34B), generalist 8 modality | ~8B Gemma 4 E4B, **1 task** (u gan CT), 1×A100 |
| Vào 3D | chỉ **lát trung tâm** | **đa lát** (2 u-lớn + 3 ngẫu nhiên) + **ca âm** |
| Nhãn vùng | box từ mask (đa ổ gộp thô) | **multi-box connected-components** (1 box/ổ), lọc nhiễu |
| Augmentation | không nêu | **augment hợp CT gan** (dịch/xoay nhẹ/scale, không flip) |
| Đơn vị đánh giá | **per-image** (pseudoreplication) | **per-patient + bootstrap CI** |
| Detect vs Localize | có metric định vị vùng, nhưng chưa đặt trong workflow lâm sàng | **tách**: overlap-detect/FP riêng, IoU riêng |
| Ca âm / FP | không có | **FP rate + abstain** (có caveat n=2) |
| Bất định | chưa tập trung vào triage cho Text→Region | **selective prediction hậu nghiệm**: logprob + spatial, risk–coverage, conformal → **triage** |
| Loss | CE ngôn ngữ thuần | CE (+ đã thử BCE-head, **báo cáo là bài học thất bại**) |
| Tinh thần | SOTA, phủ rộng | **trung thực, đi sâu, decompose "vì sao sai"** |

- **Kết quả cốt lõi (v3):** Detection F1 **0.89** (bệnh nhân) · Localization pIoU **0.27** · FP **1.5%** lát / **7.4%** bệnh nhân · ca sót thường liên quan **u nhỏ và/hoặc low-contrast/isointense**, không thể quy về một nguyên nhân duy nhất.
- **Đóng góp lớn nhất:** không phải điểm số, mà là **khung đánh giá trung thực + bất định** bổ sung cho benchmark region-grounding của paper.
- *Câu nói khi trình bày:* "Chúng em không claim đánh bại MedRegA về quy mô hay SOTA. Đóng góp chính là biến một benchmark định vị vùng thành workflow đánh giá gần lâm sàng hơn: có/không có u, khoanh ở đâu, khi nào không nên tin, và báo cáo trung thực theo bệnh nhân."
