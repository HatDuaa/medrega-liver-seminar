# Region-centric phát hiện u gan trên CT ở quy mô tiếp cận được
### Fine-tune Gemma 4 E4B theo ý tưởng MedRegA — báo cáo mạch paper

> **Sợi chỉ xuyên suốt:** Phương pháp gốc (MedRegA làm gì) → Cải tiến của nhóm (đổi gì, vì sao) → Kết quả (đo được gì) → So sánh (đặt cạnh gốc cho công bằng) → Hướng tương lai (mỗi con số còn yếu ở phần Kết quả *đẻ ra* một hướng đi tiếp).
>
> Nguyên tắc trung thực: đây là **PoC (proof-of-concept — chứng minh cơ chế khả thi)**, KHÔNG tuyên bố vượt SOTA. Mọi thuật ngữ kỹ thuật đều giải thích ngắn trong ngoặc.

---

## 0. Vì sao có bài này (một câu)

Bác sĩ đọc phim theo thứ tự **khoanh vùng → mô tả vùng → chẩn đoán kèm vị trí**. Model "region-agnostic" (không biết vùng) nén cả ảnh thành một vector rồi sinh chữ, **bỏ mất bước khoanh vùng** → sai vị trí kéo theo sai chẩn đoán. MedRegA vá chỗ này bằng cách bắt model **sinh kèm toạ độ vùng**. Nhóm lấy đúng ý tưởng đó nhưng đưa về **quy mô một sinh viên chạy được** và **đánh giá chặt hơn**.

---

## 1. PHƯƠNG PHÁP GỐC — MedRegA (Wang et al., ICLR 2025)

### 1.1. Kiến trúc mô hình (các phần)

MedRegA xây trên **InternVL 1.2 (~40B tham số)**, gồm 4 khối nối tiếp:

| Khối | Vai trò | Chi tiết |
|---|---|---|
| **Vision Encoder** | "mắt" — trích đặc trưng ảnh | **InternViT-6B**, ảnh 448×448, patch 14 → lưới 32×32 token |
| **Pixel Shuffle** | nén token ảnh, giữ cấu trúc 2D | gộp token lân cận để giảm số token đưa vào LLM |
| **MLP Connector** | "cầu" — chiếu đặc trưng ảnh sang không gian của LLM | 1 khối MLP (mạng tuyến tính nhiều lớp) |
| **LLM** | "não" — sinh chữ, suy luận | **Nous-Hermes-2-Yi-34B** (giải mã một chiều, decoder-only) |

**Mấu chốt của ý tưởng — biểu diễn vùng bằng CHỮ:** thay vì thêm một "đầu phát hiện" (detection head) riêng, MedRegA viết toạ độ box **thành text ngay trong câu trả lời**:

```
<ref>liver tumor</ref><box>[x1, y1, x2, y2]</box>
```

Toạ độ **chuẩn hoá về thang 0–1000** (không phụ thuộc kích thước ảnh thật). Nhờ vậy bài toán "khoanh vùng" trở thành bài toán "sinh chữ" quen thuộc của LLM → tận dụng được sức mạnh ngôn ngữ sẵn có.

**3 định dạng tác vụ theo vùng (region-centric):**
1. **Region-to-Text** (cho box → gọi tên vùng): "vùng này là gì?"
2. **Text-to-Region** (cho mô tả → xuất box): "vùng bất thường ở đâu?"
3. **Grounded Report** (báo cáo gắn vùng): mỗi câu mô tả *neo* vào một box cụ thể.

**Regional CoT (Chain-of-Thought theo vùng — chuỗi suy nghĩ):** lúc suy luận, model **khoanh vùng trước, rồi mới chẩn đoán dựa trên vùng đó**, thay vì phán thẳng. Đây chỉ là *mẹo lúc dùng*, không được huấn luyện tường minh.

### 1.2. Cấu trúc huấn luyện (2 giai đoạn)

| Giai đoạn | Học gì | Trạng thái các khối |
|---|---|---|
| **GĐ1 — Alignment (căn chỉnh)** | dạy Connector "phiên dịch" ảnh↔chữ, trên cặp ảnh–caption (mô tả), **KHÔNG có box** | Vision + LLM **đóng băng**, chỉ train Connector |
| **GĐ2 — Instruction tuning (tinh chỉnh theo lệnh)** | dạy làm mọi tác vụ y khoa theo lệnh, trên **MedRegInstruct (790K mẫu, 8 phương thức ảnh, song ngữ Anh–Trung)** | train LLM; Connector **đóng băng lại** |

