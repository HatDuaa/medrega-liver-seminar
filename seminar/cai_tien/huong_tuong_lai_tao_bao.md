# Hướng cải tiến TƯƠNG LAI (tham vọng nhưng chính đáng)

> Phần "Future Work" cho seminar: *nếu có thêm thời gian/nguồn lực thì đi đâu*.
> Đồ án hiện tại: fine-tune **Gemma 4 E4B (~8B)** phát hiện + khoanh box **u gan trên CT LiTS**, sinh box dạng text `<ref>...</ref><box>[...]</box>`, mới làm **detect trên 1 lát 2D**.
>
> **Nguyên tắc chọn ý ở đây:** ĐI XA HƠN các file đã có (`huong_cai_tien_MedRegA.md`, `luu_y_va_yeu_diem.md`, `cai_tien_SOTA.md`). Những gì đã bàn — unlock vision/connector, curriculum, RL lâm sàng, song ngữ dịch máy, tăng visual token, backbone lớn hơn, selective prediction/conformal, kiểm định nhân quả Regional CoT, meta-evaluation metric, polygon-as-token, negation-check — **KHÔNG lặp lại** ở đây; chỉ tham chiếu khi cần.
>
> Mỗi ý gồm: (a) tên ngắn · (b) khoảng trống nó lấp · (c) ý tưởng cách làm · (d) tham vọng & khả thi · (e) 1 câu nói khi trình bày.
> Xếp từ **khả thi gần → tham vọng xa**.

---

## Bức tranh 1 dòng

> Đồ án đã trả lời được *"khoanh được u ở đâu"* và *"khi nào không nên tin"*. Bảy hướng dưới đây trả lời tiếp: **khoanh xong thì NÓI gì (báo cáo có dẫn chứng), NHÌN bằng mắt nào (encoder/segmenter y khoa), HÀNH ĐỘNG như bác sĩ (gọi công cụ), và hiểu u như VẬT THỂ 3D THẬT — tiến tới một model region-centric đa cơ quan.**

---

## 1. Grounded Report — từ "vẽ box" sang "nói có dẫn chứng"

*(khả thi gần nhất — đây chính là task gốc của MedRegA mà đồ án còn thiếu)*

- **(a) Tên:** Grounded Report Generation (báo cáo gắn vùng — mỗi câu mô tả liên kết tường minh với một box).
- **(b) Khoảng trống:** Đồ án mới làm **detect** (task 2/3 của MedRegA). Chưa có **task 3 — sinh báo cáo mà từng câu neo vào một vùng cụ thể** ("Có một tổn thương giảm đậm độ ở hạ phân thùy VII `<box>[...]</box>`, bờ không đều"). Đây là điểm khiến MedRegA "giống bác sĩ": vừa mô tả vừa chỉ chỗ, cho phép **truy vết** (traceability) từng nhận định về đúng pixel.
- **(c) Cách làm:** Dữ liệu output đổi từ chỉ box sang **cặp (câu mô tả ↔ box)**. Sinh mô tả bán tự động từ nhãn LiTS + đặc trưng đo được (vị trí phân thùy gan, kích thước, độ tương phản), rồi bác sĩ rà mẫu. Fine-tune tiếp Gemma 4 E4B để sinh chuỗi xen kẽ chữ-và-box. Đánh giá: ngoài IoU, thêm **entailment factual** (mỗi câu có được ảnh chứng thực không — kiểu RadFact/GREEN) và **grounding-consistency** (câu nói "thùy phải" thì box có nằm thùy phải không).
- **(d) Tham vọng & khả thi:** **Ngắn hạn.** Tái dùng gần hết pipeline hiện có; chi phí chính là làm nhãn mô tả. Rủi ro: mô tả sinh máy dễ "translationese" y khoa → cần bác sĩ rà.
- **(e) Câu nói:** "Đồ án mới dạy model *chỉ chỗ*; bước tiếp là dạy nó *vừa chỉ vừa nói* — mỗi câu trong báo cáo neo vào đúng vùng, để bác sĩ truy được mọi nhận định về đúng pixel."

---

## 2. Mắt y khoa lai: dùng foundation segmenter (MedSAM) làm "người khoanh", VLM làm "người đặt tên"

