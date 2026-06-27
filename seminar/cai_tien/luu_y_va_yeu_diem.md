# Lưu ý & Yếu điểm cần cẩn thận (khi triển khai hướng cải tiến)

> File ghi nhanh các "bẫy" và điểm yếu cần thủ sẵn — đặc biệt để trả lời phản biện khi seminar.
> Đi kèm với [huong_cai_tien_MedRegA.md](huong_cai_tien_MedRegA.md).

---

## 1. Không "tháo lắp" LLM được — Connector gắn cứng vào LLM cũ
- Connector của MedRegA được train để chiếu đặc trưng ảnh vào **đúng không gian của Yi-34B**.
- Đổi LLM (vd sang Gemma 4) thì **sai cả khổ vector lẫn không gian ngữ nghĩa** → connector cũ vô dụng.
- ⚠️ Muốn đổi LLM phải **train lại connector** (làm lại giai đoạn alignment) + instruction-tune LLM mới.
- ✅ Vision Encoder thì tái dùng được (độc lập với LLM) — nhưng (xem mục 2) cũng chẳng đáng giữ.

## 2. Vision Encoder của MedRegA KHÔNG được fine-tune y khoa
- Nó là **InternViT-6B tổng quát, đóng băng** → không có tri thức y khoa trong trọng số.
- ⚠️ Vì vậy **không có lý do giữ** vision encoder cũ; dùng nguyên một VLM mới còn tốt hơn.
- 💡 Cơ hội: khi train lại, có thể **mở khóa vision encoder trên ảnh y khoa** (thứ MedRegA bỏ ngỏ) → có thể vượt bản gốc ở tổn thương tinh vi.

## 3. "Model mới mạnh hơn" chỉ đúng trên benchmark TỔNG QUÁT
- VLM đời mới (vd Gemma 4 E4B) vượt base InternVL 1.2 trên MMMU/DocVQA... → nhưng đó là **ảnh thường, không phải y khoa**.
- ⚠️ **Không** được nói "model mới giỏi hơn MedRegA" — MedRegA mạnh nhờ **fine-tune y khoa**, model mới chưa fine-tune thì **thua** ở tác vụ vùng y khoa.
- ✅ Cách nói đúng: *"backbone mới là nền tốt hơn/nhỏ hơn; vẫn phải fine-tune mới cạnh tranh được ở y khoa."*

## 4. Gemma 4 E4B (~4–8B) có thể lộ "thiếu tham số" — tùy phạm vi
- Nếu copy nguyên pipeline rộng (8 modality + song ngữ + mọi tác vụ) lên Gemma 4 E4B → dễ đuối ở:
  - độ phủ generalist, song ngữ, **báo cáo dài**, **long-tail** (đa-nhãn, tổn thương hiếm).
- Triệu chứng capacity-bound: **điểm tụt diện rộng**, **plateau dù thêm data/epoch**, **task interference** (tác vụ cắn nhau).
- ✅ Grounding/sinh tọa độ **không ngốn tham số** → phạm vi hẹp thì E4B thừa sức.
- 🛠️ Giảm nghẽn nếu giữ rộng: **LoRA rank cao**, nâng lên **Gemma 4 26B (MoE)**, adapter riêng theo tác vụ, **curriculum**.
- 👉 An toàn nhất: **thu hẹp phạm vi** (1 modality, 1–2 tác vụ).

## 5. Dữ liệu tiếng Trung — mình KHÔNG có, và bản gốc KHÔNG dịch
- Dữ liệu lâm sàng tiếng Trung là **nội bộ, không công khai** → không lấy được.
- Bản gốc dùng **dữ liệu bản ngữ** (Anh + Trung riêng), **không dịch** Anh↔Trung khi train.
- ⚠️ Nên muốn có tiếng Việt thì phải **tự thêm bước dịch** (Anh→Việt từ dữ liệu công khai) — đây là **điểm mới của nhóm**, không phải tái lập bản gốc.

## 6. Bẫy khi dịch dữ liệu sang tiếng Việt
- ⚠️ **Giữ nguyên token tọa độ** `<box>[...]`: chỉ dịch phần chữ + tên trong `<ref>`, **không đụng số** (dịch nhầm là hỏng tọa độ).
- ⚠️ **Thuật ngữ y khoa** dễ sai → cần **từ điển Anh–Việt** cố định + LLM mạnh + hậu kiểm.
- ⚠️ **"Translationese"**: bản dịch máy ≠ văn phong báo cáo bác sĩ Việt thật.
- ✅ Kiểm soát chất lượng: **back-translation** lọc câu tệ + **chuyên gia rà mẫu nhỏ** (kiểu Human Validation 50 mẫu).

## 7. Hàm mất mát cross-entropy chỉ khớp token, không đo đúng lâm sàng
- ⚠️ Phạt cả diễn đạt **đúng nghĩa nhưng khác chữ**; tối ưu "khớp token" ≠ "đúng bệnh".
- ✅ Đánh giá phải dùng thêm **BERTScore** (ngữ nghĩa) + **chỉ số lâm sàng** (CheXBert/RadGraph/RadCliQ).
- 💡 Nâng cao: dùng **RL** thưởng theo chỉ số lâm sàng/định vị (không khả vi nên không nhét vào loss thường).

## 8. Chi phí / khả thi — đừng định tái huấn luyện toàn bộ
- Bản gốc: **16× H800 (~1.280GB VRAM)**, ~vài ngày, ước tính **hàng nghìn USD** nếu thuê → **không khả thi** cho seminar.
- ⚠️ MedRegA 40B: **1 GPU không đủ** chạy đầy đủ (riêng trọng số BF16 đã 80GB); free Colab/Kaggle (16GB) **không đủ** kể cả INT4 (~24GB).
- ✅ Khả thi: **QLoRA tập nhỏ** trên **Gemma 4 E4B** → chạy được **Colab/Kaggle free** hoặc 1× GPU rẻ, vài giờ, vài USD.

---

## Checklist nhanh trước khi bắt tay
- [ ] Chốt **phạm vi hẹp** (modality nào? tác vụ nào?).
- [ ] Backbone: **Gemma 4 E4B** (đã chọn — có grounding/pointing sẵn) → đỡ phải dạy từ đầu.
- [ ] Chuẩn bị **dữ liệu vùng** (giữ `<box>` chuẩn); nếu cần tiếng Việt thì dịch + lọc.
- [ ] Dùng **QLoRA**, ước lượng VRAM/giờ/chi phí trước.
- [ ] Đánh giá bằng **IoU + BERTScore + chỉ số lâm sàng**, không chỉ nhìn loss.
- [ ] Chuẩn bị câu trả lời phản biện: *"không nhằm vượt MedRegA về độ phủ, mà chứng minh ý tưởng region-centric khả thi ở quy mô tiếp cận được."*

---

*Ghi chú: Đây là phần nhận xét/phản biện của nhóm dựa trên phân tích bài MedRegA (ICLR 2025), không phải tuyên bố từ bài gốc.*
