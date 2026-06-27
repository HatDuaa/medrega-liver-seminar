# Giải thích chi tiết bài báo MedRegA (từ Phần C → hết)

> Bài báo: *Interpretable Bilingual Multimodal Large Language Model for Diverse Biomedical Tasks* (MedRegA), ICLR 2025 — arXiv:2410.18387.
> Tài liệu này dành cho người **mới đọc paper**: giải thích kỹ ý tưởng, dữ liệu, phương pháp, kèm sơ đồ từng bước.

---

## 0. Toàn cảnh: nhóm tác giả đã làm gì? (sơ đồ tổng)

Cả bài báo có thể tóm thành **5 bước lớn** nối tiếp nhau. Mỗi bước giải quyết một việc, bước trước làm tiền đề cho bước sau:

```
┌───────────────────────────────────────────────────────────────────────────┐
│ BƯỚC 1 — PHÁT HIỆN VẤN ĐỀ                                                    │
│ MLLM y khoa cũ "mù vùng" (region-agnostic): nhìn cả ảnh như 1 khối,          │
│ không biết đang nói về vùng nào → mô tả/chẩn đoán sai, không giải thích được │
└───────────────────────────────┬───────────────────────────────────────────┘
                                 │  "Phải dạy mô hình chỉ tay vào đúng vùng"
                                 ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ BƯỚC 2 — ĐỊNH NGHĨA 3 TÁC VỤ "REGION-CENTRIC" (lấy vùng làm trung tâm)       │
│  (1) Region → Text   (2) Text → Region   (3) Grounded Report Generation      │
└───────────────────────────────┬───────────────────────────────────────────┘
                                 │  "Muốn dạy thì phải có dữ liệu — mà chưa có"
                                 ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ BƯỚC 3 — TỰ XÂY BỘ DỮ LIỆU MedRegInstruct                                    │
│  • Region-Text  (~550K)      • Region-Grounded (~240K)                       │
│  Dùng dây chuyền BÁN TỰ ĐỘNG để khỏi gán nhãn tay hàng triệu vùng           │
└───────────────────────────────┬───────────────────────────────────────────┘
                                 │  "Có dữ liệu rồi → huấn luyện mô hình"
                                 ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ BƯỚC 4 — HUẤN LUYỆN MÔ HÌNH MedRegA                                          │
│  Nền InternVL → mã hóa vùng bằng token <ref>/<box>                           │
│  Huấn luyện 2 giai đoạn + mẹo suy luận "Regional CoT"                        │
└───────────────────────────────┬───────────────────────────────────────────┘
                                 │  "Huấn luyện xong → đo xem có tốt không"
                                 ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ BƯỚC 5 — ĐÁNH GIÁ                                                            │
│  Tác vụ truyền thống (VQA, báo cáo, phân loại) + 3 tác vụ vùng              │
│  Tự đề xuất khung đo "Region-Aligned" → MedRegA đứng đầu                     │
└───────────────────────────────────────────────────────────────────────────┘
```

Phần dưới đây đi sâu vào **Bước 2 → Bước 5** (tức Phần C → hết).

---

## C. Ý tưởng cốt lõi & 3 tác vụ "region-centric"

### C0. Vì sao gọi là "region-centric"?
- **Region** = một **vùng** trên ảnh (thường là 1 cơ quan như gan/phổi/tim, hoặc 1 tổn thương như khối u).
- **Region-centric** = "lấy vùng làm trung tâm": mọi phát biểu của mô hình đều phải **neo vào một vùng cụ thể**, thay vì nói chung chung về cả ảnh.
- Đối lập với **region-agnostic** ("mù vùng") của mô hình cũ.

Bài định nghĩa **3 tác vụ**. Hãy nhớ: tất cả đều xoay quanh quan hệ giữa **VĂN BẢN** (chữ mô tả) ↔ **VÙNG** (bounding box).

> **Bounding box** = hình chữ nhật khoanh vùng, ghi bằng 4 số `[x1, y1, x2, y2]`
> (x1,y1) = góc trên-trái, (x2,y2) = góc dưới-phải.

```
        x1                 x2
   y1   ┌──────────────────┐
        │                  │
        │   vùng cần nói    │   ←  box = [x1, y1, x2, y2]
        │                  │
   y2   └──────────────────┘
```

### C1. Tác vụ 1 — Region → Text (Nhận dạng Vùng→Văn bản)
**Cho biết vùng, hỏi đó là gì.**

