# AGENTS.md — đọc trước khi làm việc trong repo này

> ⚠️ **ĐẦU MỖI SESSION:** nếu CHƯA đọc các file dưới đây, ĐỌC chúng trước để nắm ngữ cảnh/quyết định đã chốt.
> Đừng làm lại từ đầu hay đề xuất lại cái đã quyết — lịch sử + lý do nằm trong các file này.

## Dự án
Seminar về paper **MedRegA** (ICLR 2025, medical MLLM định vị vùng, box dạng text
`<ref>liver tumor</ref><box>[[x1,y1,x2,y2]]</box>`, toạ độ [0,1000)). Fine-tune **Gemma 4 E4B**
(`google/gemma-4-E4B-it`) định vị **u gan** trên **LiTS** (CT). Có hướng cải tiến "Hướng-1"
(selective prediction / abstention). Chạy trên Colab A100.

## 📌 FILE QUAN TRỌNG — đọc theo thứ tự này
1. **`seminar/code/plans/TODO.md`** — checklist hành động HIỆN TẠI (việc còn lại, ưu tiên, đã chốt gì).
2. **`seminar/memo/worklog.md`** — NHẬT KÝ đầy đủ: kết quả từng lần chạy, lỗi+cách sửa, mọi quyết định + lý do. Đọc để biết "đã làm gì rồi".
3. **`seminar/code/plans/methodology_todo.md`** — quyết định METHODOLOGY (per-patient eval, multi-focal, baseline...) kèm LÝ DO.
4. **`seminar/code/plans/results_audit.md`** — audit độ tin cậy kết quả gemma4_v2 + danh sách BUG cần sửa.
5. **`seminar/memo/plan_cai_tien.md`** — plan cải tiến vòng 2 (data/augment/loss/metric).

## File code chính
- **`seminar/code/medrega_finetune.ipynb`** — NOTEBOOK CHÍNH (setup→data→train→eval). Chạy trên Colab.
- `seminar/code/prep_data_multi_v2.py` — tạo data (cắt lát CT → PNG + box). LiTS cache ở `seminar/code/data/`.
- `seminar/code_tac_gia/MedRegA/` — code GỐC của tác giả (đối chiếu metric: `src/eval/regt2r/evaluator_reg.py`).

## Quy ước làm việc (QUAN TRỌNG)
- **Trả lời bằng TIẾNG VIỆT, giải thích MỌI thuật ngữ bằng lời thường** (user là sinh viên, yêu cầu rõ điều này).
- **KHÔNG tự ý train/chạy nặng hay đổi hướng lớn** — bàn + để user quyết.
- User thích **brainstorm kỹ + dùng subagent/panel phản biện** trước khi code.
- Mọi metric báo **n theo BỆNH NHÂN** (không theo lát — pseudoreplication).

## Quyết định đã CHỐT (đừng đề xuất lại)
- Eval = ĐA CẤP per-patient (giữ overlap), KHÔNG phải binary "có u/không". KHÔNG dùng FROC full (để future work).
- Bỏ "điểm công bằng" tự chế → dùng metric chuẩn paper (mean IoU + acc@0.25/0.5/0.75) + FP/recall.
- GIoU loss: ĐỂ SAU (cần kiểm tokenizer Gemma per-digit + test).
- Đang chờ làm: sửa multi-focal (35% lát box rác) + W_POS=3 + sửa bug eval (logprob/AUROC) + baseline zero-shot. Xem TODO.md.

## ⚠️ Bảo mật
Trong chat từng lộ HF token + Kaggle token → user cần thu hồi/tạo lại. Đừng in lại token.