- **(a) Tên:** Hybrid perception — segmentation foundation model + VLM (chia vai: khoanh vùng vs. diễn giải).
- **(b) Khoảng trống:** Nút thắt lớn nhất của đồ án là **localization chỉ trung bình (pIoU ≈ 0.27)** vì VLM regress toạ độ *dạng text* từ lưới patch thô — vốn không thiết kế để cho ranh giới khít. Trong khi đó **MedSAM/SAM** cho **mask pixel-level** rất khít. Ý này khác hẳn "tăng visual token / unlock vision encoder" (đã bàn): ta **không bắt VLM khoanh khít nữa**, mà **giao việc khoanh cho một mô hình chuyên**, VLM lo phần ngôn ngữ/chẩn đoán.
- **(c) Cách làm:** Hai kiến trúc:
  1. **VLM-đề-xuất → segmenter-tinh-chỉnh:** box thô của Gemma làm *prompt* cho MedSAM → MedSAM trả mask khít → chuyển mask thành box/polygon chính xác. Rẻ, ghép rời, không train lại VLM.
  2. **Segmenter-đề-xuất → VLM-gán-nhãn:** MedSAM/SAM sinh mọi vùng ứng viên → VLM đọc từng vùng, quyết định "u / mạch máu / nhu mô lành" và mô tả. Đúng tinh thần "region-centric": mắt khoanh, não đặt tên.
- **(d) Tham vọng & khả thi:** **Ngắn–trung hạn.** Bản (1) làm được nhanh, gần như plug-in. Bản (2) tham vọng hơn (cần điều phối 2 model). Rủi ro: MedSAM cần prompt tốt; lỗi khoanh của segmenter lại đầu độc VLM → cần đo tách bạch.
- **(e) Câu nói:** "Thay vì ép một model vừa nhìn vừa nói vừa khoanh khít, ta chia vai như phòng khám: một mô hình chuyên *khoanh* (MedSAM), VLM chuyên *đọc và đặt tên* — mỗi bên làm đúng sở trường."

---

## 3. Regional Chain-of-Thought có GIÁM SÁT từng bước (soi vùng → suy luận → chẩn đoán)

- **(a) Tên:** Supervised Regional CoT (chuỗi suy luận theo vùng, huấn luyện tường minh — không chỉ prompt lúc suy luận).
- **(b) Khoảng trống:** File cũ đã đề xuất *kiểm định nhân quả* Regional CoT (box oracle vs random — để **đo** xem model có thật dùng vùng). Ý này đi xa hơn: **thực sự huấn luyện** chuỗi lý luận có dẫn chứng vùng, với **giám sát ở TỪNG bước**, chứ không dừng ở đo lường. Lấp khoảng trống: hiện model nhảy thẳng từ ảnh → box, không có "vết suy nghĩ" kiểm được — một hộp đen về mặt lâm sàng.
- **(c) Cách làm:** Xây dữ liệu CoT có cấu trúc theo mẫu bác sĩ đọc phim: **(1) quét → liệt kê vùng nghi ngờ `<box>` → (2) với mỗi vùng: đo dấu hiệu (đậm độ, bờ, ngấm thuốc) → (3) suy luận phân biệt (u vs. nang vs. mạch) → (4) kết luận + độ tin cậy**. Giám sát từng bước (process supervision) thay vì chỉ giám sát đáp án cuối, giúp bắt lỗi "đúng đáp án nhờ lý do sai". Ghép với reward mô hình ở từng bước nếu có ngân sách.
- **(d) Tham vọng & khả thi:** **Trung hạn.** Đắt ở khâu tạo dữ liệu CoT chất lượng (cần bác sĩ hoặc chưng cất từ model lớn rồi lọc). Nhưng cực kỳ đáng giá cho tính giải thích được (explainability) — thứ hội đồng y khoa luôn hỏi.
- **(e) Câu nói:** "Bác sĩ không phán ngay — họ soi từng vùng, cân dấu hiệu, loại trừ. Ta muốn dạy model *quy trình* đó một cách tường minh và giám sát từng bước, để mỗi chẩn đoán đi kèm vết suy luận kiểm được."

---

## 4. Từ 2D box → 3D detection thật (u là vật thể 3 chiều)

