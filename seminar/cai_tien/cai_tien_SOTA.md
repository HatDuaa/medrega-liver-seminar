# Hướng cải tiến MedRegA dựa trên SOTA 2024–2026 (sau bóc tách + phản biện)

> Kết quả từ quy trình đa tác nhân: bóc tách 5 thành phần MedRegA → khảo sát 8 hướng SOTA → tổng hợp 11 ý tưởng → phản biện khắt khe → còn **7 hướng sống**.
> **Ràng buộc cốt lõi:** đã loại mọi ý tưởng chỉ là hệ quả của việc nâng base lên Gemma 4 (vd mở khóa vision encoder, tăng độ phân giải, connector tốt hơn).

---

## Kết luận lớn

Quan sát của nhóm **đúng**: đổi sang Gemma 4 đã vá phần lớn điểm yếu **tầng base** (vision encoder, grounding, đa ngôn ngữ). Vì vậy đóng góp có giá trị bây giờ phải nằm ở **các tầng khác**: dữ liệu/nhãn, hàm mục tiêu, hình thức hóa tác vụ, khung đánh giá, độ tin cậy lâm sàng. Đây là chỗ MedRegA còn hổng thật và là chỗ nhóm seminar (1 GPU, QLoRA) đóng góp được — miễn khai báo rõ là **proof-of-concept cơ chế trên base nhỏ, không so kè bảng SOTA**.

> **Câu chốt:** Base đã khỏe — đóng góp của nhóm phải là dạy MedRegA **biết mình ĐÚNG tới đâu và SAI ở đâu**, chứ không phải làm nó "to" hơn.

---

## ✅ QUYẾT ĐỊNH ƯU TIÊN CỦA NHÓM

- **TRỤC CHÍNH (chốt làm):** Hướng **1 — Selective prediction / abstention mức box** ("dạy AI biết khi nào nên im lặng"). Đây là hướng đáng làm nhất: mới thật, khả thi (không train lại, 1 GPU), giá trị lâm sàng rõ.
- **LÀM SAU NẾU DƯ THỜI GIAN (phụ):**
  - Hướng **2 — Kiểm định nhân quả Regional CoT** ("AI có thật sự nhìn đúng vùng không").
  - Hướng **3 — Meta-evaluation metric** ("sửa lại thước chấm điểm cho công bằng").
- Hai hướng phụ này **bổ trợ** cho hướng chính (cung cấp thước đo đúng + bằng chứng), nhưng **không bắt buộc** cho phạm vi seminar.

---

## Bảng tổng 7 hướng sống

| # | Hướng | Tầng | Mới thật? | Khả thi seminar | Đề xuất |
|---|---|---|---|---|---|
| 4 ★ | **Selective prediction / conformal abstention mức box-finding** | độ tin cậy | ✅ **CÓ** (duy nhất) | Cao (post-hoc, không train lại) | keep |
| 1b | **Kiểm định nhân quả Regional CoT** (detect-then-reason) | task-formulation | một phần | Cao (thuần inference) | sharpen |
| 3 | **Meta-evaluation metric** cho bối cảnh song ngữ/đa phương thức | đánh giá | một phần | Cao (inference) | sharpen |
| 1a | Polygon-as-token thay box thô | task-formulation | thấp-TB | Cao (QLoRA) | sharpen |
| 2a | Phát hiện lỗi negation/assertion trong nhãn | dữ liệu | TB-thấp | Cao (NLP offline) | sharpen |
| 2b | Probe size-stratified + false-premise theo vùng | dữ liệu | thấp | Cao | bổ trợ |
| 5 | DPO grounded-preference chống hallucination | hàm mục tiêu | thấp | rủi ro nhất | sharpen/drop |

---

## TOP 3 đáng làm nhất

### Hạng 1 ★ — Selective prediction / conformal abstention (mức box & finding)
- **Vá gì:** MedRegA biểu diễn 1 `<ref>` ↔ danh sách box **cứng**, không có xác suất/uncertainty per-box, không "biết khi nào nên im lặng". Định vị bừa khi không chắc rất nguy hiểm lâm sàng.
- **Vì sao Gemma 4 không vá:** đây là tầng độ tin cậy/triển khai; model lớn hơn thường **calibration còn TỆ hơn** (overconfident).
- **Cách làm gọn (1 GPU, không train lại):**
  1. Chỉ làm selective prediction cho **Text-to-Region** + **Grounded Report**.
  2. **Thí nghiệm tiền đề bắt buộc:** chứng minh có tín hiệu tin cậy phân biệt được — so 3 nguồn: logprob của coordinate token / độ nhất quán không gian khi sample N=5 / self-verbalized confidence — đối chiếu với IoU thật. *Nếu tín hiệu yếu → báo cáo negative result (vẫn là đóng góp).*
  3. **Conformal theo modality** (Mondrian/class-conditional) để giữ coverage guarantee trên 8 phương thức.
  4. Metric mới: **cost-aware selective IoU/F1** (định vị bừa khi sai > im lặng) + đường risk-coverage.
