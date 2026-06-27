# KẾ HOẠCH METHODOLOGY — eval & data (note để làm sau)

> Nguồn: 2 panel đa quan điểm (per-slice vs per-patient) + 1 audit soi lỗ hổng panel + brainstorm với chủ dự án (2026-06-27).
> Bối cảnh: seminar SV về MedRegA, fine-tune Gemma 4 E4B định vị u gan trên LiTS. Thời gian hạn chế → ưu tiên cái rẻ + cao giá trị.
> Đã có sẵn: data v2 (1238 mẫu, 5 lát dương + 5 âm/bệnh nhân), augment on-the-fly, WeightedTrainer (w_pos=2), eval per-slice + per-patient sơ khai, Hướng-1 (selective prediction/conformal).

---

## 🔴 PHẢI LÀM (rẻ + cao giá trị)

### 1. Sửa box ĐA Ổ (multi-focal) — lỗi data nặng nhất
- **Làm gì:** lát có ≥2 khối u rời nhau → KHÔNG dùng 1 box bao min/max tất cả pixel u nữa (vì box đó bao trùm cả gan lành giữa 2 khối = nhãn rác). Tách từng ổ bằng `scipy.ndimage.label` trên `seg==2`.
- **Tại sao:** đã ĐẾM TRÊN DATA THẬT → **207/585 lát dương (35.4%) bị đa ổ** (có lát tới 20 ổ). Trên 1/3 nhãn dương đang sai → đo IoU vô nghĩa. Lại đúng vào đóng góp multi-region của MedRegA mà mình đang ép thành 1-box.
- **2 cách (chốt khi làm):**
  - **NHANH:** mỗi lát đa ổ chỉ lấy box của **ổ TO NHẤT**, bỏ ổ nhỏ. Giữ pipeline 1-box, sửa ít. Nhược: bỏ qua u phụ.
  - **CHUẨN:** xuất **nhiều box (1/ổ)** → đúng tinh thần MedRegA. Phải sửa: (a) đáp án train = nhiều `<box>`, (b) eval = matching nhiều box (Hungarian như evaluator gốc). Xịn hơn, nhiều việc hơn.
- **Code đã có:** đoạn đếm đa ổ (connected-components) đã chạy được — mở rộng thành sinh box/ổ.

### 2. BASELINE Gemma 4 zero-shot (CHƯA fine-tune)
- **Làm gì:** load Gemma 4 **gốc, chưa train** → chạy ĐÚNG pipeline eval per-patient → trên ĐÚNG test set v2 → so với bản fine-tune.
- **Tại sao:** muốn nói "fine-tune giúp cải tiến" thì PHẢI có cột "trước khi train". Thiếu = không chứng minh được gì.
- **Lưu ý:** file baseline CŨ (gemma-3n + data_liver 249) KHÔNG dùng được — khác model + khác data + khác metric ("táo vs cam"). Phải chạy lại cho ĐÚNG Gemma 4 + ĐÚNG test set + ĐÚNG metric.
- **Rẻ:** chỉ inference, KHÔNG train.

### 3. Pipeline EVAL per-patient (ý chủ dự án — đã verify ĐÚNG)
- **Làm gì:** THÊM 1 pipeline eval, đơn vị độc lập = **bệnh nhân** (giữ pipeline per-slice hiện tại làm chi tiết). Mỗi bệnh nhân chấm CẢ:
  - **Phát hiện (dương/âm):** model có nói "có u" trên ≥1 lát không.
  - **Overlap (localization):** IoU trung bình các lát của bệnh nhân đó → 1 số/bệnh nhân.
- **Tại sao:** per-slice IoU bị **pseudoreplication** (5 lát/bệnh nhân giống hệt → đếm 1 khối u nhiều lần → tin tưởng giả). Đơn vị độc lập thật = bệnh nhân (~13 ca dương test). Panel TRƯỚC chê ý này "sai 40%" nhưng AUDIT xác nhận đó là **đánh bù nhìn** — panel cãi bản "binary có/không" mà chủ dự án KHÔNG đề xuất; ý thật (giữ overlap) gần như TRÙNG mục (B) panel tự đề xuất → **ý chủ dự án đúng**.
- **Báo cáo:** per-patient = con số CHÍNH để kết luận; per-slice tụt xuống "phân tích chi tiết", KHÔNG dùng khoe độ tin cậy.