- **Hàm mất mát:** cross-entropy tiêu chuẩn của mô hình ngôn ngữ (khớp từng token, kể cả token toạ độ) — không có loss hình học riêng cho box.
- **Ảnh 3D (CT/MRI):** chỉ lấy **một lát cắt 2D ở giữa** khối u (central slice).
- **Song ngữ:** dùng **hai nguồn dữ liệu bản ngữ riêng** (Anh: MIMIC-CXR + bộ công khai; Trung: dữ liệu lâm sàng nội bộ), **KHÔNG dịch** Anh↔Trung.
- **Tài nguyên:** **16× GPU H800 (~1.280 GB VRAM)**, vài ngày.

### 1.3. Hạn chế của phương pháp gốc *(bản lề để bước sang cải tiến)*

- Dồn gần hết gánh nặng lên **LLM 40B**; **"mắt" (Vision Encoder) và "cầu" (Connector) gần như bất động** → đặc trưng định vị "định vị được nhưng không sắc" (IoU thấp, hay bỏ sót vùng ở ca nhiều ổ).
- **Không có** cơ chế **từ chối trả lời khi không chắc** (abstain), **không dùng ca âm** (ảnh không có u), **không đo độ tin cậy**.
- Đánh giá **theo từng ảnh** (micro), IoU@0.5 — **không theo bệnh nhân**, không khoảng tin cậy.
- Chi phí **ngoài tầm** một đồ án sinh viên.

---

## 2. CẢI TIẾN CỦA NHÓM (so với gốc)

> Đóng khung: *MedRegA để "mắt" và "cầu" bất động, dồn hết lên LLM 40B. Nhóm **thu hẹp phạm vi** (1 phương thức ảnh — CT gan, 1 tác vụ — phát hiện u) để khả thi, và **bù lại bằng đánh giá chặt hơn** + vài cơ chế gốc không có.*

### 2.1. Kiến trúc — đổi backbone

| | MedRegA gốc | Của nhóm |
|---|---|---|
| Backbone | InternVL 1.2 (~40B) | **Gemma 4 E4B (~8B)** — nhỏ hơn ~5× |
| Vision | InternViT-6B (tổng quát, đóng băng) | **SigLIP** (nhỏ) — và nhóm **mở khoá để fine-tune** |
| Chạy được trên | 16× H800 | **1 GPU rẻ / Colab–Kaggle** |

Lý do đổi: Vision Encoder của MedRegA **không hề được fine-tune y khoa** → không đáng giữ; lấy nguyên một VLM (mô hình ngôn ngữ–thị giác) đời mới đã có sẵn khả năng grounding (khoanh vùng) rồi fine-tune còn tốt hơn. *(Lưu ý phản biện: KHÔNG nói "Gemma 4 giỏi hơn MedRegA" — Gemma mạnh trên ảnh thường; ở ảnh y khoa phải fine-tune mới cạnh tranh được.)*

### 2.2. Dữ liệu — LiTS, đa lát, đa box, có ca âm

- Bộ **LiTS (Liver Tumor Segmentation)** — CT gan có mask (mặt nạ vùng) đầy đủ.
- **Đa box:** một lát có nhiều ổ u → tách bằng **connected-components** (`scipy.ndimage.label` — gán nhãn từng vùng liên thông) → mỗi ổ một box, thay vì một box gộp.
- **Đa lát:** mỗi ca lấy nhiều lát (u lớn + vài lát ngẫu nhiên) thay vì chỉ 1 lát giữa như gốc.
- **Ca âm (negatives):** đưa cả lát **không có u** vào — để đo tỉ lệ **báo động giả (false-positive)**, thứ MedRegA bỏ qua.
- Augment (tăng cường dữ liệu) hợp CT gan: **không lật trái–phải** (giải phẫu gan có chiều).

### 2.3. Huấn luyện

- **LoRA trên LLM** (Low-Rank Adaptation — chỉ chèn thêm ma trận nhỏ, giữ nguyên trọng số gốc) **+ full-finetune Vision tower** (fp32, LR 1e-5).
- **Hàm mất mát:** cross-entropy tiêu chuẩn. *(Bài học: nhóm ĐÃ thử thêm một nhánh BCE-head để dạy riêng quyết định "có/không u", nhưng **thất bại** — trọng số λ quá lớn lấn át loss toạ độ, model hỏng → đã revert. Đây là kinh nghiệm sẽ dùng ở phần Future.)*
- **LoRA giữ trọng số gốc** → là nền tảng cho việc "fine-tune mà không quên" (mục 3).

### 2.4. Đánh giá — chặt hơn hẳn gốc *(đây là điểm mới thật sự của nhóm)*

