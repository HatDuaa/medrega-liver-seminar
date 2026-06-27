# Tổng hợp các trang giá thuê GPU

> Cập nhật: 06/2026. **Giá GPU thay đổi liên tục** (theo cung–cầu, vùng, spot vs on-demand) → luôn mở link gốc xem giá thực tế trước khi thuê. Giá dưới đây là *tham khảo* (USD/giờ, 1 GPU).

---

## 0. Cần bao nhiêu VRAM cho MedRegA (~40B)?

MedRegA ≈ **40 tỷ tham số** (InternViT-6B + Yi-34B). VRAM ≈ **(byte/param) × số tham số + overhead**.

| Độ chính xác | Byte/param | Trọng số cho 40B |
|---|---|---|
| BF16/FP16 (gốc) | 2 | **80 GB** |
| INT8 (8-bit) | 1 | **40 GB** |
| INT4 (4-bit) | 0.5 | **20 GB** |

> Cộng thêm ~20–40% cho **activation + KV cache** (tăng theo độ dài ngữ cảnh × batch; ảnh có thêm visual token).

### VRAM theo tác vụ

| Tác vụ | Cách chạy | VRAM ước tính | GPU tối thiểu thực tế |
|---|---|---|---|
| Inference | BF16 đầy đủ | **~90–100 GB** | 2× 80GB (A100/H100) |
| Inference | INT8 | **~48–55 GB** | 1× 80GB, hoặc 1× 48GB (sát) |
| Inference | INT4 (quantize) | **~24–32 GB** | 1× 24–32GB (RTX 4090 / A100-40GB) |
| Fine-tune **QLoRA** | base 4-bit + adapter | **~40–50 GB** | 1× A100/H100 80GB |
| Fine-tune LoRA | base BF16 + adapter | **~100–120 GB** | 2× 80GB |
| **Full fine-tune** | BF16 + Adam (~16 B/param) | **~640+ GB** | 8–16× 80GB (ZeRO-3) |

**Lưu ý:**
- Riêng trọng số BF16 đã **80GB** → 1× H100 80GB **không đủ** chạy đầy đủ → cần 2 GPU hoặc lượng tử hóa.
- Chạy trên **1 GPU đơn** → bắt buộc **quantize** (INT8 vừa 1×80GB; INT4 ~24–32GB chạy được trên 4090).
- **Colab Free (T4 16GB) / Kaggle (P100 16GB) KHÔNG đủ** cho 40B kể cả INT4 (~24GB) → phải dùng GPU ≥24GB.
- Con số **16× H800** của bài chính là cho **full fine-tune** (~640GB+ sharded qua ZeRO-3).

### Map nhanh sang chỗ thuê

| Kịch bản | Cần GPU | Giá tham khảo | Thuê ở đâu (xem mục dưới) |
|---|---|---|---|
| Chạy thử (INT4) | 1× RTX 4090 / A100-40GB | ~$0.3–0.8/h | Vast.ai, RunPod |
| Inference (INT8) | 1× A100/H100 80GB | ~$1–2.7/h | RunPod, Vast.ai, Spheron |
| Inference BF16 | 2× 80GB | ~$2–6/h | RunPod, Lambda |
| **Fine-tune QLoRA** | 1× A100 80GB | ~$1–2/h (vài USD/lần) | RunPod, Vast.ai |
| Full fine-tune | 8–16× H100/H800 | $30–80/h+ | Lambda, CoreWeave (không khả thi cho seminar) |

---

## 1. Trang so sánh giá (xem ở đây trước cho nhanh)

| Trang | Mô tả | Link |
|---|---|---|
| GPU per Hour | So sánh ~28 nhà cung cấp, lọc theo loại GPU | https://gpuperhour.com/ |
| Spheron Blog | So sánh 15+ provider, cập nhật theo tháng | https://www.spheron.network/blog/gpu-cloud-pricing-comparison-2026/ |
| IntuitionLabs | Chuyên so sánh giá H100 | https://intuitionlabs.ai/articles/h100-rental-prices-cloud-comparison |
| CloudZero | Phân tích chi phí H100 (mua vs thuê) | https://www.cloudzero.com/blog/h100-gpu-cost/ |

---

## 2. Lựa chọn MIỄN PHÍ / rẻ cho sinh viên (nên dùng cho seminar/đồ án)

| Nền tảng | GPU | Hạn mức | Giá | Link |
|---|---|---|---|---|
| **Google Colab (Free)** | T4 (16GB) | ~15–30 giờ GPU/tuần, phiên tối đa 12h | **Miễn phí** | https://colab.research.google.com/ |
| **Kaggle Notebooks** | P100 / T4 (16GB) | **30 giờ GPU/tuần** | **Miễn phí** | https://www.kaggle.com/ |
| Colab Pro | T4/L4, ưu tiên hơn | gói compute units | **$9.99/tháng** | https://colab.research.google.com/signup |
| Colab Pro+ | ưu tiên GPU mạnh | hạn mức cao hơn | **$49.99/tháng** | https://colab.research.google.com/signup |
| Azure for Students | nhiều loại | tín dụng $100/năm | **Miễn phí** (cần email .edu) | https://azure.microsoft.com/free/students/ |

> Mẹo: gộp **Colab (30h) + Kaggle (30h)** = ~60 giờ GPU miễn phí mỗi tuần. Đủ cho demo/inference *model nhỏ*, nhưng **không đủ cho MedRegA 40B** (xem dưới).

### Chi tiết accelerator của Kaggle (đều miễn phí, ~30h GPU/tuần — Kaggle KHÔNG có gói trả phí)

