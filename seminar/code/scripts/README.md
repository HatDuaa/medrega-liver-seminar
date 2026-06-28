# scripts/ — phân tích kết quả eval (chạy LOCAL, KHÔNG cần GPU)

Phân tích file `eval_pred_*.json` (xuất từ cell PREDICT trong notebook) ngay trên máy,
không cần Colab/model. Dùng để soi số + lặp nhanh.

## analyze_eval.py
**Cách dùng:**
1. Tải `eval_pred_gemma4_v3_*.json` từ Drive (`model/checkpoints/eval_runs/`) về **folder này** (`scripts/`).
2. Chạy:
   ```
   python analyze_eval.py eval_pred_gemma4_v3_xxxx.json
   ```
   (không truyền path → tự tìm `eval_pred_*.json` mới nhất trong folder)

**In ra:**
- **METRICS** — recall/precision@IoU(0.1/0.25/0.5/0.75), mean-IoU, per-patient + bootstrap CI, phân tầng số ổ, FP ca âm.
- **RECALL theo KÍCH THƯỚC u** — diện tích GT box (proxy độ to/rõ) → recall nhỏ/vừa/lớn.
- **HƯỚNG-1** — 3 tín hiệu (cal chọn, flip dấu), risk-coverage, conformal.
- Lưu chart `risk_coverage.png`.

**Yêu cầu:** numpy, scipy, scikit-learn, matplotlib (đã có sẵn nếu dùng venv của repo).
