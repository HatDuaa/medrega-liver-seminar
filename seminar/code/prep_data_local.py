# prep_data_local.py — Chuẩn bị data CHẠY LOCAL (KHÔNG mount Drive)
# - Máy có kagglehub + nibabel + kaggle.json -> TẢI LiTS thật vào ./data và xử lý.
# - Thiếu thứ gì đó (hoặc tải lỗi)           -> fallback DEMO tổng hợp để vẫn chạy/test được.
#
# Cài (để chạy thật):  pip install kagglehub nibabel pillow numpy
# Kaggle token:        ~/.kaggle/kaggle.json  (Kaggle > Settings > API > Create New Token)
#
# Output: ./data/data_liver/data.jsonl + images/*.png ; biến `dataset` (cal/test) split theo bệnh nhân.
import os, re, glob, json, importlib.util
import numpy as np
from PIL import Image

# ----------------------- CONFIG -----------------------
DATA_ROOT   = "./data"
OUT_DIR     = os.path.join(DATA_ROOT, "data_liver")
COORD_SCALE = 1000
SEED        = 0
WL, WW      = 40, 400
N_DEMO      = 8
# ------------------------------------------------------

os.makedirs(DATA_ROOT, exist_ok=True)
os.makedirs(os.path.join(OUT_DIR, "images"), exist_ok=True)
rng = np.random.default_rng(SEED)


def window(x):
    lo, hi = WL - WW / 2, WL + WW / 2
    return ((np.clip(x, lo, hi) - lo) / (hi - lo) * 255).astype(np.uint8)


def mask_to_box(mask, W, H):
    ys, xs = np.where(mask)
    return [int(xs.min() / W * COORD_SCALE), int(ys.min() / H * COORD_SCALE),
            int(xs.max() / W * COORD_SCALE), int(ys.max() / H * COORD_SCALE)]


def make_record(image_path, gt_box, label, pid):
    q = "Please detect the liver tumor in this CT image and give its bounding box."
    a = (f"<ref>liver tumor</ref><box>[[{gt_box[0]}, {gt_box[1]}, {gt_box[2]}, {gt_box[3]}]]</box>"
         if gt_box is not None else "No liver tumor is found.")
    return {"id": f"{pid}_{label}", "patient_id": int(pid), "image_path": image_path,
            "question": q, "gt_box": gt_box, "label": label, "modality": "ct_liver",
            "conversations": [{"from": "human", "value": "<image>\n" + q},
                              {"from": "gpt", "value": a}]}


