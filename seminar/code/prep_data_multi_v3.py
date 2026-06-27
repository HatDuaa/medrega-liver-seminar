# prep_data_multi_v3.py — MULTI-BOX: mỗi ổ u 1 box (sửa lỗi đa ổ 35%), CHẠY LOCAL
# Khác v2: 1 lát đa ổ -> NHIỀU box (1/ổ) thay vì 1 box bao trùm rác. Lọc ổ < MIN_LESION_PX.
# Output: ./data/data_liver_multi_v3/
import os, re, glob, json
import numpy as np
from PIL import Image
from scipy import ndimage

# ----------------------- CONFIG -----------------------
DATA_ROOT     = "./data"
OUT_DIR       = os.path.join(DATA_ROOT, "data_liver_multi_v3")
N_POS_SLICES  = 5
N_LARGEST     = 2
N_NEG_SLICES  = 5
MIN_LESION_PX = 30        # bỏ ổ < 30px (nhiễu / u gần vô hình)
WL, WW        = 40, 400
COORD_SCALE   = 1000
SEED          = 0
# ------------------------------------------------------
os.makedirs(os.path.join(OUT_DIR, "images"), exist_ok=True)
rng = np.random.default_rng(SEED)


def window(x):
    lo, hi = WL - WW / 2, WL + WW / 2
    return ((np.clip(x, lo, hi) - lo) / (hi - lo) * 255).astype(np.uint8)


def slice_to_boxes(mask, W, H):
    """mask = seg[:,:,z]==2. Tách từng ổ rời -> list box [x1,y1,x2,y2] thang [0,1000).
       Bỏ ổ < MIN_LESION_PX. Sort theo (y,x) để thứ tự ổn định khi train."""
    lbl, n = ndimage.label(mask)
    boxes = []
    for k in range(1, n + 1):
        ys, xs = np.where(lbl == k)
        if len(xs) < MIN_LESION_PX:
            continue
        boxes.append([int(xs.min() / W * COORD_SCALE), int(ys.min() / H * COORD_SCALE),
                      int(xs.max() / W * COORD_SCALE), int(ys.max() / H * COORD_SCALE)])
    boxes.sort(key=lambda b: (b[1], b[0]))
    return boxes


def make_record(fn, gt_boxes, label, pid):
    q = "Please detect the liver tumor in this CT image and give its bounding box."
    if gt_boxes:
        inner = ", ".join(f"[{b[0]}, {b[1]}, {b[2]}, {b[3]}]" for b in gt_boxes)
        a = f"<ref>liver tumor</ref><box>[{inner}]</box>"
    else:
        a = "No liver tumor is found."
    return {"id": f"{pid}_{label}_{os.path.basename(fn)}", "patient_id": int(pid),
            "image_path": fn, "question": q, "gt_boxes": gt_boxes, "label": label, "modality": "ct_liver",
            "conversations": [{"from": "human", "value": "<image>\n" + q},
                              {"from": "gpt", "value": a}]}


def main():
    import kagglehub, nibabel as nib
    os.environ.setdefault("KAGGLEHUB_CACHE", os.path.abspath(DATA_ROOT))
    roots = [kagglehub.dataset_download("andrewmvd/liver-tumor-segmentation"),
             kagglehub.dataset_download("andrewmvd/liver-tumor-segmentation-part-2")]
    seg_paths, vol_paths = {}, {}
    for r in roots:
        for p in glob.glob(os.path.join(r, "**", "segmentation-*.nii*"), recursive=True):
            seg_paths[int(re.search(r"segmentation-(\d+)", p).group(1))] = p
        for p in glob.glob(os.path.join(r, "**", "volume-*.nii*"), recursive=True):
            vol_paths[int(re.search(r"volume-(\d+)", p).group(1))] = p
    print("So ca co nhan:", len(seg_paths), "| co volume:", len(vol_paths))

    rows = []
    n = len(seg_paths)
    n_skip_empty = 0
    box_per_slice = {}
    for k, pid in enumerate(sorted(seg_paths)):
        if pid not in vol_paths:
            continue
        seg = np.asarray(nib.load(seg_paths[pid]).dataobj)
        vimg = nib.load(vol_paths[pid])
        H, W, D = seg.shape
        tumor = (seg == 2).reshape(-1, D).sum(0)
        liver = (seg == 1).reshape(-1, D).sum(0)

        def _save(z, fn):
            Image.fromarray(window(np.asarray(vimg.dataobj[:, :, z]))).save(os.path.join(OUT_DIR, fn))

        # DƯƠNG: 2 lát u to nhất + 3 lát ngẫu nhiên (có u)
        tumor_z = [int(z) for z in range(D) if tumor[z] > 0]
        if tumor_z:
            by_size = sorted(tumor_z, key=lambda z: -tumor[z])
            pick = by_size[:N_LARGEST]
            rest = [z for z in tumor_z if z not in pick]
            if rest:
                rng.shuffle(rest)
                pick += rest[:max(0, N_POS_SLICES - N_LARGEST)]
            for z in sorted(set(pick)):
                boxes = slice_to_boxes(seg[:, :, z] == 2, W, H)
                if not boxes:                       # toàn ổ < MIN_LESION_PX -> bỏ lát (noise)
                    n_skip_empty += 1
                    continue
                fn = f"images/liver_{pid:03d}_pos_z{z}.png"
                _save(z, fn)
                rows.append(make_record(fn, boxes, "tumor", pid))
                box_per_slice[len(boxes)] = box_per_slice.get(len(boxes), 0) + 1

        # ÂM: lát gan-không-u
        cand = np.where((tumor == 0) & (liver > 0))[0]
        if len(cand):
            sel = cand[np.linspace(0, len(cand) - 1, min(N_NEG_SLICES, len(cand))).astype(int)]
            for z in sorted(set(int(z) for z in sel)):
                fn = f"images/liver_{pid:03d}_neg_z{z}.png"
                _save(z, fn)
                rows.append(make_record(fn, [], "none", pid))

        del seg
        print(f"  [{k+1}/{n}] pid {pid}", flush=True)

    with open(os.path.join(OUT_DIR, "data.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_pos = sum(r["label"] == "tumor" for r in rows)
    multi = sum(k * v for k, v in box_per_slice.items() if k >= 2)
    print("=" * 55)
    print("Tong mau:", len(rows), "| duong:", n_pos, "| am:", sum(r["label"] == "none" for r in rows),
          "| benh nhan:", len({r["patient_id"] for r in rows}))
    print("Box/lat (duong):", dict(sorted(box_per_slice.items())))
    print(f"Lat da-o (>=2 box): {sum(v for k,v in box_per_slice.items() if k>=2)}/{n_pos} "
          f"({100*sum(v for k,v in box_per_slice.items() if k>=2)/max(n_pos,1):.1f}%)")
    print("Lat bo do toan o nho:", n_skip_empty)
    print("Luu:", OUT_DIR)


if __name__ == "__main__":
    main()
