# HƯỚNG DẪN CHẠY — Fine-tune Gemma 4 định vị u gan (MedRegA)

> Notebook fine-tune **Gemma 4 E4B** định vị khối u gan trên ảnh CT (LiTS), kèm **selective prediction**
> (model biết im khi không chắc). Có **3 chế độ chạy** tuỳ nhu cầu — xem mục 4.

---

## 1. Chuẩn bị thư mục Google Drive (CỦA BẠN)
Tạo cấu trúc trong `Drive của tôi / Colab Notebooks /`:
```
Colab Notebooks/
└── medrega/
    ├── data_multi_v3/
    │   └── data_liver_multi_v3.zip          ← data (notebook tự giải nén)
    └── model/checkpoints/
        ├── gemma4_v3/                        ← (CHỈ cần cho Mode B/C) checkpoint đã train
        └── eval_runs/
            └── eval_pred_gemma4_v3_...json   ← (CHỈ cần cho Mode C) kết quả dự đoán
```
> Copy nội dung từ folder được chia sẻ vào đúng cấu trúc trên trong Drive của bạn.
> Folder `data/`, `checkpoints/` khác notebook **tự tạo** khi chạy.

## 2. Hugging Face token (BẮT BUỘC cho Mode A & B, KHÔNG cần Mode C)
- Đồng ý license: https://huggingface.co/google/gemma-4-E4B-it → **"Agree and access"**.
- Tạo token: https://huggingface.co/settings/tokens (read).
- Đặt token (chọn 1):
  - **Colab Secret** (khuyên): notebook → 🔑 (cột trái) → Add secret, Name `HF_TOKEN`, dán token, bật Notebook access.
  - **File:** tạo `medrega/secrets.env`, nội dung 1 dòng: `HF_TOKEN=hf_xxxxx`
> ⚠️ Dùng token **của chính bạn**.

## 3. Mở notebook
Upload `medrega_finetune.ipynb` lên Colab (hoặc mở từ Drive).

---

## 4. CHỌN 1 TRONG 3 CHẾ ĐỘ CHẠY

### 🟢 Mode A — TRAIN từ đầu + EVAL (đầy đủ)
> Train model mới rồi đánh giá. **Cần GPU A100** (Runtime → Change runtime type → A100). **~2 giờ.**
1. Runtime → **Run all** (chạy hết từ trên xuống).
2. Cell `[TÙY CHỌN] Nạp model CŨ` để mặc định `RUN_OLD_CKPT = False` → tự bỏ qua, train model mới.
3. (Tuỳ chọn) đổi tên lần train: cell **cấu hình** (`cfg`), sửa `RUN_NAME = "gemma4_v3"` → tên khác để không đè.
- Output: model `model/checkpoints/<RUN_NAME>/` + JSON `model/checkpoints/eval_runs/eval_pred_<...>.json`.

### 🟡 Mode B — EVAL có sẵn checkpoint (KHÔNG train)
> Dùng model `gemma4_v3` đã train, chỉ chạy đánh giá. **Cần A100.** **~1.5 giờ.**
1. Đảm bảo có `model/checkpoints/gemma4_v3/` trong Drive.
2. Trong cell `[TÙY CHỌN] Nạp model CŨ`: đặt **`RUN_OLD_CKPT = True`**.
3. **KHÔNG chạy cell `TRAIN`** (cell `# === TRAIN: ...`). Chạy các cell còn lại theo thứ tự
   (env → cfg → mount → getdata → split → load → fmt → util → **[nạp model cũ]** → diag → eval).
- Output: JSON kết quả mới trong `eval_runs/`.

### 🔵 Mode C — CHỈ XEM KẾT QUẢ từ JSON có sẵn (KHÔNG train, KHÔNG predict, KHÔNG cần GPU)
> Nạp file `eval_pred_*.json` đã có → tính lại metric + vẽ biểu đồ. **Chạy vài giây, CPU cũng được.**
1. Runtime → CPU (hoặc bất kỳ — không cần GPU).
2. Chỉ chạy **4 cell** này theo thứ tự (bỏ qua tất cả cell khác):
   - `# === Hàm tiện ích — parse_box + IoU ...` (cell **util**)
   - `# === [TÙY CHỌN — Mode C] Nạp JSON ...` → **đặt** `LOAD_JSON_PATH = "đường dẫn tới file eval_pred_....json"`
   - `# === [EVAL METRICS] ...`
   - `# === [EVAL HƯỚNG-1] ...`
3. Xong → in metric + biểu đồ risk-coverage ngay.

| | Mode A | Mode B | Mode C |
|---|--------|--------|--------|
| Train? | ✅ | ❌ | ❌ |
| Predict (chạy model)? | ✅ | ✅ | ❌ |
| Cần GPU A100? | ✅ | ✅ | ❌ (CPU OK) |
| Cần HF token? | ✅ | ✅ | ❌ |
| Cần checkpoint `gemma4_v3`? | ❌ | ✅ | ❌ |
| Cần file JSON? | ❌ | ❌ | ✅ |
| Thời gian | ~2h | ~1.5h | vài giây |

---

## 5. Kết quả
- **Metric in ra** (2 cell cuối): mean-IoU per-patient + recall/precision@IoU + risk-coverage + 3 tín hiệu tự tin.
- **JSON** (Mode A/B): `model/checkpoints/eval_runs/eval_pred_<RUN_NAME>_<timestamp>.json` — **mỗi lần chạy 1 file, không ghi đè**.

**Số tham khảo (lần chạy gốc):** per-patient IoU ~**0.32** (CI [0.24, 0.42]); FP (bịa u) ~**1%**;
tín hiệu **logprob** dự báo độ đúng tốt (Spearman ~0.96); gate đẩy IoU **0.32 → 0.57** khi chỉ trả lời ca chắc.

---

## Troubleshooting
| Lỗi | Cách xử |
|-----|---------|
| `401 / gated repo` (Mode A/B) | Chưa Agree license Gemma 4, hoặc token sai |
| `FileNotFoundError ...zip` | Chưa bỏ `data_liver_multi_v3.zip` đúng `medrega/data_multi_v3/` |
| OOM / CUDA out of memory | Không phải A100 → đổi runtime sang A100 |
| `bitsandbytes` import error | Chạy lại cell cài thư viện → **Restart runtime** → chạy lại |
| Mode C báo `name 'rows_eval' is not defined` | Chưa đặt `LOAD_JSON_PATH` (đang rỗng) hoặc đường dẫn sai |
| Mode C báo `match_boxes is not defined` | Chưa chạy cell **util** trước |

Có gì kẹt cứ hỏi người chia sẻ notebook.