```
ĐẦU VÀO:  [ảnh y khoa]  +  [1 bounding box]      (ví dụ: box khoanh ở giữa ngực)
                │
                ▼
            MedRegA
                │
                ▼
ĐẦU RA:   "Đây là tim (cardiac silhouette)."     (tên cấu trúc / tổn thương)
```
- Mục đích: kiểm tra mô hình có **hiểu nội dung của một vùng** khi được "chỉ" vào hay không.
- Bài chia nhỏ thành 2 loại: **nhận dạng cấu trúc** (cơ quan bình thường) và **nhận dạng tổn thương** (u, ung thư). Nhận dạng cấu trúc dễ hơn vì cơ quan to; tổn thương khó hơn vì nhỏ và đa dạng hình.

### C2. Tác vụ 2 — Text → Region (Phát hiện Văn bản→Vùng)
**Cho biết tên, hỏi nó nằm đâu.** (Chiều ngược lại của C1.)

```
ĐẦU VÀO:  [ảnh y khoa]  +  [tên đối tượng: "gan"]
                │
                ▼
            MedRegA
                │
                ▼
ĐẦU RA:   <box>[388, 270, 956, 1281]</box>       (tọa độ vùng của gan)
```
- Mục đích: mô hình phải **tự định vị** được cấu trúc/tổn thương trên ảnh.
- Có thể yêu cầu **nhiều đối tượng** cùng lúc, hoặc **một đối tượng nằm ở nhiều vùng** → bài chia thành 4 trường hợp con (xem Phần F).

### C3. Tác vụ 3 — Grounded Report Generation (Sinh báo cáo có định vị)
**Tác vụ "đỉnh" — kết hợp cả viết báo cáo + chỉ vùng.**

```
ĐẦU VÀO:  [ảnh y khoa]
                │
                ▼
            MedRegA
                │
                ▼
ĐẦU RA:   Một báo cáo, MỖI CÂU gắn 1 box:
          • <ref>Phổi trái</ref> <box>[...]</box>: thể tích phổi giảm nhẹ...
          • <ref>Bóng tim</ref>  <box>[...]</box>: tim to vừa...
          • <ref>Gan</ref>       <box>[...]</box>: thấy nốt giảm tỉ trọng ~35mm...
```
- **"Grounded"** = *neo/gắn*: mỗi nhận định được **gắn vào bằng chứng** (vùng ảnh) thay vì chữ trôi nổi.
- Đây là cái khiến báo cáo **kiểm chứng được** → bác sĩ nhìn box là biết AI căn cứ vào đâu → tăng **tính diễn giải (interpretability)**.

### C4. Vì sao 3 tác vụ này quan trọng?
Chúng buộc mô hình học **mối quan hệ 2 chiều giữa chữ và vùng**:
- C1 dạy "đọc" vùng → chữ.
- C2 dạy "viết" chữ → vùng.
- C3 dạy làm cả hai cùng lúc trong một báo cáo hoàn chỉnh.

→ Khi thành thạo, mô hình **không thể nói mơ hồ** nữa: nói gì cũng phải kèm "ở đâu".

---

## D. Dữ liệu: bộ MedRegInstruct (chi tiết)

**Vấn đề:** muốn dạy 3 tác vụ trên thì cần dữ liệu ghép *văn bản ↔ vùng*, nhưng **chưa có bộ nào** đủ lớn và đa cơ quan. → Nhóm **tự xây** bộ **MedRegInstruct**, gồm 2 bộ con:

| Bộ con | Quy mô | Một mẫu gồm gì | Phục vụ tác vụ |
|---|---|---|---|
| **Region-Text** | ~550.000 | (ảnh, cặp hỏi-đáp, vùng) | C1 (Region→Text) & C2 (Text→Region) |
| **Region-Grounded** | ~240.000 | (ảnh, báo cáo gắn vùng + mô tả chi tiết từng vùng) | C3 (Grounded Report) |

### D1. Bộ Region-Text (~550K) — đến từ đâu, làm thế nào?

**Nguồn:** **SA-Med2D-20M** — bộ dữ liệu *phân đoạn* (segmentation) khổng lồ, ảnh y khoa 2D của gần như mọi bộ phận cơ thể.
- *Phân đoạn (segmentation)*: mỗi pixel được dán nhãn thuộc cơ quan nào → tạo thành **mặt nạ (mask)** tô màu theo cơ quan.