| Lựa chọn | VRAM | Ghi chú |
|---|---|---|
| GPU P100 | 16GB (1 GPU) | HBM2, băng thông cao, nhanh hơn T4 cho 1 GPU |
| **GPU T4 ×2** | **32GB** (2× 16GB) | VRAM tổng cao nhất — nhưng là **2 card rời**, phải shard model |
| TPU v3-8 | (TPU) | Cho JAX/TF |

**Dùng cho MedRegA (40B)?** "32GB" là 2 card 16GB riêng (cần model sharding):
- Inference **INT4** (~24–32GB): ✅ vừa đủ (sát), phải shard qua 2 card, **chậm**.
- Inference INT8 (~48GB) / BF16 (~90GB): ❌ không đủ.
- QLoRA fine-tune (~40–50GB): ❌ không đủ.

➡️ Kaggle (tối đa **T4×2 = 32GB**) chỉ vừa chạy **inference INT4** và chậm; làm nghiêm túc vẫn phải thuê **1× A100 80GB**.

---

## 3. Nhà cung cấp giá rẻ (neocloud / marketplace) — khi cần GPU mạnh

| Nhà cung cấp | A100 80GB | H100 | Ghi chú | Link |
|---|---|---|---|---|
| **Vast.ai** | ~$0.67–1.0/h | ~$1.87/h | Marketplace, rẻ nhất nhưng host biến động | https://vast.ai/ |
| **RunPod** | ~$1.19–1.39/h | ~$1.99/h (PCIe), $2.69/h (SXM) | Tính theo giây, dễ dùng | https://www.runpod.io/pricing |
| **Spheron** | ~$1.07/h (spot $0.60) | ~$1.03/h (spot) – $2.50/h | Giá thấp nhất nhiều thời điểm | https://www.spheron.network/ |
| **Lambda Labs** | ~$1.99/h (40GB) | ~$3.29/h (PCIe) | Ổn định, hướng nghiên cứu | https://lambdalabs.com/service/gpu-cloud |
| **Paperspace** | đa dạng | có | Giao diện thân thiện | https://www.paperspace.com/ |

> "Spot" = giá rẻ nhưng có thể bị ngắt bất ngờ (hợp việc thử nghiệm, không hợp job dài quan trọng).

---

## 4. Hyperscaler (đắt hơn, dùng khi cần hạ tầng doanh nghiệp)

| Nhà cung cấp | H100 (tham khảo) | Link |
|---|---|---|
| AWS (p5) | ~$6.88/h | https://aws.amazon.com/ec2/instance-types/p5/ |
| Google Cloud | tùy cấu hình | https://cloud.google.com/compute/gpus-pricing |
| Azure | ~$12.29/h | https://azure.microsoft.com/pricing/details/virtual-machines/ |
| CoreWeave | cạnh tranh | https://www.coreweave.com/pricing |

---

## 5. Liên hệ với bài MedRegA (để biết quy mô)

- Bài gốc huấn luyện trên **16 GPU NVIDIA H800** → chi phí khổng lồ, **không khả thi** để tái huấn luyện cho seminar.
- Cho seminar, chỉ cần GPU để **chạy thử / inference / fine-tune nhỏ (LoRA)** → **Colab/Kaggle miễn phí** hoặc **RunPod/Vast.ai** vài giờ là đủ.
- Ước lượng nhanh: 1× A100 80GB ~$1/h → fine-tune LoRA nhỏ vài giờ chỉ tốn vài USD.

## 6. Hướng triển khai của nhóm: Gemma 4 E4B (nhỏ → khả thi)

Thay vì đụng tới 40B, nhóm dùng backbone **Gemma 4 E4B** (~4.5B effective / ~8B tổng) rồi **QLoRA** trên dữ liệu vùng y khoa. VRAM nhẹ hơn hẳn:

| Tác vụ với Gemma 4 E4B | VRAM ước tính | Chạy ở đâu |
|---|---|---|
| Inference (INT4/INT8) | ~4–8 GB | **Colab/Kaggle free**, hoặc 1× GPU rẻ |
| **QLoRA fine-tune** | ~8–12 GB | **Colab/Kaggle free** (T4 16GB) hoặc 1× 16–24GB |
| LoRA (base BF16) | ~16–20 GB | 1× 24GB (RTX 4090 / A10) |

➡️ Khác biệt mấu chốt: với Gemma 4 E4B, **fine-tune lọt vào GPU MIỄN PHÍ** (Colab/Kaggle) — không cần thuê như khi đụng MedRegA 40B. Nếu lộ thiếu tham số thì nâng lên **Gemma 4 26B (MoE)**, lúc đó mới cần thuê 1× A100 80GB (~$1/h).

---

## Nguồn tham khảo
- [Spheron — GPU Cloud Pricing 2026](https://www.spheron.network/blog/gpu-cloud-pricing-comparison-2026/)
- [IntuitionLabs — H100 Rental Prices](https://intuitionlabs.ai/articles/h100-rental-prices-cloud-comparison)
- [GPU per Hour — so sánh 28 provider](https://gpuperhour.com/)
- [CloudZero — H100 GPU Cost 2026](https://www.cloudzero.com/blog/h100-gpu-cost/)
- [RunPod Pricing](https://www.runpod.io/pricing)
- [Colab Paid Services Pricing](https://colab.research.google.com/signup)
- [Thunder Compute — Colab alternatives 2026](https://www.thundercompute.com/blog/colab-alternatives-for-cheap-deep-learning-in-2025)

*Lưu ý: giá tổng hợp tại thời điểm 06/2026, chỉ mang tính tham khảo — kiểm tra lại trên trang gốc trước khi thuê.*