| Thứ nhóm thêm | Ý nghĩa |
|---|---|
| **Đánh giá theo bệnh nhân** (per-patient) + **bootstrap CI** (khoảng tin cậy bằng lấy mẫu lặp) | không thổi phồng bằng cách đếm từng lát; báo cả độ bất định |
| **Tách "phát hiện" khỏi "định vị"** | "có/không u đúng" (detection) là câu hỏi khác "khoanh trúng chỗ" (localization) — MedRegA gộp làm một |
| **Selective prediction** (dự đoán có chọn lọc) | model **biết khi nào không nên tin**: ngưỡng theo **logprob** (độ chắc token) + **nhất quán không gian** (box có hội tụ khi sample nhiều lần không) |
| **Penalized IoU** | phạt khi khoanh thừa/thiếu số ổ, không chỉ đo chồng lấp |

---

## 3. KẾT QUẢ

### 3.1. Trước → sau fine-tune (before/after)

| Chỉ số | Zero-shot (Gemma 4 chưa train) | Sau fine-tune | 
|---|---|---|
| **Detection F1** (theo bệnh nhân) | 0.33 | **0.89** |
| **Sensitivity** (độ nhạy — tỉ lệ bắt được u) | 20% | **80%** |
| **Localization recall @ IoU 0.25** (tỉ lệ khoanh trúng) | 0% | **54%** |
| **per-patient pIoU** (chồng lấp trung bình/bệnh nhân) | 0.002 | **0.270** — CI95 [0.186, 0.359] |
| **False-positive** (báo động giả, trên lát âm) | 2.2% | **1.5%** |

Zero-shot gần như luôn trả "No liver tumor is found." → chứng minh fine-tune **dạy được task từ số 0**.

### 3.2. Fine-tune KHÔNG làm "quên" (một điểm cộng ngoài dự kiến)

Lo ngại tự nhiên: fine-tune hẹp có làm model "ngu" đi việc khác? Test hội thoại đa lượt (lượt 1 = prompt detect như train, các lượt sau hỏi tự do bằng tiếng Anh) cho thấy model **vẫn**: khoanh được u, trả lời đúng JSON (đúng key), đếm đúng số câu, giải thích song ngữ cho bệnh nhân, làm thơ, tính `17×23=391`, và **nhớ ngữ cảnh** giữa các lượt. Lý do: **LoRA giữ nguyên trọng số gốc**, chỉ cộng thêm delta nhỏ → thêm kỹ năng mà không xoá kỹ năng cũ.

### 3.3. Phân tích lỗi *(bản lề sang Future — quan trọng)*

Các u **bị sót** chủ yếu là **isointense** (đồng tỉ trọng — cùng độ đậm với nhu mô gan), **KHÔNG phải u nhỏ**: pid=116 có u chiếm **5.63% diện tích** vẫn bị sót; u sót vs u bắt được kích thước xấp xỉ nhau (1.28% vs 1.32%). Cửa sổ hiển thị CT đang để **rộng (WL40/WW400)** → nén dải xám, làm chênh lệch u–gan biến mất.

---

## 4. SO SÁNH VỚI PAPER GỐC

> **Nguyên tắc:** KHÔNG so số trực tiếp (khác dữ liệu / tác vụ / cách tính / quy mô). So **tính chất** và **thứ mỗi bên có/không có**.

| Khía cạnh | MedRegA gốc | Của nhóm |
|---|---|---|
| Quy mô | ~40B, 16× H800, vài ngày | **~8B, 1 GPU rẻ** |
| Phạm vi | 8 phương thức ảnh, song ngữ, 3 task | **1 phương thức (CT gan), 1 task (detect)** |
| Đánh giá | micro theo ảnh, IoU@0.5 | **per-patient + CI**, tách detect/localize |
| Độ tin cậy | không có abstain/độ tin cậy | **selective prediction** ✔ |
| Ca âm | không dùng | **có, đo false-positive** ✔ |
| Grounded report (task 3) | **có** ✔ | chưa (→ Future) |

- Về định vị: MedRegA Text-to-Region **IoU ~23**, của nhóm **pIoU 0.27** — *cùng khoảng "định vị thô", KHÔNG kết luận hơn/kém* vì khác bộ dữ liệu và cách tính.
- **Trung thực về giới hạn thống kê:** test rất nhỏ (~25 bệnh nhân dương, **chỉ 2 bệnh nhân hoàn toàn không-u**) → "specificity" (độ đặc hiệu) **chưa đủ dữ liệu để kết luận**; CI rộng; 1 dataset. → Đây là **PoC chứng minh cơ chế khả thi ở quy mô tiếp cận được**, không phải tuyên bố SOTA.

**Đóng góp thật của nhóm** (không phải "MedRegA thu nhỏ"): (1) đưa region-centric về quy mô chạy được; (2) **khung đánh giá chặt** (per-patient, CI, tách detect/localize); (3) **selective prediction** — "biết khi nào không nên tin"; (4) chứng minh **fine-tune không quên** nhờ LoRA.

---

## 5. HƯỚNG TƯƠNG LAI