**Quy trình:**
```
SA-Med2D-20M (rất nhiều ảnh + mask)
        │
        │ ① Lọc ~285.000 ảnh (giữ đa dạng cơ quan + tổn thương)
        ▼
   Ảnh + Mask (mặt nạ phân đoạn)
        │
        │ ② Chuyển MASK → BOUNDING BOX
        │    (lấy hình chữ nhật bao quanh mask — chỉ cần định vị thô)
        ▼
   Cặp (ảnh, vùng)
        │
        │ ③ Điền tên vùng + tọa độ vào MẪU CÂU (template) sẵn
        ▼
   ~550.000 cặp hỏi-đáp
   ├── ~một nửa: Region → Text
   └── ~một nửa: Text → Region
```
> **Tại sao đổi mask → box?** Vì bài chỉ cần "khoanh vùng để định vị", không cần đường viền chi li từng pixel. Box gọn, dễ cho mô hình ngôn ngữ sinh ra (chỉ 4 số).

### D2. Bộ Region-Grounded (~240K) — khó hơn, cần báo cáo thật

**Nguồn (2 kho dữ liệu):**
- **MIMIC-CXR**: bộ X-quang ngực công khai cực lớn (~371.920 ảnh, ~227.943 báo cáo, ~65.079 bệnh nhân).
- **Dữ liệu nội bộ bệnh viện** (Sun Yat-Sen Memorial Hospital): **25.000 ảnh** X-quang/CT/MRI từ **15.000 bệnh nhân**, phủ **não, bụng, ngực, cột sống, khung chậu**. Báo cáo bằng **tiếng Trung** → đây là nguồn tạo năng lực **song ngữ Anh–Trung**.

**Pipeline xây dựng tự động — 3 BƯỚC (đây chính là Hình 3 của bài):**

```
                ┌──────────────────────────────────────────────┐
   BƯỚC 1       │  XÂY CẶP ẢNH – BÁO CÁO                         │
   Image-Report │  • MIMIC-CXR: dùng ảnh thẳng + nghiêng,        │
   Pair         │    gộp "Findings" + "Impression"              │
                │  • Nội bộ: ảnh 3D (CT/MRI) → lấy LÁT CẮT       │
                │    TRUNG TÂM làm ảnh 2D đại diện               │
                │  → tạo ~95.000 cặp ảnh–báo cáo                 │
                └───────────────────┬──────────────────────────┘
                                    ▼
                ┌──────────────────────────────────────────────┐
   BƯỚC 2       │  TINH CHỈNH BÁO CÁO                            │
   Report       │  Báo cáo gốc = 1 đoạn dài, lẫn nhiều cơ quan   │
   Refinement   │  • Luật (rule-based): liệt kê danh sách cơ quan│
                │  • LLM InternLM: TÁCH báo cáo thành mô tả      │
                │    RIÊNG cho từng cơ quan                      │
                │  VD →  "Gan: ...", "Túi mật: ...", "Thận: ..." │
                └───────────────────┬──────────────────────────┘
                                    ▼
                ┌──────────────────────────────────────────────┐
   BƯỚC 3       │  PHÁT HIỆN CẤU TRÚC (gắn TỌA ĐỘ cho mỗi mô tả) │
   Structure    │  • MIMIC-CXR: dùng nhãn box sẵn của            │
   Detection    │    Chest ImaGenome (29 vị trí → chọn 12 ở ngực)│
                │    → ghép box ↔ mô tả → ~220.000 báo cáo       │
                │  • Nội bộ: CHƯA có box cơ quan →               │
                │     finetune 1 MLLM trên bộ Region-Text (D1),  │
                │     rồi dùng nó TỰ SINH box cho cơ quan;       │
                │     tổn thương (u) thì bác sĩ đã khoanh tay    │
                └───────────────────┬──────────────────────────┘
                                    ▼
                  Báo cáo có ĐỊNH VỊ: mỗi câu ↔ 1 box  (~240K)
```

**Bước kiểm định chất lượng (Human Validation):**
- Lấy ngẫu nhiên **50 mẫu**, mời **2 chuyên gia** gán nhãn tay để so sánh.
- Tách câu (Bước 2): chính xác **93,33%**.
- Box (Bước 3): chính xác **~72%**. Box thường hơi to hơn một chút nhưng **vẫn bao trùm** vùng mục tiêu → đủ dùng (vì chỉ cần định vị, không cần box khít tuyệt đối).