- **(a) Tên:** 2.5D/3D lesion detection (khoanh khối u theo thể tích, không theo một lát).
- **(b) Khoảng trống:** Đồ án tự nhận 2 hạn chế gốc: **3D→2D mất thông tin** và **"kích thước u" chỉ là proxy diện tích box 2D, không phải thể tích thật**. Một khối u trải qua nhiều lát; nhìn 1 lát thì u nhỏ và mạch máu cắt ngang **trông y hệt nhau** — chỉ ngữ cảnh 3D (theo dõi qua các lát) mới phân biệt được. Đây là nguồn gốc nhiều ca sót/nhầm.
- **(c) Cách làm:** Ba nấc tăng dần:
  1. **2.5D rẻ:** nạp một *chồng* vài lát kề (dưới/giữa/trên) làm nhiều kênh hoặc nhiều ảnh → VLM có ngữ cảnh dọc trục z mà không cần kiến trúc 3D. Phân biệt u (khối tồn tại qua nhiều lát) vs. mạch (mảnh, đổi vị trí nhanh).
  2. **Ghép box liên-lát thành khối 3D:** detect 2D từng lát rồi liên kết các box chồng nhau qua z → **bounding volume** → báo **thể tích thật** (đơn vị lâm sàng đúng, thay proxy 2D).
  3. **Box token 3D thật:** mở rộng cú pháp `<box>[x1,y1,z1,x2,y2,z2]</box>`, VLM sinh khối 3D trực tiếp. Tham vọng nhất.
- **(d) Tham vọng & khả thi:** **Trung → dài hạn.** Nấc (1)(2) khả thi gần (hậu xử lý + ngữ cảnh nhẹ); nấc (3) là nghiên cứu thật (VLM sinh toạ độ 3D còn ít tiền lệ). Trực tiếp vá đúng 2 hạn chế người dùng đã nêu.
- **(e) Câu nói:** "Khối u là vật thể 3D; nhìn một lát thì u và mạch máu giống hệt nhau. Bước tiếp là cho model thấy chiều sâu — rẻ thì chồng vài lát kề, tham vọng thì sinh box 3D thật và báo thể tích, không phải diện tích proxy."

---

## 5. Agentic — VLM gọi công cụ như bác sĩ (đo HU, chạy segmenter, tra cứu)