---

## 🟡 NÊN LÀM (nếu kịp)

### 4. Phân tầng overlap theo KÍCH THƯỚC u (đừng vứt lát nhỏ)
- **Làm gì:** báo IoU riêng theo u to / vừa / nhỏ, thay vì 1 số gộp HOẶC bỏ hẳn lát nhỏ.
- **Tại sao:** lát u-vài-pixel kéo IoU xuống oan (label noise), NHƯNG bỏ hẳn = ăn gian "chỉ chấm chỗ dễ" + lát nhỏ chính là early HCC lâm sàng cần nhất. Phân tầng = vừa trung thực vừa có thông tin (cho thấy model mạnh/yếu ở đâu).
- **Lưu ý:** ngưỡng "rõ" định nghĩa từ nhãn thật (GT area), CHỐT TRƯỚC khi xem model đoán (không chỉnh ngưỡng cho đẹp = gian lận). Nên chạy 2-3 ngưỡng cho thấy kết luận không đổi.

---

## ⚪ TẠM BỎ / KHÔNG LÀM (kèm lý do)

### 5. K-fold cross-validation — BỎ
- **Lý do:** k-fold = train 5 lần (5× thời gian). Chủ dự án không có thời gian train đi train lại. → giữ 1 split train/cal/test (cách hiện tại ĐÚNG, không sai). Chỉ cần nói thẳng "test 27 ca, n nhỏ".

### 6. Ablation (bật/tắt augment, w_pos) — BỎ tạm
- **Lý do:** cần train nhiều lần để so → tốn thời gian. Ghi "future work". Cứ xây pipeline trước.

### 7. FROC per-lesion (full) — BỎ, để "future work"
- **Lý do:** cần prep lại TOÀN volume + connected-component 3D + matching lesion xuyên lát. Audit chỉ ra panel **over-engineer**: FROC trên ~13 ca dương CŨNG CI rộng → không mạnh hơn per-patient-aggregate, chỉ khác trục đo. Tốn công không tương xứng seminar. Hạ xuống slide "hướng mở rộng".

### 8. Error bar (khoảng tin cậy số) — TẠM KHÔNG thêm
- **Lý do:** chủ dự án chọn nói "n nhỏ" bằng lời, chưa thêm khoảng. Chấp nhận được (miễn đừng báo trơ 1 số như thể chính xác). Nếu sau muốn: khoảng đơn-giản-nhất = min–max hoặc ±std của 13 số/bệnh nhân (chỉ mô tả data đã có, KHÔNG cần giả thiết).

---

## 📝 FRAMING / GỌI TÊN ĐÚNG (lúc viết báo cáo)

- **"Specificity":** metric "không bịa u trên 653 lát âm" CHÍNH là specificity trên mấy lát đó — nhưng lát âm lấy từ **chính bệnh nhân CÓ u** (gan bệnh, chưa thấy người khỏe nào). → ĐỪNG ghi "độ đặc hiệu lâm sàng / an toàn với người khỏe". Gọi đúng: **"tỉ lệ không bịa u trên lát không-u của bệnh nhân có u"** (intra-patient slice discrimination). Hiện đang gọi đúng ("bịa u/abstain") → giữ nguyên.
- **Hướng-1 (selective prediction):** conformal trên ~13 ca dương quá yếu → trình bày kèm caveat "n nhỏ", HOẶC neo phần selective vào abstain-trên-lát-âm (n=653, mạnh hơn). Đừng rút kết luận mạnh từ 13 ca.
- **n nhỏ:** mọi metric per-patient nói rõ n = số BỆNH NHÂN (~13 dương / 27 test), không bao giờ báo n_lát làm cỡ mẫu.

---

## Thứ tự đề xuất khi bắt tay
1. Sửa multi-focal (data) → vì nó hỏng nhãn 35%, sửa trước mọi đo đạc.
2. Pipeline eval per-patient (detection + overlap) + phân tầng kích thước.
3. Baseline Gemma 4 zero-shot trên cùng eval.
4. (sau) viết slide với framing trung thực ở trên.