> **Mỗi hướng trỏ NGƯỢC về một con số còn yếu ở phần 3–4.** Không có ý nào từ trên trời — đây là chỗ làm bài "mạch paper".

| Kết quả/hạn chế còn yếu | → Hướng đi tiếp | Chi phí |
|---|---|---|
| **Sót u isointense** (§3.3), cửa sổ rộng WL40/WW400 | **① Multi-window** — đóng gói 3 cửa sổ (gan hẹp WL80/WW150 + rộng + tối) vào 3 kênh R/G/B để kéo giãn đúng chênh lệch u–gan | 🟢 rất thấp |
| **3D→2D mất thông tin, u lẫn mạch máu** (ý gốc) | **② 2.5D stack** — nhồi lát z−1/z/z+1 vào 3 kênh: mạch máu (ống xuyên lát) trùng vị trí → xám; u (khu trú 1 lát) → lệch màu, nổi bật. Không tốn thêm token | 🟢 thấp |
| *(gốc rễ ý trên)* | **③ CT đa pha** (arterial/portal/delayed) — u gan tách khỏi mạch bằng **động học ngấm–thải thuốc**, không bằng hình học. **LiTS chỉ 1 thì → u isointense về bản chất không tách được**: đây là trần của DỮ LIỆU, không phải của model | 🔴 cần data khác |
| **pIoU chỉ 0.27** (§3.1, box thô) | **④ Mắt lai MedSAM + VLM** — segmenter chuyên *khoanh khít* (mask pixel-level), VLM *đặt tên/chẩn đoán*; và **polygon-as-token** tận dụng mask LiTS thay box thô | 🟡 vừa |
| **2 ca âm, 1 dataset, CI rộng** (§4) | **⑤ External validation** (test lên **3D-IRCADb / MSD Task03** để chống overfit) + **thêm ca âm** vá specificity + **FROC** (metric chuẩn phát hiện nhiều ổ) + **calibration** (model nói 80% có đúng 80%?) | 🟡 chủ yếu inference |
| **Chỉ làm detect** (thiếu task 3 của gốc) | **⑥ Grounded report** — mỗi câu mô tả neo vào một box → "vừa chỉ vừa nói" như bác sĩ, truy vết được từng nhận định về đúng pixel | 🟡 vừa |
| **Chỉ train u gan** (ý gốc) | **⑦ Generalist đa cơ quan** — công thức "khoanh rồi đọc" không phụ thuộc cơ quan; mở rộng gan→thận→tụy→phổi. Caveat: E4B ~8B có thể **chật tham số** (task interference — các tác vụ cắn nhau) | 🔴 dài hạn |
| **Vụ BCE-head fail** (§2.3) | **⑧ Cân bằng loss thông minh** — thay chỉnh λ tay bằng **uncertainty weighting** (mỗi loss tự học trọng số) + bật phụ-loss muộn + λ mềm; thêm **loss hình học** (GIoU) qua soft-argmax | 🟢 thấp |

### Kể thành 3 mạch (đừng liệt kê rời)

1. **"Ảnh giàu hơn"** → ①②③: trả lại tương phản và chiều sâu đã vứt khi ép 2D đơn pha.
2. **"Đáng tin & an toàn hơn"** → ⑤ + selective sẵn có: đánh giá theo chuẩn an toàn lâm sàng, không chạy theo SOTA.
3. **"Từ chỉ-chỗ tới nói-có-dẫn-chứng, rồi generalist"** → ⑥④⑦: khoanh khít hơn, nói có bằng chứng hơn, mở ra nhiều cơ quan.

### Câu chốt slide Future

> *"Chúng em không đoán bừa hướng tương lai — mỗi hướng vá đúng một con số mà kết quả của chính chúng em chỉ ra là còn yếu. Gần nhất: làm ảnh giàu thông tin hơn (multi-window, 2.5D) và đánh giá đáng tin hơn (external validation, calibration). Xa nhất: hiểu u như vật thể 3D và khoanh-đọc cho mọi cơ quan. Chúng em không hứa đã tới đích — chỉ ra con đường và nói rõ chỗ nào còn dốc."*

---

*Nguồn: tổng hợp từ phân tích MedRegA (Wang et al., ICLR 2025) + kết quả đồ án u gan LiTS của nhóm. Số liệu chốt từ `eval_baseline.ipynb`; các tên công cụ (MedSAM, FROC, conformal, IRCADb/MSD) là hướng tham chiếu — tự xác minh nguồn trước khi nộp. Chi tiết brainstorm đầy đủ: [huong_tuong_lai_tao_bao.md](huong_tuong_lai_tao_bao.md), [huong_cai_tien_MedRegA.md](huong_cai_tien_MedRegA.md), [luu_y_va_yeu_diem.md](luu_y_va_yeu_diem.md).*