def process_real():
    """Tải LiTS (CẢ part 1 + part 2 vì andrewmvd tách 2 dataset) + xử lý 3D->2D."""
    import kagglehub, nibabel as nib
    os.environ.setdefault("KAGGLEHUB_CACHE", os.path.abspath(DATA_ROOT))
    roots = [kagglehub.dataset_download("andrewmvd/liver-tumor-segmentation"),
             kagglehub.dataset_download("andrewmvd/liver-tumor-segmentation-part-2")]
    for r in roots:
        print("LiTS root:", r)
    seg_paths, vol_paths = {}, {}
    for r in roots:                          # gộp file từ cả 2 dataset (theo số id)
        for p in glob.glob(os.path.join(r, "**", "segmentation-*.nii*"), recursive=True):
            seg_paths[int(re.search(r"segmentation-(\d+)", p).group(1))] = p
        for p in glob.glob(os.path.join(r, "**", "volume-*.nii*"), recursive=True):
            vol_paths[int(re.search(r"volume-(\d+)", p).group(1))] = p
    print("Số ca có nhãn:", len(seg_paths), "| có volume:", len(vol_paths))
    out = []
    n = len(seg_paths)
    for k, pid in enumerate(sorted(seg_paths)):
        if pid not in vol_paths:
            continue
        # seg: đọc dtype gốc (uint8/int16) -> nhẹ ~8x so với get_fdata (float64)
        seg = np.asarray(nib.load(seg_paths[pid]).dataobj)
        vimg = nib.load(vol_paths[pid])          # LAZY: chỉ đọc lát cần qua dataobj[...]
        H, W, D = seg.shape

        def _save_slice(z, fn):                  # chỉ đọc 1 lát từ volume (không load cả khối)
            Image.fromarray(window(np.asarray(vimg.dataobj[:, :, z]))).save(os.path.join(OUT_DIR, fn))

        tumor = (seg == 2).reshape(-1, D).sum(0)
        liver = (seg == 1).reshape(-1, D).sum(0)
        if tumor.max() > 0:                                  # DƯƠNG: lát u lớn nhất
            z = int(tumor.argmax())
            fn = f"images/liver_{pid:03d}_pos_z{z}.png"
            _save_slice(z, fn)
            out.append(make_record(fn, mask_to_box(seg[:, :, z] == 2, W, H), "tumor", pid))
        cand = np.where((tumor == 0) & (liver > 0))[0]       # ÂM: lát gan không u
        if len(cand):
            z = int(cand[len(cand) // 2])
            fn = f"images/liver_{pid:03d}_neg_z{z}.png"
            _save_slice(z, fn)
            out.append(make_record(fn, None, "none", pid))
        del seg
        print(f"  [{k+1}/{n}] pid {pid} xong", flush=True)
    return out


def process_demo(n=N_DEMO):
    """Sinh dữ liệu DEMO tổng hợp (chỉ numpy + pillow) để test pipeline."""
    H = W = 256
    out = []
    for pid in range(n):
        img = rng.normal(60, 15, (H, W)).astype(float)
        x1, y1 = int(rng.integers(40, 150)), int(rng.integers(40, 150))
        x2, y2 = min(x1 + int(rng.integers(30, 80)), W - 1), min(y1 + int(rng.integers(30, 80)), H - 1)
        img[y1:y2, x1:x2] += 120
        mask = np.zeros((H, W), bool); mask[y1:y2, x1:x2] = True
        fn = f"images/demo_{pid:03d}_pos.png"
        Image.fromarray(window(img)).save(os.path.join(OUT_DIR, fn))
        out.append(make_record(fn, mask_to_box(mask, W, H), "tumor", pid))
        fn2 = f"images/demo_{pid:03d}_neg.png"
        Image.fromarray(window(rng.normal(60, 15, (H, W)).astype(float))).save(os.path.join(OUT_DIR, fn2))
        out.append(make_record(fn2, None, "none", pid))
    return out


# --- Chọn chế độ: ưu tiên THẬT nếu đủ điều kiện, không thì DEMO ---
def _have(mod):
    return importlib.util.find_spec(mod) is not None

def _kaggle_auth():
    home = os.path.expanduser("~/.kaggle")
    return (os.path.exists(os.path.join(home, "kaggle.json"))
            or os.path.exists(os.path.join(home, "access_token"))
            or bool(os.environ.get("KAGGLE_USERNAME"))
            or bool(os.environ.get("KAGGLE_API_TOKEN")))

can_real = _have("kagglehub") and _have("nibabel") and _kaggle_auth()
if can_real:
    try:
        rows, mode = process_real(), "THAT (LiTS)"
    except Exception as e:
        print("[CANH BAO] Che do THAT loi:", repr(e), "-> fallback DEMO")
        rows, mode = process_demo(), "DEMO"
else:
    print("[INFO] Thieu kagglehub/nibabel/kaggle.json -> chay DEMO (may co du thi tu chuyen sang THAT).")
    rows, mode = process_demo(), "DEMO"

# --- Ghi jsonl ---
with open(os.path.join(OUT_DIR, "data.jsonl"), "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# --- Split THEO BỆNH NHÂN (cal 50% / test 50%) ---
pids = sorted({r["patient_id"] for r in rows})
rng2 = np.random.default_rng(SEED); rng2.shuffle(pids)
cut = int(len(pids) * 0.5); calset = set(pids[:cut])
dataset = {"train": [],
           "cal":  [r for r in rows if r["patient_id"] in calset],
           "test": [r for r in rows if r["patient_id"] not in calset]}
DATA_DIR = OUT_DIR

print("=" * 50)
print("Che do:", mode)
print("Tong mau:", len(rows),
      "| duong:", sum(r["label"] == "tumor" for r in rows),
      "| am:", sum(r["label"] == "none" for r in rows))
print("Split:", {k: len(v) for k, v in dataset.items()})
_ov = set(r["patient_id"] for r in dataset["cal"]) & set(r["patient_id"] for r in dataset["test"])
print("Benh nhan trung cal/test (phai rong):", _ov)
if rows:
    print("Vi du record:", json.dumps(rows[0], ensure_ascii=False)[:260])