> **Thông điệp lớn của Phần D:** thay vì thuê bác sĩ ngồi khoanh tay hàng trăm nghìn vùng (cực đắt & chậm), nhóm dựng **dây chuyền bán tự động** = dùng dữ liệu có sẵn (SA-Med2D-20M, Chest ImaGenome) + AI (InternLM, MLLM finetune) để **tự sinh nhãn vùng quy mô lớn**. Đây là phần "khôn" nhất của bài.

---

## E. Phương pháp: mô hình MedRegA

### E1. Mấu chốt: "nhét" tọa độ vào trong NGÔN NGỮ
Ý tưởng tinh tế: **coi tọa độ như một phần của chữ**, để mô hình ngôn ngữ (vốn giỏi sinh chữ) cũng "đọc/viết" được tọa độ.

- Box `[x1,y1,x2,y2]` được **chuẩn hóa** về số nguyên trong khoảng `[0, 1000)`
  → không phụ thuộc kích thước ảnh gốc (ảnh to/nhỏ đều quy về cùng thang 0–1000).
- Nhúng vào câu bằng **token đặc biệt**:

```
   <ref> tên đối tượng </ref> <box>[x1,y1,x2,y2]</box>
        ↑ "CÁI GÌ"                  ↑ "Ở ĐÂU"

   Ví dụ mô hình sinh ra:
   <ref>vùng bất thường</ref><box>[340,414,386,436]</box>
```

→ Nhờ cách này:
- **Region → Text**: cho box trong câu hỏi, mô hình sinh chữ tên vùng. (đọc tọa độ)
- **Text → Region**: cho tên, mô hình sinh ra `<box>...</box>`. (viết tọa độ)
- Cả hai đều quy về **bài toán sinh văn bản** quen thuộc.

### E2. Kiến trúc — dựa trên InternVL 1.2
```
  ẢNH ──► [ Vision Encoder ]──►[ Module nối ]──►┐
          InternViT-6B          (alignment)     │
                                                ├──► [ Language Model ]──► VĂN BẢN ĐẦU RA
  CHỮ (câu hỏi/chỉ dẫn) ────────────────────────┘     Nous-Hermes-2-Yi-34B    (kèm <ref>/<box>)
```
- **Vision Encoder** `InternViT-6B`: "mắt" — biến ảnh thành vector.
- **Module nối**: "phiên dịch" vector ảnh sang không gian ngôn ngữ.
- **Language Model** `Nous-Hermes-2-Yi-34B`: "não" — đọc ảnh + chữ → sinh câu trả lời.

### E3. Huấn luyện 2 giai đoạn
> Ký hiệu: ❄️ = đóng băng (không cập nhật trọng số), 🔥 = được huấn luyện.

```
GIAI ĐOẠN 1 — ALIGNMENT (căn chỉnh)
  Vision Encoder ❄️   Module nối 🔥   Language Model ❄️
  Dữ liệu: ảnh y khoa + chú thích (captioning)
  Mục tiêu: dạy "module nối" hiểu cách phiên dịch ảnh Y KHOA sang ngôn ngữ
        │
        ▼
GIAI ĐOẠN 2 — INSTRUCTION TUNING (tinh chỉnh theo chỉ dẫn)
  Vision Encoder ❄️   Module nối ❄️   Language Model 🔥
  Dữ liệu: dữ liệu công khai (VQA, báo cáo, phân loại)  +  MedRegInstruct (3 tác vụ vùng)
  Mỗi tác vụ có CHỈ DẪN riêng để mô hình biết đang được yêu cầu làm gì
  Hàm mất mát: loss của mô hình ngôn ngữ (dự đoán token kế tiếp)
```
→ Kết quả: **một mô hình đa năng** làm được VQA + báo cáo + phân loại + 3 tác vụ vùng, lại **song ngữ**.

### E4. Mẹo lúc suy luận: REGIONAL CoT (rất quan trọng)
- **CoT (Chain-of-Thought)** = "chuỗi suy luận": thay vì trả lời ngay, mô hình "nghĩ nháp" trước rồi mới kết luận → thường chính xác hơn.
- **Regional CoT** = CoT bằng **vùng**: ép mô hình **phát hiện vùng trước → rồi mới suy luận**.

