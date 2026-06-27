# Hạn chế & Hướng cải tiến cho MedRegA

> Tài liệu phản biện cho seminar. Mỗi điểm gồm: **hạn chế quan sát được → bằng chứng từ kết quả của bài → đề xuất cải tiến**.
> Gốc chung của hầu hết hạn chế: bài **dồn gần hết gánh nặng lên LLM**, còn **"mắt" (Vision Encoder) và "cầu" (Connector) bị đóng băng hoặc chỉ chỉnh theo caption**.
>
> **Backbone nhóm chọn để triển khai: `Gemma 4 E4B`** (Google, 04/2026) — VLM mở nhỏ, mới nhất, có sẵn detection/pointing, đa ngôn ngữ (tiếng Việt), cấu hình được visual token. Thay cho stack 40B cũ của MedRegA (xem Mục 7).

---

## 1. Connector chỉ học trên ảnh + caption, không học chuyển đổi khi có box

**Hạn chế.** Connector chỉ được huấn luyện ở Giai đoạn 1 (captioning, *không có box*) rồi **đóng băng** ở Giai đoạn 2. Phép "phiên dịch" đặc trưng ảnh → không gian LLM vì vậy được tối ưu cho **mô tả tổng thể**, chưa bao giờ tối ưu cho **giữ chi tiết không gian / định vị**.

**Bằng chứng từ bài.** IoU thấp (ví dụ ca đa-đối-tượng đa-vùng IoU chỉ ~15) và **recall < precision** ở các ca nhiều vùng (mô hình bỏ sót vùng) — phù hợp với việc biểu diễn ảnh đưa vào LLM chưa đủ "giàu không gian".

**Cải tiến.**
- Mở khóa connector ở Giai đoạn 2 (hoặc LoRA cho connector) để nó **đồng thích nghi** với tác vụ vùng.
- Thêm **một giai đoạn căn chỉnh trung gian** cho connector dùng dữ liệu Region-Text (ảnh ↔ box) trước instruction tuning.
- Dùng connector **giữ nhiều token / giữ cấu trúc 2D hơn** (giảm pixel-shuffle) cho nhánh tác vụ vùng.

---

## 2. Vision Encoder không học trích xuất tọa độ — liệu có thực sự encode được vị trí?

**Hạn chế.** Vị trí *có* được mã hóa (qua positional embedding của ViT) nên LLM mới regress ra tọa độ; **nhưng** encoder **chưa từng được tối ưu cho định vị**, nên đặc trưng "định vị được nhưng không sắc". Nút thắt chính là **độ phân giải**: ảnh 448×448, patch 14 → lưới 32×32, lại pixel-shuffle → độ mịn không gian thô → box chỉ thô.

**Bằng chứng từ bài.** Box chỉ ở mức định vị (auto-label ~72%); bài tự nói chỉ cần định vị, không cần box khít.

**Cải tiến.**
- Mở khóa Vision Encoder (LoRA) để học đặc trưng thân thiện với định vị.
- Tăng độ phân giải: với **Gemma 4** có thể **tăng visual token budget** (model cho phép cấu hình) → lưới mịn hơn → box chính xác hơn, bắt tổn thương nhỏ tốt hơn.
- Thêm **đầu phát hiện phụ (detection head)** hoặc pretrain định vị trên ảnh y khoa để "mắt" quen việc khoanh vùng.

---

## 3. Vision Encoder có encode được "bất thường" không, khi chưa từng học y khoa?

**Hạn chế.** Vision Encoder (InternViT) pretrain trên **ảnh tổng quát / web**, **không** được fine-tune giám sát trên ảnh y khoa. Thích nghi y khoa chỉ xảy ra ở connector (caption) + LLM. Nên đặc trưng cho **tổn thương tinh vi** (u nhỏ, nốt mờ) có thể bị thiếu/yếu ngay từ tầng "mắt".

**Bằng chứng từ bài.** Nhận dạng **tổn thương (lesion) kém hơn cấu trúc (structure)**; **phân loại đa nhãn khó nhất** — đúng kiểu "mắt không nhạy với khác biệt tinh vi".

**Cải tiến.**
- Continue-pretrain / fine-tune Vision Encoder trên ảnh y khoa (tự giám sát hoặc với nhãn bất thường).
- Hoặc thay bằng **encoder chuyên y khoa** (kiểu BiomedCLIP / medical SigLIP) thay vì InternViT tổng quát.
- Pretrain kiểu **contrastive bình thường vs bất thường** để "mắt" học khái niệm "khác lạ".

---

## 4. Tác vụ "soi từng phần" lại trộn chung train — nên có bước dạy mô hình tập trung từng cơ quan

