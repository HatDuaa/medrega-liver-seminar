# HƯỚNG DẪN CHẠY — Fine-tune Gemma 4 định vị u gan (MedRegA)

> Notebook fine-tune **Gemma 4 E4B** định vị khối u gan trên ảnh CT (LiTS), kèm **selective prediction**
> (model biết im khi không chắc). Chạy trên **Google Colab A100**.

---

## 0. Yêu cầu
- **Google Colab Pro** (cần GPU **A100 40GB** — bf16. T4 free KHÔNG đủ).
- **Tài khoản Hugging Face** + đã **đồng ý license Gemma 4**:
  vào https://huggingface.co/google/gemma-4-E4B-it → bấm **"Agree and access"**.
- **HF token** của bạn: https://huggingface.co/settings/tokens → tạo token (read) → copy.

---

## 1. Chuẩn bị thư mục trên Google Drive của BẠN
Tạo đúng cấu trúc sau trong `Drive của tôi / Colab Notebooks /`:

```
Colab Notebooks/
└── medrega/
    └── data_multi_v3/
        └── data_liver_multi_v3.zip      ← copy file zip vào đây (KHÔNG cần giải nén)
```

- Tạo folder `medrega`, trong đó folder `data_multi_v3`, **bỏ `data_liver_multi_v3.zip` vào** (notebook tự giải nén).
- Các folder `model/checkpoints/`, `data/` notebook **tự tạo** khi chạy — không cần làm tay.

## 2. Đặt HF token (chọn 1 trong 2 cách)
**Cách A (khuyên — Colab Secret):**
- Mở notebook trên Colab → bấm 🔑 (Secrets, cột trái) → **Add new secret**:
  - Name: `HF_TOKEN`
  - Value: dán token của bạn
  - Bật "Notebook access".

**Cách B (file):** tạo file `medrega/secrets.env` trên Drive, nội dung 1 dòng:
```
HF_TOKEN=hf_xxxxxxxxxxxxxxxxx
```

> ⚠️ Dùng **token của CHÍNH BẠN**, đừng xin token người khác.

## 3. Mở notebook & chọn GPU
- Upload `medrega_finetune.ipynb` lên Drive (hoặc mở trực tiếp trong Colab).
- Menu **Runtime → Change runtime type → A100 GPU**.

## 4. Chạy
Chạy **lần lượt từ trên xuống** (Runtime → Run all cũng được). Mốc thời gian:
- Cài thư viện + tải model Gemma 4 (~16GB): **~5-10 phút** (lần đầu).
- **Train** (5 epoch): **~30 phút**.
- **Eval** (predict test + cal, mỗi ảnh đoán 7 lần cho 3 tín hiệu tự tin): **~1.5 giờ**.
→ Tổng **~2 giờ**. Có thể treo máy.

### Kiểm tra khi chạy:
- Cell `getdata` phải in `jsonl: 1211` (data đã giải nén đúng).
- Cell `load` in `Đã tải model BF16` (token OK). Nếu lỗi **401/gated** → chưa đồng ý license hoặc token sai.
- Cell `train` in `BEST mới (eval_loss=...)` giảm dần.

## 5. Kết quả ở đâu
- **Metric in ra** ở 2 cell cuối: mean-IoU per-patient + recall/precision + risk-coverage + 3 tín hiệu.
- **File JSON** (dự đoán thô) tự lưu vào `medrega/model/checkpoints/eval_runs/eval_pred_<tên>_<thời gian>.json`
  — **tên có timestamp nên mỗi lần chạy 1 file, không ghi đè**.
- **Model** lưu ở `medrega/model/checkpoints/<RUN_NAME>/` (mặc định `gemma4_v3`).

**Số tham khảo (lần chạy gốc):** per-patient IoU ~**0.32** (CI [0.24, 0.42]), FP (bịa u) ~**1%**,
tín hiệu **logprob** dự báo độ đúng tốt (Spearman ~0.96), gate đẩy IoU 0.32→0.57 khi chỉ trả lời ca chắc.

## 6. (Tùy chọn) Đặt tên lần chạy riêng
Trong cell `cfg`, đổi:
```python
RUN_NAME = "gemma4_v3"   # đổi thành tên khác (vd "gemma4_test1") để không đè checkpoint cũ
```

## 7. (Tùy chọn) Eval mà KHÔNG train lại
Nếu có sẵn checkpoint `gemma4_v3` (copy vào `medrega/model/checkpoints/gemma4_v3/`):
- Trong cell `[TÙY CHỌN] Nạp model CŨ`, đặt `RUN_OLD_CKPT = True`.
- **Bỏ qua (không chạy) cell `train`** → chạy thẳng tới eval.

---

## Troubleshooting
| Lỗi | Cách xử |
|-----|---------|
| `401 / gated repo` | Chưa Agree license Gemma 4, hoặc token sai/thiếu quyền |
| `FileNotFoundError ...zip` | Chưa bỏ `data_liver_multi_v3.zip` đúng `medrega/data_multi_v3/` |
| OOM / CUDA out of memory | Không phải A100 (đang T4?) → đổi runtime sang A100 |
| `bitsandbytes` import error | Chạy lại cell cài thư viện rồi **Restart runtime**, chạy lại |

Có gì kẹt cứ hỏi người chia sẻ notebook này.