- **Vì sao hạng 1:** là hướng **duy nhất** được chấm *mới thật*; khả thi nhất; giá trị lâm sàng trực tiếp, dễ kể ("model biết khi nào nên im lặng").

### Hạng 2 — Kiểm định nhân quả Regional CoT
- **Vá gì:** Regional CoT chỉ là mẹo prompt; lỗi detect đầu độc bước sau; không rõ lợi ích đến từ **đúng vùng** hay chỉ **thói quen nhìn vùng**.
- **Cách làm (thuần inference, rất rẻ):** 4 nhánh đối chứng — (i) no-box, (ii) box model tự detect, (iii) box **oracle** (GT), (iv) box **ngẫu nhiên/đối nghịch**.
  - Gap (iii)−(ii) = trần lợi ích còn lại do lỗi detect.
  - (ii)−(iv) = model có thật sự dùng **nội dung** box hay chỉ bị "mồi" bởi sự hiện diện của box.
  - Thêm self-consistency top-k box + verifier nhẹ (inference-time) để vá error-propagation.
- **Vì sao hạng 2:** đánh trúng "linh hồn" region-grounded reasoning của MedRegA; câu hỏi này là khe hở mà SOTA 2025 (Ophiuchus, VLM-R3) **bỏ ngỏ**; mọi kết quả (kể cả phản trực giác "box sai vẫn không hại") đều đáng giá.

### Hạng 3 — Meta-evaluation metric cho song ngữ/đa phương thức
- **Vá gì:** IoU@0.5 nhị phân (0.51 và 0.95 như nhau); box to dễ đạt IoU cao; alignment exact-match phạt đồng nghĩa; BLEU-1 vô nghĩa với output 1–2 từ.
- **Cách làm:** **đừng chỉ nhập SOTA metric** (RadFact spatial cũng nhị phân hóa ở IoU 0.5 → kế thừa đúng lỗi). Tách 2 trục: **factual** = RadFact/GREEN entailment (không lệ thuộc box); **localization** = mAP@[.5:.95] + boundary-IoU + AR theo size. Đóng góp chính = **meta-evaluation**: ~150–300 câu có 1–2 bác sĩ chấm, đo correlation (Kendall/Spearman) + sensitivity-to-error của từng metric **riêng cho tiếng Trung** và **riêng cho CT/MRI** — chứng minh metric nào sống/chết ngoài CXR-English. Thêm probe left/right-swap + sai chẩn đoán đối nghịch.

> **Ghép thành một stack mạch lạc "region-grounded reliability":** 1b sinh ra hiện tượng cần đo → 3 cung cấp thước đo đúng → 4 thêm trục độ-tin-cậy. Bán thành 1 câu chuyện thay vì 3 mẩu rời.

---

## ⚠️ Cảnh báo liêm chính trích dẫn (RẤT QUAN TRỌNG)

Các agent phát hiện **một số trích dẫn đáng nghi / năm tương lai** trong phần SOTA tự sinh. **Phải tự kiểm tra từng nguồn trước khi đưa vào báo cáo**, gỡ nếu không truy được:
- arXiv ID khả nghi: `2601.12471`, `2502.06884`, `2601.17918`, "Nature Sci Rep 2026", và mọi ID dạng `26xx.xxxxx`.
- Lỗi venue cần sửa: **MMedPO là ICML 2025** (không phải ICLR/OpenReview).
- Các con số kiểu "+22% AUROC / giảm 70–85% calibration error": chỉ trích nếu xác minh được nguồn gốc.

Những tên đã verify được và an toàn để tham chiếu (nên tự check lại): RadFact (MAIRA-2), GREEN (EMNLP 2024), RaTEScore, RadGraph-F1, LISA, PolyFormer, CheXbert/NegBio, CARES, MedVH.

---

## Các hướng đã DROP (Gemma 4 nuốt hoặc trùng SOTA nặng)
- Mở khóa/đổi vision encoder, tăng độ phân giải, connector tốt hơn → **Gemma 4 lo rồi**.
- Train end-to-end detect-then-reason bằng GRPO + ROI-feature + gating → **đã bị Ophiuchus (12/2025) và VLM-R3 (5/2025) chiếm**; chỉ giữ phần kiểm định nhân quả (1b).
- Pixel grounding bằng `<SEG>` + SAM-Med2D → **trùng MedPLIB (AAAI 2025)**, đắt; chỉ giữ bản polygon-as-token rẻ (1a).

---

*Ghi chú: Đây là phân tích/đề xuất của nhóm dựa trên bài MedRegA (ICLR 2025) + khảo sát SOTA. Mọi trích dẫn SOTA cần tự xác minh trước khi nộp.*