```
  CÁCH CŨ (trả lời thẳng):
     Ảnh + câu hỏi ──► MedRegA ──► Trả lời   (dễ nhìn lướt cả ảnh → sai)

  REGIONAL CoT (2 bước):
     ┌─ STAGE 1: PHÁT HIỆN VÙNG ───────────────┐
     │  Ảnh + "khoanh các vùng bất thường"      │
     │       └──► MedRegA ──► các <box>[...]     │
     └──────────────────┬──────────────────────┘
                        │ (đưa chính các vùng vừa tìm được vào lại)
     ┌─ STAGE 2: SUY LUẬN DỰA TRÊN VÙNG ────────┐
     │  Ảnh + câu hỏi + các vùng đã phát hiện    │
     │       └──► MedRegA ──► Trả lời / chẩn đoán│
     └──────────────────────────────────────────┘
```
- **Trực giác:** giống bác sĩ khoanh vùng nghi ngờ rồi mới kết luận, thay vì phán bừa khi nhìn lướt.
- **Hiệu quả (phân loại đa nhãn, bộ VinDr-SpineXR — X-quang cột sống):**
  - MedRegA + Regional CoT: **F1 = 61,75%**
  - cao hơn MedDr **~34,95%** và cao hơn chính MedRegA-không-CoT **~31,59%**.
- **Lý do:** Regional CoT buộc mô hình nối **từng vùng cục bộ ↔ từng nhãn bệnh**, thay vì gộp cả ảnh tổng thể với tất cả nhãn cùng lúc.

---

## F. Đánh giá & cách đọc kết quả

### F1. Tác vụ truyền thống (so với các mô hình khác)
So sánh với: Med-Flamingo, LLaVA-Med, RadFM, MedDr, BiomedGPT, và mô hình nền InternVL.

| Tác vụ | Bộ dữ liệu đánh giá | Kết quả tóm tắt của MedRegA |
|---|---|---|
| **VQA** | SLAKE, VQA-RAD, PathVQA (Anh + Trung) | Vượt baseline ~2–40% (Anh), >10% (Trung) |
| **Sinh báo cáo** | MIMIC-CXR, IU-Xray + bộ tiếng Trung | BLEU-1 trung bình cao hơn MedDr **5,97%** (Anh), **28,77%** (Trung) |
| **Phân loại** | nhiều bộ (X-quang, siêu âm, mắt, da) | Đơn nhãn vượt ~15–31%; đa nhãn cải thiện mạnh nhờ Regional CoT |

> Con số tiếng Trung nhảy vọt là nhờ **dữ liệu song ngữ nội bộ** (các baseline khác hầu như không làm tốt tiếng Trung).

### F2. Tác vụ region-centric & khung "Region-Aligned" (tự đề xuất)
Vì là tác vụ **mới**, nhóm phải tự nghĩ cách đo. Khung đo theo **3 chiều** (đây là Hình 6):

```
  (1) OBJECT-LEVEL        : có nhận đúng ĐỐI TƯỢNG không?
                            (ví dụ: có liệt kê đúng "gan, lách, thận" không)

  (2) REGION-LEVEL        : có khoanh đúng VÙNG không?
                            dùng IoU = độ chồng lấn giữa box dự đoán & box thật
                            (IoU > 0,5 → coi là đúng)

  (3) OBJECT-REGION       : box có gắn ĐÚNG với đối tượng tương ứng không?
      ALIGNMENT             (quan trọng khi có NHIỀU đối tượng — tránh
                            "đúng box nhưng dán nhầm tên")
```

**IoU (Intersection over Union)** — đo độ trùng giữa 2 hình chữ nhật:
```
            diện tích phần GIAO (chồng lên nhau)
   IoU = ───────────────────────────────────────
            diện tích phần HỢP (gộp cả hai)

   IoU = 1  → trùng khít hoàn toàn
   IoU = 0  → không chồng nhau tí nào
```

**Bài chia Text→Region thành 4 trường hợp** (theo số đối tượng × số vùng):
```
                       1 vùng / đối tượng        nhiều vùng / đối tượng
   1 đối tượng    │  đơn-đối-tượng đơn-vùng  │  đơn-đối-tượng đa-vùng
   nhiều đối tượng│  đa-đối-tượng đơn-vùng   │  đa-đối-tượng đa-vùng
```
→ Càng nhiều đối tượng/vùng càng khó. Bài nhận xét: khi nhiều vùng, mô hình **recall < precision** (tức là **bỏ sót** vùng — sinh ra ít box một cách thận trọng).