**Hạn chế.** Hiện bài trộn tất cả tác vụ vào **một nồi instruction tuning**, và "soi từng vùng rồi mới kết luận" (**Regional CoT**) **chỉ là mẹo lúc suy luận**, không được huấn luyện tường minh thành một quy trình suy luận.

**Cải tiến.**
- **Học theo lộ trình (curriculum):** giai đoạn A dạy định vị / grounding cho vững → giai đoạn B mới dạy chẩn đoán *dựa trên* vùng.
- **Huấn luyện tường minh chuỗi "phát hiện → chẩn đoán"** (CoT có giám sát: dữ liệu dạng *tìm vùng bất thường → rồi trả lời*), thay vì chỉ prompt lúc suy luận.
- Dùng **RL** thưởng cho chuỗi "soi đúng vùng → kết luận đúng".

---

## 5. (Bổ sung) Hàm mất mát cross-entropy 1-1 — tối ưu khớp token, không phải đúng lâm sàng

**Hạn chế.** Cross-entropy phạt cả diễn đạt **đúng nghĩa nhưng khác chữ**; nó tối ưu "khớp token" chứ không phải "đúng lâm sàng".

**Cải tiến.**
- Dùng **RL** với phần thưởng là chỉ số lâm sàng (CheXBert / RadGraph / RadCliQ) hoặc định vị (IoU) — vốn không khả vi nên không nhét vào loss thường được.
- Thêm dữ liệu đa dạng cách diễn đạt để giảm cứng nhắc.

---

## 6. Bản địa hóa: làm song ngữ Anh–Việt

**Hai sự thật nền (từ bài gốc):**
- MedRegA song ngữ **Anh–Trung** nhờ **hai nguồn dữ liệu bản ngữ riêng**: tiếng Anh từ MIMIC-CXR + bộ công khai; tiếng Trung từ **dữ liệu lâm sàng nội bộ**. Phương pháp gốc **KHÔNG dịch** Anh↔Trung khi huấn luyện.
- Phần **dữ liệu tiếng Trung nội bộ KHÔNG được công khai** (bài chỉ phát hành dữ liệu tạo từ nguồn công khai) → ta **không có** để dùng.

**Ý tưởng cải tiến.** Vì không có dữ liệu Trung, để có ngôn ngữ thứ hai là tiếng Việt, ta **dịch phần dữ liệu tiếng Anh công khai sang tiếng Việt** (dùng LLM lớn), **giữ nguyên bản tiếng Anh** → ra tập song ngữ **Anh–Việt**. Đây là điểm **mới** so với bản gốc (bản gốc dùng dữ liệu bản ngữ, không dịch).

- Phần tiếng Anh: **giữ nguyên** (MIMIC-CXR, VQA Anh, region-text\ldots).
- Phần tiếng Việt: **dịch máy từ chính dữ liệu tiếng Anh đó**.
- (Chỉ khi xin được dữ liệu Trung nội bộ thì mới có lựa chọn dịch Trung→Việt để giữ nội dung đa cơ quan — nhưng thực tế khó.)

**Cần làm cẩn thận:**
- **Giữ nguyên token tọa độ khi dịch:** với `<ref>gan</ref><box>[388,270,...]</box>: mô tả`, chỉ dịch phần chữ và tên trong `<ref>`, **không đụng số trong `<box>`** (dịch nhầm là hỏng tọa độ).
- **Thuật ngữ y khoa:** kèm **từ điển Trung/Anh–Việt** cố định (vd "glioma" → "u thần kinh đệm") để dịch nhất quán; dùng LLM mạnh + hậu kiểm.
- **Chất lượng dịch:** dùng **back-translation** để lọc câu dịch tệ; cho **chuyên gia rà một mẫu nhỏ** (giống bước Human Validation 50 mẫu của bài).
- Lưu ý "translationese": bản dịch máy có thể không giống văn phong báo cáo của bác sĩ Việt thật.

**Lợi ích:**
- Hữu ích thực tế tại Việt Nam (bệnh viện/người dùng Việt).
- Tận dụng được phần nội dung lâm sàng đa cơ quan của bộ tiếng Trung (chỉ đổi ngôn ngữ).
- Rẻ: dịch chỉ là chi phí inference một lần trên phần dữ liệu.
- Ghép tốt với **Gemma 4 E4B** — vốn đã đa ngôn ngữ (hỗ trợ tiếng Việt), nên rất hợp hướng song ngữ này.

