# prep_data_multi_v2.py — Cắt lát u NGẪU NHIÊN + LỚN NHẤT (đa dạng vị trí), CHẠY LOCAL
# Khác v1: thay "top-N lát u lớn nhất" -> "2 lát lớn nhất + (N-2) lát NGẪU NHIÊN có u"
# Output: ./data/data_liver_multi_v2/  (folder MỚI, không đè v1)
import os, re, glob, json
import numpy as np
from PIL import Image

# ----------------------- CONFIG -----------------------
DATA_ROOT    = "./data"
OUT_DIR      = os.path.join(DATA_ROOT, "data_liver_multi_v2")
N_POS_SLICES = 5          # tổng lát DƯƠNG/bệnh nhân
N_LARGEST    = 2          # trong đó: 2 lát u LỚN NHẤT
N_NEG_SLICES = 5          # lát ÂM (gan không u)
WL, WW       = 40, 400
COORD_SCALE  = 1000
SEED         = 0
# ------------------------------------------------------
os.makedirs(os.path.join(OUT_DIR, "images"), exist_ok=True)
rng = np.random.default_rng(SEED)


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
        seg = np.asarray(nib.load(seg_paths[pid]).dataobj)
        vimg = nib.load(vol_paths[pid])
        H, W, D = seg.shape
        tumor = (seg == 2).reshape(-1, D).sum(0)
        liver = (seg == 1).reshape(-1, D).sum(0)

        def _save(z, fn):
            Image.fromarray(window(np.asarray(vimg.dataobj[:, :, z]))).save(os.path.join(OUT_DIR, fn))

        # === DƯƠNG: N_LARGEST lát u LỚN NHẤT + phần còn lại NGẪU NHIÊN (trong lát có u) ===
        tumor_z = [int(z) for z in range(D) if tumor[z] > 0]
        if tumor_z:
            by_size = sorted(tumor_z, key=lambda z: -tumor[z])
            pick = by_size[:N_LARGEST]                          # 2 lát lớn nhất
            rest = [z for z in tumor_z if z not in pick]
            if rest:
                rng.shuffle(rest)                               # phần còn lại: ngẫu nhiên
                pick += rest[:max(0, N_POS_SLICES - N_LARGEST)]
            for z in sorted(set(pick)):
                fn = f"images/liver_{pid:03d}_pos_z{z}.png"
                _save(z, fn)
                rows.append(make_record(fn, mask_to_box(seg[:, :, z] == 2, W, H), "tumor", pid))

        # === ÂM: N_NEG_SLICES lát gan-không-u, rải đều ===
        cand = np.where((tumor == 0) & (liver > 0))[0]
        if len(cand):
            sel = cand[np.linspace(0, len(cand) - 1, min(N_NEG_SLICES, len(cand))).astype(int)]
            for z in sorted(set(int(z) for z in sel)):
                fn = f"images/liver_{pid:03d}_neg_z{z}.png"
                _save(z, fn)
                rows.append(make_record(fn, None, "none", pid))

        del seg
        print(f"  [{k+1}/{n}] pid {pid}", flush=True)

    with open(os.path.join(OUT_DIR, "data.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # verify: phân bố vị trí TÂM box dương (xem có rải hơn không)
    cen = [((r["gt_box"][0] + r["gt_box"][2]) / 2, (r["gt_box"][1] + r["gt_box"][3]) / 2)
           for r in rows if r["gt_box"]]
    cx = np.array([c[0] for c in cen]); cy = np.array([c[1] for c in cen])
    print("=" * 50)
    print("Tong mau:", len(rows), "| duong:", sum(r["label"] == "tumor" for r in rows),
          "| am:", sum(r["label"] == "none" for r in rows), "| benh nhan:", len({r["patient_id"] for r in rows}))
    print(f"Tam box duong: x [{cx.min():.0f}-{cx.max():.0f}] std {cx.std():.0f} | "
          f"y [{cy.min():.0f}-{cy.max():.0f}] std {cy.std():.0f}  (std cao = rai hon)")
    print("Luu:", OUT_DIR)


if __name__ == "__main__":
    main()