### F3. Điểm mấu chốt khi đọc các bảng số (Bảng 1–5)
- Các mô hình cũ **KHÔNG làm được** tác vụ vùng → ô của chúng ghi **`x`** (hoặc điểm gần 0).
- Chỉ InternVL (giỏi ảnh thường) có chút khả năng nhưng **rất thấp**.
- MedRegA **bỏ xa**. Ví dụ Region→Text: BertScore **87,13** so với InternVL **49,85** (chênh ~39,85%).
- Lưu ý: dấu trong bảng — `N/A` = không báo cáo; `-` = không sinh được output hợp lệ; `*` = mô hình được finetune riêng trên bộ đó (nên điểm cao là dễ hiểu).

---

## G. Tóm tắt một mạch (để thuyết trình)

1. **Vấn đề:** MLLM y khoa cũ "mù vùng" → mô tả/chẩn đoán dễ sai, **không giải thích được** cho bác sĩ.
2. **Ý tưởng:** dạy mô hình làm như bác sĩ — **gắn mỗi câu nói với một vùng (bounding box)** cụ thể trên ảnh (region-centric), qua **3 tác vụ**: Region→Text, Text→Region, Grounded Report.
3. **Dữ liệu:** vì chưa có → tự xây **MedRegInstruct** (550K Region-Text + 240K Region-Grounded) bằng **dây chuyền bán tự động** (SA-Med2D-20M, MIMIC-CXR, dữ liệu bệnh viện + InternLM + Chest ImaGenome).
4. **Mô hình MedRegA:** nền InternVL; mã hóa vùng bằng token `<ref>`/`<box>`; huấn luyện 2 giai đoạn; thêm **Regional CoT** (phát hiện vùng trước → suy luận sau).
5. **Kết quả:** đứng đầu cả tác vụ truyền thống lẫn tác vụ vùng; **song ngữ Anh–Trung**; là mô hình **duy nhất** thực sự làm được 3 tác vụ region-centric → vừa **chính xác hơn** vừa **giải thích được**.

> **Một câu mở đầu seminar:**
> *"MedRegA dạy AI y khoa biết **chỉ tay vào đúng vùng** trên ảnh khi mô tả/chẩn đoán — nhờ bộ dữ liệu MedRegInstruct gắn văn bản với bounding box và cơ chế Regional CoT (phát hiện vùng trước, suy luận sau) — giúp kết quả vừa chính xác hơn vừa giải thích được cho bác sĩ."*

---

## Phụ lục — Bảng thuật ngữ nhanh

| Thuật ngữ | Nghĩa ngắn gọn |
|---|---|
| **MLLM** | Mô hình ngôn ngữ lớn đa phương thức (LLM + "mắt" nhìn ảnh) |
| **Modality (phương thức)** | Loại ảnh chụp: X-quang, CT, MRI, siêu âm, giải phẫu bệnh... |
| **Region-agnostic** | "Mù vùng" — nhìn cả ảnh như 1 khối, không biết vùng nào |
| **Region-centric** | "Lấy vùng làm trung tâm" — mọi phát biểu neo vào 1 vùng cụ thể |
| **Bounding box** | Hình chữ nhật khoanh vùng, ghi bằng `[x1,y1,x2,y2]` |
| **Grounded** | "Neo/gắn" — mỗi câu mô tả gắn với 1 vùng bằng chứng |
| **Segmentation / mask** | Phân đoạn: dán nhãn cơ quan cho từng pixel → mặt nạ tô màu |
| **VQA** | Hỏi-đáp dựa trên hình ảnh |
| **CoT (Chain-of-Thought)** | Chuỗi suy luận: nghĩ nháp trước, kết luận sau |
| **Regional CoT** | CoT bằng vùng: phát hiện vùng trước → rồi mới suy luận |
| **IoU** | Độ chồng lấn giữa box dự đoán và box thật (0→1) |
| **BLEU / ROUGE / METEOR / BertScore** | Các thước đo độ giống nhau giữa văn bản sinh ra và văn bản chuẩn |
| **Interpretability** | Tính diễn giải — khả năng giải thích/kiểm chứng kết quả của mô hình |
```