- **(a) Tên:** Tool-use / agentic radiologist (VLM điều phối công cụ chuyên rồi tổng hợp).
- **(b) Khoảng trống:** VLM tự "ước lượng bằng mắt" mọi thứ — kể cả những đại lượng **đo được chính xác** (đậm độ Hounsfield, thể tích, so với lát trước). Bác sĩ thật thì *dùng công cụ*: kéo ROI đo HU, đối chiếu phim cũ. Việc bắt VLM nội suy các con số này trong đầu vừa kém chính xác vừa dễ bịa (hallucination số liệu). Khác hẳn các hướng trên: đây là **thay đổi cách vận hành lúc suy luận**, không phải train thêm.
- **(c) Cách làm:** Đóng gói các công cụ: `measure_HU(box)` (đọc đậm độ từ CT gốc — u gan thường giảm đậm độ so nhu mô), `segment(box)` (gọi MedSAM ở ý #2), `compare_prior(patient)` (đối chiếu lần chụp trước), `lookup(term)` (tra tiêu chí chẩn đoán). Gemma 4 hỗ trợ tool-calling → model **quyết định gọi công cụ nào**, nhận kết quả số, rồi mới kết luận. Reward/curriculum có thể dạy *khi nào nên gọi công cụ*.
- **(d) Tham vọng & khả thi:** **Trung hạn.** Từng công cụ dễ viết (đo HU chỉ là đọc pixel value trên ảnh chưa windowed). Cái khó là dạy model *điều phối* đáng tin và tránh gọi loạn. Rất "kể được" trước hội đồng vì mô phỏng đúng hành vi bác sĩ.
- **(e) Câu nói:** "Bác sĩ không đoán đậm độ bằng mắt — họ đo. Ta cho VLM cùng bộ công cụ: đo HU, gọi segmenter, đối chiếu phim cũ — rồi mới kết luận. Model thành *người điều phối*, không phải người đoán mò mọi con số."

---

## 6. Uncertainty có nguyên lý + conformal cho BOX (đảm bảo phủ ground-truth theo xác suất)

- **(a) Tên:** Conformal region prediction (dự đoán vùng có bảo chứng thống kê về độ phủ).
- **(b) Khoảng trống:** Đồ án đã làm selective prediction (bỏ ca kém tin) và conformal *ở mức ngưỡng chọn/bỏ*. Bước xa hơn — **conformal cho chính hình học của box**: thay vì trả một box điểm, trả một **vùng bao có bảo chứng** "chứa GT với xác suất ≥ 90%" (một *prediction set* không gian). Đây là loại đảm bảo mà lâm sàng cần nhưng gần như chưa ai làm cho detection sinh-bằng-text. Khác selective (bỏ/giữ cả ca): đây là *định lượng bất định ngay trên toạ độ*.
- **(c) Cách làm:** Sinh N mẫu box (đã có hạ tầng multi-sample từ slide 8) → dùng **conformal prediction** trên tập calibration để nới box điểm thành **vùng tin cậy** (nới biên sao cho phủ GT đúng mức 1−α trên calibration). Báo hai lớp: "vùng chắc chắn có u" (giao các mẫu) và "vùng có thể có u" (hợp/đã nới) — giống bác sĩ khoanh "chắc chắn" vs. "nghi ngờ". Mondrian/class-conditional theo cỡ u để giữ bảo chứng cho cả u nhỏ.
- **(d) Tham vọng & khả thi:** **Trung hạn.** Nền lý thuyết conformal đã vững; cái mới là *áp cho hình học box sinh bằng text*. Rào cản chính: cỡ mẫu calibration nhỏ (đồ án ~13 bệnh nhân) → bảo chứng lỏng; cần dữ liệu lớn hơn để phát biểu mạnh.
- **(e) Câu nói:** "Thay vì một box cứng, ta trả một *vùng có bảo chứng*: 'chứa khối u với xác suất ≥ 90%'. Model khoanh hai lớp như bác sĩ — vùng chắc chắn và vùng nghi ngờ — kèm một lời hứa thống kê kiểm được."

---

## 7. Generalist region-centric đa cơ quan/đa bệnh — mở rộng ý "chỉ train u gan" thành tầm nhìn lớn

*(tham vọng xa nhất — đây là "bắc thang lên trời" chính đáng)*

- **(a) Tên:** Multi-organ / multi-disease region-centric foundation (một model khoanh-và-đọc cho nhiều cơ quan, nhiều bệnh, nhiều thì CT).
- **(b) Khoảng trống:** Đồ án cố tình **thu hẹp về đúng u gan** để khả thi. Nhưng chính điểm mạnh của công thức region-centric — "khoanh vùng rồi đặt tên" — **không phụ thuộc vào cơ quan nào**. Đây là lời hứa lớn: một khung duy nhất phủ gan → thận → tụy → phổi, u → nang → sỏi → viêm. Đồng thời gom hai hướng còn lại người dùng nêu: **kết hợp bệnh sử/text lâm sàng** và **nhiều thì CT** (không thuốc / động mạch / tĩnh mạch — u gan đặc trưng bởi *kiểu ngấm thuốc theo thì*, một lát không thuốc là mù thông tin này).
- **(c) Cách làm:** Ba trụ:
  1. **Đa cơ quan bằng một model:** hợp nhất nhiều dataset segmentation công khai (gan, thận, tụy, phổi…) về cùng format region-text; curriculum từ dễ (cơ quan lớn) → khó (tổn thương nhỏ). Kiểm **task interference** (các cơ quan cắn nhau) — đúng cảnh báo capacity-bound của E4B → có thể cần MoE/adapter theo cơ quan.
  2. **Fusion đa thì CT + bệnh sử:** nạp nhiều thì (arterial/venous/delayed) để model *thấy kiểu ngấm thuốc*; ghép text lâm sàng (tuổi, xét nghiệm, tiền sử viêm gan) như thêm ngữ cảnh — bệnh sử thay đổi xác suất tiền nghiệm của chẩn đoán.
  3. **Tận dụng CT không nhãn (self-/weak-supervision):** phần lớn CT trên đời **không có box**. Pretrain tự giám sát trên khối CT lớn (contrastive bình thường-vs-bất thường, masked-modeling) để "mắt" học khái niệm "khác lạ" trước, rồi mới fine-tune vùng trên phần ít nhãn — giảm phụ thuộc nhãn đắt.
- **(d) Tham vọng & khả thi:** **Dài hạn / tầm nhìn.** Không làm trong seminar; là "bắc thang" cho thấy phương pháp mở rộng tới đâu. Rào cản thật: capacity của model nhỏ, hợp nhất dữ liệu không đồng nhất, và task interference. Nói tỉnh táo thì đây là *hướng*, không phải lời hứa xong-trong-một-kỳ.
- **(e) Câu nói:** "Ta cố tình bó về u gan để khả thi — nhưng công thức 'khoanh rồi đọc' không biết đến ranh giới cơ quan. Tầm nhìn xa là một model region-centric duy nhất cho nhiều cơ quan, nhiều thì CT và cả bệnh sử, học phần lớn từ CT chưa gán nhãn. Đó là đích, không phải bài tập kỳ này."

---

## Bảng tổng — xếp khả thi gần → tham vọng xa

| # | Hướng | Lấp khoảng trống chính | Tham vọng | Khả thi |
|---|---|---|---|---|
| 1 | **Grounded Report** (nói có dẫn chứng) | mới có detect, thiếu báo cáo gắn vùng | vừa | **Ngắn hạn** ⭐ |
| 2 | **Mắt lai MedSAM + VLM** | pIoU 0.27 — VLM khoanh không khít | vừa | Ngắn–trung |
| 3 | **Regional CoT giám sát từng bước** | model là hộp đen, không có vết suy luận | vừa-cao | Trung |
| 4 | **2D → 3D detection thật** | mất thông tin 3D; u lẫn mạch; size proxy | cao | Trung–dài |
| 5 | **Agentic tool-use** (đo HU, segment, tra cứu) | VLM đoán số thay vì đo | cao | Trung |
| 6 | **Conformal cho hình học box** | box cứng, không bảo chứng độ phủ | cao | Trung |
| 7 | **Generalist đa cơ quan + đa thì + self-sup** | bó hẹp u gan; bỏ bệnh khác; 1 thì | **rất cao** | **Dài hạn** |

---

## 3 câu chuyện ghép (nếu muốn kể thành mạch, không rời rạc)

1. **"Nói được, chỉ được, khoanh khít được":** #1 (báo cáo gắn vùng) + #2 (segmenter khoanh khít) + #3 (vết suy luận) → một trợ lý *vừa chỉ vừa giải thích vừa khoanh chuẩn*.
2. **"Đáng tin trong lâm sàng":** #5 (đo thay vì đoán) + #6 (bảo chứng độ phủ) → nối thẳng vào lớp selective-prediction đồ án đã có, thành một stack *độ tin cậy* hoàn chỉnh.
3. **"Đúng bản chất vật lý → mở rộng ra thế giới":** #4 (u là vật thể 3D thật) + #7 (mọi cơ quan, mọi thì, học từ dữ liệu không nhãn) → từ đúng-một-lát-gan tới tầm nhìn generalist.

---

## Câu chốt cho slide Future Work

> "Đồ án này chứng minh một *cơ chế* — region-centric khả thi ở quy mô tiếp cận được. Bảy hướng trên là bản đồ mở rộng: gần nhất là dạy model **nói có dẫn chứng** và **khoanh khít bằng segmenter chuyên**; xa nhất là một model **hiểu u như vật thể 3D** và **khoanh-đọc cho mọi cơ quan, học từ biển CT chưa gán nhãn**. Chúng em không hứa đã tới đích — chúng em chỉ ra con đường và nói rõ chỗ nào còn dốc."

---

*Ghi chú: Đề xuất hướng tương lai của nhóm, mở rộng từ phân tích MedRegA (ICLR 2025) và kết quả đồ án u gan LiTS. Các tên công cụ (MedSAM/SAM, RadFact/GREEN, conformal prediction) là hướng tham chiếu — cần tự xác minh nguồn trước khi đưa vào bản nộp.*
