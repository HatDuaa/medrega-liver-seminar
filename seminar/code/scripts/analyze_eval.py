"""Phân tích file eval_pred_*.json (xuất từ notebook) — CHẠY LOCAL, KHÔNG cần GPU/model.

Input JSON: {"run":..., "test":[...], "cal":[...]}, mỗi phần tử:
  {pid, is_pos, pred_boxes:[[x1,y1,x2,y2],...], gt_boxes:[...], logprob, spatial, selfconf, ...}

Usage:
  python analyze_eval.py <path_to_json>
  (không truyền -> tự tìm eval_pred_*.json trong cùng folder)
"""
import sys, json, glob, os
import numpy as np

try:
    from scipy.optimize import linear_sum_assignment
    from scipy.stats import spearmanr
    from sklearn.metrics import roc_auc_score
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAVE_PLOT = True
except ImportError as e:
    print("Thiếu thư viện:", e); sys.exit(1)

SIGNALS = ["logprob", "spatial", "selfconf"]
THRS = [0.1, 0.25, 0.5, 0.75]
IOU_CORRECT = 0.5


# ---------------- box utils ----------------
def iou(b1, b2):
    if not b1 or not b2:
        return 0.0
    xa, ya = max(b1[0], b2[0]), max(b1[1], b2[1])
    xb, yb = min(b1[2], b2[2]), min(b1[3], b2[3])
    inter = max(0, xb - xa) * max(0, yb - ya)
    a1 = max(0, b1[2] - b1[0]) * max(0, b1[3] - b1[1])
    a2 = max(0, b2[2] - b2[0]) * max(0, b2[3] - b2[1])
    u = a1 + a2 - inter
    return inter / u if u > 0 else 0.0


def match_boxes(preds, gts):
    if not preds or not gts:
        return [], len(preds), len(gts)
    M = np.zeros((len(preds), len(gts)))
    for i, p in enumerate(preds):
        for j, g in enumerate(gts):
            M[i, j] = iou(p, g)
    ri, ci = linear_sum_assignment(1 - M)
    return [float(M[r, c]) for r, c in zip(ri, ci)], len(preds), len(gts)


def boot_ci(vals, n=2000, seed=0):
    vals = np.asarray(vals, float)
    if len(vals) < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = np.arange(len(vals))
    ms = [vals[rng.choice(idx, len(idx), replace=True)].mean() for _ in range(n)]
    return tuple(np.percentile(ms, [2.5, 97.5]))


def per_patient(rows):
    from collections import defaultdict
    bp = defaultdict(list)
    for r in rows:
        if r["is_pos"]:
            bp[r["pid"]].append(r)
    piou = np.array([np.mean([x["miou"] for x in rs]) for rs in bp.values()])
    psig = {k: np.array([np.mean([x[k] for x in rs]) for rs in bp.values()]) for k in SIGNALS}
    return piou, psig


# ---------------- analyses ----------------
def prep(rows):
    for r in rows:
        r["matched"] = match_boxes(r["pred_boxes"], r["gt_boxes"])[0]
        r["miou"] = float(np.mean(r["matched"])) if r["matched"] else 0.0
    return rows


def metrics(rows):
    pos = [r for r in rows if r["is_pos"]]
    neg = [r for r in rows if not r["is_pos"]]
    print("\n" + "=" * 60 + "\n## METRICS (Hungarian multi-box)\n" + "=" * 60)
    print(f"[per-slice DƯƠNG] {len(pos)} lát | mean matched-IoU {np.mean([r['miou'] for r in pos]):.3f}")
    for th in THRS:
        tp = sum(sum(v > th for v in r["matched"]) for r in pos)
        ngt = sum(len(r["gt_boxes"]) for r in pos)
        npr = sum(len(r["pred_boxes"]) for r in pos)
        print(f"   @IoU>{th}: recall {tp/ngt if ngt else 0:.0%} | precision {tp/npr if npr else 0:.0%}")
    pat_iou, _ = per_patient(pos)
    lo, hi = boot_ci(pat_iou)
    print(f"\n[PER-PATIENT] {len(pat_iou)} bệnh nhân | mean-IoU {pat_iou.mean():.3f} | CI95 [{lo:.3f}, {hi:.3f}]")
    for th in [0.25, 0.5]:
        print(f"   bệnh nhân IoU-TB >= {th}: {(pat_iou >= th).mean():.0%}")
    single = [r["miou"] for r in pos if len(r["gt_boxes"]) == 1]
    multi = [r["miou"] for r in pos if len(r["gt_boxes"]) >= 2]
    print(f"\n[Phân tầng số ổ] 1-ổ: {len(single)} lát IoU {np.mean(single) if single else 0:.3f}"
          f" | nhiều-ổ: {len(multi)} lát IoU {np.mean(multi) if multi else 0:.3f}")
    if neg:
        fp = sum(len(r["pred_boxes"]) > 0 for r in neg)
        print(f"\n[ÂM] {len(neg)} lát | im đúng {len(neg)-fp} | BỊA box (FP) {fp} ({fp/len(neg):.0%})")
    return pat_iou


