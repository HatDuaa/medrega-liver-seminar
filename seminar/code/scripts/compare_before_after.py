"""So sánh BEFORE (Gemma4 zero-shot) vs AFTER (fine-tune v3) — bảng before/after cho báo cáo.
Chạy LOCAL, không GPU. Tính từ 2 file eval_pred_*.json (chỉ cần pred_boxes/gt_boxes/is_pos/pid).

Cách dùng:
  python compare_before_after.py eval_pred_gemma4_zeroshot_XXXX.json eval_pred_gemma4_v3_XXXX.json
  (không truyền -> tự tìm file zeroshot + v3 mới nhất trong folder này)
"""
import sys, os, glob, json
import numpy as np
from collections import defaultdict
try:
    from scipy.optimize import linear_sum_assignment
except ImportError:
    print("Cần scipy: pip install scipy"); sys.exit(1)

IOU_THR = 0.25   # ngưỡng coi là "trúng" (khớp cell metrics / analyze_eval)


def iou(b1, b2):
    if not b1 or not b2: return 0.0
    xa, ya = max(b1[0], b2[0]), max(b1[1], b2[1])
    xb, yb = min(b1[2], b2[2]), min(b1[3], b2[3])
    inter = max(0, xb - xa) * max(0, yb - ya)
    a1 = max(0, b1[2] - b1[0]) * max(0, b1[3] - b1[1])
    a2 = max(0, b2[2] - b2[0]) * max(0, b2[3] - b2[1])
    u = a1 + a2 - inter
    return inter / u if u > 0 else 0.0


def match(preds, gts):
    if not preds or not gts: return [], len(preds), len(gts)
    M = np.zeros((len(preds), len(gts)))
    for i, p in enumerate(preds):
        for j, g in enumerate(gts):
            M[i, j] = iou(p, g)
    ri, ci = linear_sum_assignment(1 - M)
    return [float(M[r, c]) for r, c in zip(ri, ci)], len(preds), len(gts)


def analyze(rows):
    """Trả về dict các chỉ số chính cho 1 JSON test."""
    pos = [r for r in rows if r["is_pos"]]
    neg = [r for r in rows if not r["is_pos"]]

    # --- Localization ---
    ng = sum(len(r["gt_boxes"]) for r in pos)
    tp = 0; pen_by_pat = defaultdict(list)
    for r in pos:
        mi, npd, ngt = match(r["pred_boxes"], r["gt_boxes"])
        tp += sum(v > IOU_THR for v in mi)
        d = max(ngt, npd)
        pen_by_pat[r["pid"]].append(sum(mi) / d if d else 0.0)
    recall_loc = tp / ng if ng else 0.0
    pat_iou = np.array([np.mean(v) for v in pen_by_pat.values()])

    # --- Detection nhị phân (per-patient): có vẽ box hay không ---
    bp = defaultdict(lambda: [0, 0])
    for r in rows:
        bp[r["pid"]][0] |= int(bool(r["gt_boxes"]))
        bp[r["pid"]][1] |= int(len(r["pred_boxes"]) > 0)
    items = list(bp.values())
    TP = sum(g and p for g, p in items); FP = sum((not g) and p for g, p in items)
    TN = sum((not g) and not p for g, p in items); FN = sum(g and not p for g, p in items)
    sens = TP / (TP + FN) if TP + FN else 0.0
    prec = TP / (TP + FP) if TP + FP else 0.0
    f1 = 2 * prec * sens / (prec + sens) if prec + sens else 0.0

    # --- FP ca âm ---
    fp_sl = sum(len(r["pred_boxes"]) > 0 for r in neg)
    nbp = defaultdict(list)
    for r in neg: nbp[r["pid"]].append(len(r["pred_boxes"]) > 0)
    fp_pat = sum(any(v) for v in nbp.values())

    return {
        "n_test": len(rows), "n_pos_slice": len(pos), "n_pos_pat": len(pat_iou),
        "det_sens": sens, "det_prec": prec, "det_f1": f1,
        "loc_recall@.25": recall_loc, "loc_pIoU_patient": pat_iou.mean() if len(pat_iou) else 0.0,
        "fp_slice": fp_sl / len(neg) if neg else 0.0,
        "fp_patient": fp_pat / len(nbp) if nbp else 0.0,
    }


def _find(tag):
    fs = sorted(glob.glob(f"eval_pred_*{tag}*.json"), key=os.path.getmtime)
    return fs[-1] if fs else None


def main():
    if len(sys.argv) >= 3:
        before_p, after_p = sys.argv[1], sys.argv[2]
    else:
        before_p, after_p = _find("zeroshot"), _find("v3")
    assert before_p and after_p, "Không tìm thấy JSON zeroshot / v3 — truyền path tường minh."
    B = analyze(json.load(open(before_p, encoding="utf-8"))["test"])
    A = analyze(json.load(open(after_p, encoding="utf-8"))["test"])
    print(f"\nBEFORE (zero-shot): {os.path.basename(before_p)}")
    print(f"AFTER  (fine-tune): {os.path.basename(after_p)}")
    print(f"(test {A['n_test']} lát | {A['n_pos_pat']} bệnh nhân dương | IoU-thr {IOU_THR})\n")
    rows = [
        ("Detection F1 (bệnh nhân)", "det_f1", "{:.2f}"),
        ("  Sensitivity (bắt u)", "det_sens", "{:.0%}"),
        ("  Precision", "det_prec", "{:.0%}"),
        ("Localization recall@.25 (lát)", "loc_recall@.25", "{:.0%}"),
        ("Localization pIoU (bệnh nhân)", "loc_pIoU_patient", "{:.3f}"),
        ("False-positive (lát âm)", "fp_slice", "{:.1%}"),
        ("False-positive (bệnh nhân)", "fp_patient", "{:.1%}"),
    ]
    print(f"{'Chỉ số':34}{'BEFORE':>12}{'AFTER':>12}")
    print("-" * 58)
    for label, key, fmt in rows:
        print(f"{label:34}{fmt.format(B[key]):>12}{fmt.format(A[key]):>12}")
    print("\n=> Cột chênh lệch = giá trị fine-tune (đóng góp before/after cho báo cáo).")


if __name__ == "__main__":
    main()
