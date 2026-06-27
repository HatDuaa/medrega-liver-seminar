# KẾ HOẠCH CÁC BƯỚC CẦN LÀM

> File theo dõi việc cần làm. Bám theo [huong_cai_tien_MedRegA.md](huong_cai_tien_MedRegA.md), [cai_tien_SOTA.md](cai_tien_SOTA.md), [luu_y_va_yeu_diem.md](luu_y_va_yeu_diem.md).
> Tick `[x]` khi xong.

## Chốt nhanh (đã quyết)
- **Backbone:** Gemma 4 E4B (nhỏ, mới, có grounding sẵn). Nếu thiếu tham số → nâng Gemma 4 26B.
- **Trục chính:** Hướng 1 — "dạy AI biết khi nào nên im lặng" (selective prediction / abstention).
- **Phụ (làm sau nếu dư thời gian):** Hướng 2 (kiểm tra AI có nhìn đúng vùng), Hướng 3 (sửa thước chấm điểm).
- **Phần cứng:** chạy trên máy remote (SSH), có 4090 → đủ, miễn phí.
- **Cách train:** QLoRA (nhẹ), không tái huấn luyện toàn bộ.

---

## GIAI ĐOẠN 0 — Chuẩn bị môi trường
- [ ] SSH vào máy remote, chạy `nvidia-smi` xác nhận GPU + VRAM.
- [ ] Cài `tmux` (để train không chết khi rớt SSH); tạo phiên làm việc.
- [ ] Tạo môi trường Python (venv/conda) + cài: `torch`, `transformers`, `accelerate`, `peft`, `bitsandbytes`, `pillow`, `numpy/scipy/scikit-learn/matplotlib`.
- [ ] (Khuyến nghị) Dùng VS Code Remote-SSH để mở/chạy notebook trực tiếp trên remote.
- [ ] Copy folder `code/` lên remote (`scp`/`rsync`).

## GIAI ĐOẠN 1 — Chạy được base model (Gemma 4 E4B)
- [ ] Xin quyền truy cập + tải Gemma 4 E4B (điền `MODEL_ID` thật).
- [ ] Chạy thử inference 1 ảnh: cho model xuất `<box>` để chắc nó làm grounding được.
- [ ] Viết hàm `predict()` (trả box + logprob token toạ độ) và `self_confidence()` cho notebook.
- [ ] Đổi `USE_MOCK = False` trong notebook, xác nhận nối model thật chạy thông.

## GIAI ĐOẠN 2 — Chuẩn bị dữ liệu vùng y khoa
- [ ] Chọn phạm vi HẸP: 1 phương thức (vd X-quang ngực) + 1–2 tác vụ (Text→Region / Grounded Report).
- [ ] Lấy subset có sẵn box: **MIMIC-CXR + box Chest ImaGenome** (tiếng Anh, có ground truth).
- [ ] Định dạng mỗi mẫu: ảnh + câu hỏi + `gt_box` (toạ độ chuẩn hoá [0,1000)).
- [ ] Tách tập calibration nhỏ (để đặt ngưỡng) + tập test.
- [ ] (Tùy chọn) Chuẩn bị vài nghìn mẫu cho QLoRA nếu cần fine-tune.

## GIAI ĐOẠN 3 — TRỤC CHÍNH: Hướng 1 (selective prediction)
- [ ] Chạy notebook ở chế độ MOCK để hiểu rõ luồng (đã có sẵn).
- [ ] **Bước cổng (bắt buộc):** đo 3 tín hiệu tin cậy (logprob / nhất quán không gian khi sample N=5 / hỏi thẳng độ tự tin) và xem cái nào tương quan với IoU thật (Spearman + AUROC).
  - [ ] Nếu có tín hiệu tốt → đi tiếp. Nếu cả 3 yếu → **ghi nhận negative result** (vẫn là đóng góp), dừng đúng lúc.
- [ ] Vẽ **đường risk–coverage** + tính **selective IoU** (trả lời ít hơn nhưng chắc hơn).
- [ ] Áp **conformal theo từng phương thức** để giữ coverage guarantee.
- [ ] Định nghĩa + đo **cost-aware selective IoU** (phạt nặng khi định vị bừa lúc sai).
- [ ] (Tùy chọn) QLoRA fine-tune nhẹ nếu muốn cải thiện base trước khi đo.
- [ ] So sánh với "abstention ngầm" sẵn có của MedRegA (nó sinh ít box hơn khi không chắc).

## GIAI ĐOẠN 4 — Đánh giá & viết kết quả
- [ ] Tổng hợp số liệu (bảng tương quan, biểu đồ risk–coverage).
- [ ] Viết nhận xét: tín hiệu nào dùng được, abstention giúp giảm rủi ro bao nhiêu.
- [ ] Nêu rõ: đây là **proof-of-concept trên base nhỏ**, không so kè bảng SOTA.

## GIAI ĐOẠN 5 — (NẾU DƯ THỜI GIAN) Hướng phụ
- [ ] **Hướng 2 — Kiểm định nhân quả Regional CoT:** chạy 4 nhánh (no-box / model tự detect / box đúng / box ngẫu nhiên), so điểm để biết AI có thật sự "dùng" vùng không. (Thuần inference, rẻ.)
- [ ] **Hướng 3 — Meta-evaluation metric:** dùng thước chấm theo nghĩa (RadFact/GREEN/RaTEScore) + kiểm tra thước nào đáng tin cho tiếng Trung / CT-MRI; probe lỗi đảo trái-phải.

## GIAI ĐOẠN 6 — Báo cáo & slide
- [ ] Gộp phần phân tích + hạn chế + Hướng 1 vào báo cáo LaTeX (`baocao_dich` hoặc báo cáo nhóm).
- [ ] Làm slide: vấn đề → ý tưởng (im lặng khi không chắc) → cách làm → kết quả → kết luận.
- [ ] Chuẩn bị Q&A phản biện (xem `luu_y_va_yeu_diem.md`).

---

## ⚠️ Nhắc liên tục (từ luu_y_va_yeu_diem.md)
- [ ] **Verify mọi trích dẫn SOTA** trước khi đưa vào báo cáo (có vài arXiv ID đáng nghi / năm tương lai; MMedPO là ICML 2025).
- [ ] Giữ **phạm vi hẹp** — đừng ôm 8 phương thức + song ngữ + mọi tác vụ.
- [ ] Khi dịch dữ liệu (nếu làm song ngữ): **giữ nguyên số trong `<box>`**, dùng từ điển thuật ngữ, back-translation lọc.
- [ ] QLoRA trên Linux remote chạy native — không lo vấn đề Windows.