def by_size(rows):
    print("\n" + "=" * 60 + "\n## RECALL THEO KÍCH THƯỚC u (diện tích GT box = proxy độ to/rõ)\n" + "=" * 60)
    pos = [r for r in rows if r["is_pos"]]
    lesions = []
    for r in pos:
        for gv in r["gt_boxes"]:
            best = max((iou(p, gv) for p in r["pred_boxes"]), default=0.0)
            lesions.append(((gv[2] - gv[0]) * (gv[3] - gv[1]), best))
    if not lesions:
        print("  (không có ổ u)"); return
    A = np.array([a for a, _ in lesions], float)
    B = np.array([b for _, b in lesions], float)
    print(f"Tổng {len(lesions)} ổ u | diện tích box (%ảnh): nhỏ {A.min()/1e4:.2f}% | "
          f"trung vị {np.median(A)/1e4:.2f}% | to {A.max()/1e4:.2f}%")
    q1, q2 = np.percentile(A, [33, 67])
    print(f"\n{'Nhóm u':18}{'n':>5}{'recall@.25':>12}{'recall@.5':>11}{'IoU TB':>9}{'cỡ TB(%ảnh)':>13}")
    for name, lo, hi in [("NHỎ/mờ", A.min() - 1, q1), ("VỪA", q1, q2), ("LỚN/rõ", q2, A.max() + 1)]:
        m = (A >= lo) & (A < hi)
        if not m.any():
            continue
        bb = B[m]
        print(f"{name:18}{int(m.sum()):>5}{(bb>0.25).mean():>12.0%}{(bb>0.5).mean():>11.0%}"
              f"{bb.mean():>9.3f}{A[m].mean()/1e4:>12.2f}%")


def huong1(test, cal, out_png=None):
    print("\n" + "=" * 60 + "\n## HƯỚNG-1 (selective prediction): CAL chọn / TEST báo cáo\n" + "=" * 60)
    T_iou, T_sig = per_patient(test)
    C_iou, C_sig = per_patient(cal)
    c25 = (C_iou >= 0.25).astype(int)
    chosen = {}
    print(f"{'tín hiệu':10}{'Spearman(cal)':>15}{'AUROC@.25':>11}")
    for k in SIGNALS:
        v = C_sig[k]
        rho = spearmanr(v, C_iou).correlation if np.std(v) > 1e-9 and np.std(C_iou) > 1e-9 else float("nan")
        sign = -1.0 if (not np.isnan(rho) and rho < 0) else 1.0
        auc = roc_auc_score(c25, sign * v) if len(set(c25)) > 1 and np.std(v) > 1e-9 else float("nan")
        chosen[k] = {"sign": sign, "rho": rho}
        print(f"{k:10}{rho:>+15.3f}{auc:>11.3f}")
    valid = [k for k in SIGNALS if not np.isnan(chosen[k]["rho"])]
    BEST = max(valid, key=lambda k: abs(chosen[k]["rho"])) if valid else "spatial"
    print(f"=> BEST (|Spearman| cal): {BEST}   (AUROC=1.0 trên cal n nhỏ là ẢO -> tin Spearman)")

    n = len(T_iou)
    print(f"\n[TEST risk-coverage] {n} bệnh nhân")
    if HAVE_PLOT and out_png:
        plt.figure(figsize=(6, 4))
    for k in SIGNALS:
        sig = chosen[k]["sign"] * T_sig[k]; order = np.argsort(-sig)
        sel = [T_iou[order[:i + 1]].mean() for i in range(n)]
        if HAVE_PLOT and out_png:
            plt.plot([(i + 1) / n for i in range(n)], sel, marker="o", ms=3, label=k + (" *" if k == BEST else ""))
    sig = chosen[BEST]["sign"] * T_sig[BEST]; order = np.argsort(-sig)
    for c in [1.0, .75, .5, .25]:
        kk = max(1, int(c * n)); print(f"   [{BEST}] coverage {c:.0%}: selIoU = {T_iou[order[:kk]].mean():.3f}")
    if HAVE_PLOT and out_png:
        plt.gca().invert_xaxis(); plt.xlabel("Coverage"); plt.ylabel("Selective mean-IoU")
        plt.title("Risk-Coverage (test)"); plt.legend(); plt.grid(alpha=.3); plt.tight_layout()
        plt.savefig(out_png, dpi=90, bbox_inches="tight"); print(f"\n   [đã lưu chart] {out_png}")

    csig = chosen[BEST]["sign"] * C_sig[BEST]
    thr = float(np.quantile(csig, 0.3))
    tsig = chosen[BEST]["sign"] * T_sig[BEST]
    ans = tsig >= thr; selia = T_iou[ans]; wrong = int(np.sum(selia < IOU_CORRECT))
    print(f"\n[Conformal] ngưỡng(cal,cov~70%) {thr:.3f} | TEST trả lời {int(ans.sum())}/{n} "
          f"| sai {wrong} | selIoU {np.mean(selia) if len(selia) else float('nan'):.3f}")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        here = os.path.dirname(os.path.abspath(__file__))
        cand = sorted(glob.glob(os.path.join(here, "eval_pred_*.json")) + glob.glob(os.path.join(here, "*.json")))
        if not cand:
            print("Không tìm thấy JSON. Dùng: python analyze_eval.py <path.json>"); sys.exit(1)
        path = cand[-1]
    print(f"Đọc: {path}")
    d = json.load(open(path, encoding="utf-8"))
    test = prep(d["test"]); cal = prep(d["cal"])
    print(f"run={d.get('run')} | test {len(test)} ({sum(r['is_pos'] for r in test)} dương) | cal {len(cal)}")
    metrics(test)
    by_size(test)
    huong1(test, cal, out_png=os.path.join(os.path.dirname(os.path.abspath(path)), "risk_coverage.png"))


if __name__ == "__main__":
    main()
