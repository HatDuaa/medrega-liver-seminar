# prep_data_multi_local.py — Cắt NHIỀU lát/bệnh nhân, CHẠY LOCAL (LiTS đã tải ở ./data)
# Output: ./data/data_liver_multi/data.jsonl + images/*.png  (folder MỚI, không đè data_liver cũ)
# Chạy:  PYTHONIOENCODING=utf-8 python prep_data_multi_local.py
import os, re, glob, json
import numpy as np
from PIL import Image

# ----------------------- CONFIG -----------------------
DATA_ROOT    = "./data"
OUT_DIR      = os.path.join(DATA_ROOT, "data_liver_multi")    # FOLDER MỚI
N_POS_SLICES = 5          # số lát DƯƠNG (u lớn nhất) / bệnh nhân
N_NEG_SLICES = 5          # số lát ÂM (gan không u) / bệnh nhân
WL, WW       = 40, 400
COORD_SCALE  = 1000
# ------------------------------------------------------

os.makedirs(os.path.join(OUT_DIR, "images"), exist_ok=True)


def window(x):
    lo, hi = WL - WW / 2, WL + WW / 2
    return ((np.clip(x, lo, hi) - lo) / (hi - lo) * 255).astype(np.uint8)


def mask_to_box(mask, W, H):
    ys, xs = np.where(mask)
    return [int(xs.min() / W * COORD_SCALE), int(ys.min() / H * COORD_SCALE),
            int(xs.max() / W * COORD_SCALE), int(ys.max() / H * COORD_SCALE)]


def make_record(fn, gt_box, label, pid):
    q = "Please detect the liver tumor in this CT image and give its bounding box."
    a = (f"<ref>liver tumor</ref><box>[[{gt_box[0]}, {gt_box[1]}, {gt_box[2]}, {gt_box[3]}]]</box>"
         if gt_box is not None else "No liver tumor is found.")
    return {"id": f"{pid}_{label}_{os.path.basename(fn)}", "patient_id": int(pid),
            "image_path": fn, "question": q, "gt_box": gt_box, "label": label, "modality": "ct_liver",
            "conversations": [{"from": "human", "value": "<image>\n" + q},
                              {"from": "gpt", "value": a}]}


def main():
    import kagglehub, nibabel as nib
    os.environ.setdefault("KAGGLEHUB_CACHE", os.path.abspath(DATA_ROOT))
    roots = [kagglehub.dataset_download("andrewmvd/liver-tumor-segmentation"),
             kagglehub.dataset_download("andrewmvd/liver-tumor-segmentation-part-2")]
    for r in roots:
        print("LiTS root:", r)

    seg_paths, vol_paths = {}, {}
    for r in roots:
        for p in glob.glob(os.path.join(r, "**", "segmentation-*.nii*"), recursive=True):
            seg_paths[int(re.search(r"segmentation-(\d+)", p).group(1))] = p
        for p in glob.glob(os.path.join(r, "**", "volume-*.nii*"), recursive=True):
            vol_paths[int(re.search(r"volume-(\d+)", p).group(1))] = p
    print("So ca co nhan:", len(seg_paths), "| co volume:", len(vol_paths))

    rows = []
    n = len(seg_paths)
    for k, pid in enumerate(sorted(seg_paths)):
        if pid not in vol_paths:
            continue
        seg = np.asarray(nib.load(seg_paths[pid]).dataobj)        # dtype goc (nhe)
        vimg = nib.load(vol_paths[pid])                           # LAZY
        H, W, D = seg.shape
        tumor = (seg == 2).reshape(-1, D).sum(0)
        liver = (seg == 1).reshape(-1, D).sum(0)

        def _save(z, fn):
            Image.fromarray(window(np.asarray(vimg.dataobj[:, :, z]))).save(os.path.join(OUT_DIR, fn))

        pos_z = [int(z) for z in np.argsort(tumor)[::-1] if tumor[z] > 0][:N_POS_SLICES]
        for z in pos_z:
            fn = f"images/liver_{pid:03d}_pos_z{z}.png"
            _save(z, fn)
            rows.append(make_record(fn, mask_to_box(seg[:, :, z] == 2, W, H), "tumor", pid))

        cand = np.where((tumor == 0) & (liver > 0))[0]
        if len(cand):
            pick = cand[np.linspace(0, len(cand) - 1, min(N_NEG_SLICES, len(cand))).astype(int)]
            for z in sorted(set(int(z) for z in pick)):
                fn = f"images/liver_{pid:03d}_neg_z{z}.png"
                _save(z, fn)
                rows.append(make_record(fn, None, "none", pid))

        del seg
        print(f"  [{k+1}/{n}] pid {pid}: +{len(pos_z)} duong", flush=True)

    with open(os.path.join(OUT_DIR, "data.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("=" * 50)
    print("Tong mau:", len(rows),
          "| duong:", sum(r["label"] == "tumor" for r in rows),
          "| am:", sum(r["label"] == "none" for r in rows))
    print("So benh nhan:", len({r["patient_id"] for r in rows}))
    print("Luu o:", OUT_DIR)


if __name__ == "__main__":
    main()