**Quy trình gọn:**
```
Dữ liệu Anh  ──────────────────────────────► giữ nguyên (English)
Dữ liệu Anh ─► LLM lớn dịch Anh→Việt ───────► phần tiếng Việt
   (tách phần chữ, GIỮ NGUYÊN <box> số; + từ điển thuật ngữ; back-translation lọc)
                                  │
                                  ▼
        Tập song ngữ Anh–Việt → QLoRA fine-tune Gemma 4 E4B (region-centric)
```

---

## 7. Backbone đã chọn: Gemma 4 E4B

Thay vì cứu vớt stack 40B của MedRegA (vision encoder của bài là InternViT-6B tổng quát, **không** học y khoa → không đáng giữ), nhóm **lấy nguyên một VLM nhỏ hiện đại đã có grounding, rồi QLoRA fine-tune trên dữ liệu vùng y khoa**. **Lựa chọn: `Gemma 4 E4B`.** Bảng dưới so sánh để giải thích vì sao chọn nó:

| Backbone | Cỡ | Grounding sẵn | Điểm mạnh cho ý tưởng |
|---|---|---|---|
| **Gemma 4 E4B** (Google, 04/2026) ⭐ | nhỏ (E2B/E4B) | ✅ detection + pointing | **Mới nhất**; đa ngôn ngữ (tiếng Việt); **cấu hình visual token** (tăng chi tiết ảnh y khoa) |
| Qwen2.5-VL-7B | ~8B | ✅ bbox mạnh | **Song ngữ Anh–Trung** sẵn; grounding chín |
| InternVL2.5-8B | ~8B | ✅ | Cùng "họ" InternVL với bài → dễ kế thừa pipeline |
| PaliGemma 2-3B (Google, 12/2024) | 3B | ✅ detect/segment native | Task format detection đã chín; nhưng **base Gemma 2 cũ** |

**Ghi chú quan trọng về Google:**
- **Gemma 4 E4B là lựa chọn Google ưu tiên hiện nay** (thay PaliGemma 2): mới nhất + có sẵn detection/pointing + đa ngôn ngữ + chỉnh được visual token budget (giúp bắt tổn thương nhỏ — đúng nút thắt độ phân giải).
- PaliGemma 2 chỉ nên chọn nếu cần **task format detection/segmentation đã battle-tested**, chấp nhận base cũ hơn.

**Phân rã tham số (để thấy hiệu quả kiến trúc mới):**

| Model | Vision Encoder | LLM | Tổng |
|---|---|---|---|
| MedRegA (bài) | InternViT-6B | Yi-34B | ~40B |
| **Gemma 4 E4B (chọn)** | SigLIP (nhỏ) | ~4.5B effective | **~8B tổng** (4.5B active) |

→ Nhỏ hơn MedRegA ~5×, vision encoder nhỏ hơn nhiều, mà benchmark tổng quát của Gemma 4 vẫn rất cao (E4B: MMLU-Pro 69.4%, MMMU-Pro 52.6%) → đủ làm nền tốt rồi QLoRA cho y khoa.

**Nếu 8B lộ thiếu tham số** (xem [luu_y_va_yeu_diem.md](luu_y_va_yeu_diem.md) mục 4): nâng lên nấc trung gian **Gemma 4 26B (MoE)** / **InternVL2.5-26B–38B** trước khi chạm quy mô 40B.

---

## Bức tranh tổng: 4 trục cải tiến

| Trục | Vấn đề | Cải tiến |
|---|---|---|
| **Mắt** (Vision Encoder) | đông cứng, không nhạy y khoa / định vị | mở khóa / LoRA, domain pretrain, tăng độ phân giải |
| **Cầu** (Connector) | chỉ học caption, đóng băng ở GĐ2 | mở khóa / đồng thích nghi, thêm giai đoạn căn chỉnh có box |
| **Quy trình train** | trộn 1 nồi, CoT chỉ ở inference | curriculum, train CoT tường minh, RL |
| **Mục tiêu học** | cross-entropy khớp token | thêm RL theo phần thưởng lâm sàng / định vị |

> **Câu chốt cho seminar:** Điểm mạnh của MedRegA là biến định vị thành bài toán *sinh chữ* để tận dụng LLM — nhưng cũng vì vậy nó để "mắt" và "cầu" gần như bất động. Các hạn chế (IoU thấp, bỏ sót vùng, kém với tổn thương tinh vi) đều có thể truy về đó; hướng cải tiến tự nhiên là **làm phần thị giác chủ động hơn** và **huấn luyện theo lộ trình** thay vì trộn một nồi.

---

*Ghi chú: Đây là phần nhận xét/phản biện của nhóm, dựa trên phân tích bài báo gốc MedRegA (ICLR 2025); các "bằng chứng" trích từ kết quả thực nghiệm của chính bài.*
