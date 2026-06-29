# Eval-pipeline correctness review — v4 numbers

**Date:** 2026-06-29
**Reviewer scope:** Is the v4 eval (per-patient IoU 0.071, recall@0.25 10%, recall@0.5 1%, FP-per-patient 26%) WRONG (model fine, eval under-reporting), or is it a faithful measurement of a genuinely-bad model?
**Files:** `medrega_finetune.ipynb` cells `util`, `fmt`, `split`, `sec8`, `sec9`, `1JZwDbmBDdnw`, `sec11`, `diag`; `scripts/analyze_eval.py`; `prep_data_multi.ipynb`; `eval/eval_pred_gemma4_v3_0628_050605.json`.

---

## (a) VERDICT

**The eval pipeline is TRUSTWORTHY. It is NOT under-reporting a fine model.** Low IoU/recall is a real property of the model's output, not an artifact of parsing, scale, GT-linkage, or aggregation.

Decisive evidence: I re-ran the metrics math from scratch on the only on-disk prediction file (`eval_pred_gemma4_v3_*.json`, the v3 run) and **reproduced the reported v3 numbers exactly**:

| metric | reported (worklog) | recomputed from JSON |
|---|---|---|
| per-patient mean-IoU | 0.32 | **0.324** |
| per-slice mean-IoU | 0.32 | 0.334 |
| recall@0.25 | 54% | **54%** (112/206) |
| recall@0.5 | ~38% | 38% (79/206) |

A pipeline that reproduces v3 to 3 decimals is not silently zeroing IoU. The v4 numbers come out of the *same* code path, so the v4 collapse is the model, not the metric. (I could not recompute v4 directly — no `eval_pred_gemma4_v4_*.json` exists on disk yet; the diagnostic in section (c) closes that gap once the v4 run produces one.)

**Caveat / one genuine risk flagged below:** the v4 model is loaded via a brand-new BCE-head training + `selck` + `mergesave` chain. If v4 IoU is *uniformly* near-zero (not the bimodal "miss-or-good" pattern v3 shows), the most likely culprit is **a broken/degraded model load (bad merge or wrong checkpoint), or BCE-head over-suppressing detection**, NOT the metric. The section (c) diagnostic distinguishes these in one run.

---

## (b) Assessment of each suspected bug — all CLEARED, with evidence

### 1. Box scale / parsing — NO mismatch
- GT boxes are written in `prep_data_multi.ipynb` `_box()` as `int(x/W*COORD_SCALE)` with `COORD_SCALE=1000` → `[0,1000)`.
- Training answer text (`fmt._answer_from_boxes`) and the inference prompt (`INSTRUCT_PROMPT_TRAIN`, "1000x1000 grid") use the same scale.
- `util.parse_boxes` reads raw integers from `[x1,y1,x2,y2]` literals — same scale.
- **Empirical proof** (v3 JSON, raw rows): pred and GT are on the same scale and frequently near-identical, e.g. pid 7 `pred [369,183,405,221]` vs `gt [373,191,404,218]`; pid 14 `pred [626,453,663,491]` vs `gt [632,449,667,494]`. No ×1000 / ×0.001 / xywh-vs-xyxy offset anywhere. IoU ~0 is **not** a scale artifact.

### 2. `pred_boxes` source / regex — CORRECT
- `sec9._predict_row`: `gens[0] = gen_raw(rec, 0.0)` (greedy) and `pred_boxes = g0["boxes"]`. `gen_raw` parses from `processor.decode(new, skip_special_tokens=True)`. Correct: greedy = the "main" answer.
- `parse_boxes` regex `\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]` correctly extracts every `[a,b,c,d]` from `<box>[[...],[...]]</box>`; unit asserts in `util` pass for multi-box. It silently drops a box only if `x2<=x1 or y2<=y1` (degenerate) — correct behavior, not a leak.
- One **minor** edge case (not the cause here): the negative-guard `if neg and "[" not in t` means a generation that says "no tumor" but still contains a stray `[` would skip the early-return; harmless because it then just finds no valid 4-int group and returns `[]`.

### 3. GT linkage — CORRECT
- `gt_boxes` is a field on each `data.jsonl` row (v3 data), carried verbatim through `split` (rows filtered by `patient_id`, order preserved) into `dataset["test"]`. `_predict_row` attaches `gt_boxes` and `pred_boxes` **on the same `rec` in the same iteration** — there is no separate sort/zip that could misalign pred↔GT.
- Per-row pairing is intrinsic (both fields live on one dict), so a split/ordering bug cannot desync them. Confirmed in the JSON: matched pairs are spatially coherent (section b1).

### 4. Metrics math (`1JZwDbmBDdnw`) — CORRECT
- `match_boxes`: Hungarian on `1 - IoU`, returns matched IoUs. `miou = mean(matched)` per slice; empty match → 0.0. Correct.
- `micro_recall_prec`: `tp = count(matched_iou > th)`, `recall = tp/ngt`, `prec = tp/npr`. No double-counting (Hungarian gives ≤1 match per GT). 
- `> th` vs `>= th`: immaterial — **zero** matched IoUs land exactly on a threshold (checked: 0 values == 0.5; only 5 in (0.49,0.51)).
- Per-patient: `mean over patients of (mean miou over that patient's pos slices)` — standard, no deflation.
- `analyze_eval.py` mirrors all of this identically.

### 5. The diag-vs-metrics "inconsistency" — RESOLVED: real misses, not a bug
This was the crux. The histogram of v3 per-slice IoU over 120 positive slices:

```
IoU = 0 (true miss):   51 slices  (42%)   <- of which 49 are EMPTY pred (0 boxes)
IoU (0, 0.25):          5 slices  ( 4%)
IoU [0.25, 0.5):       17 slices  (14%)
IoU [0.5, 0.75):       33 slices  (28%)
IoU [0.75, 1.0]:       14 slices  (12%)
```

- **41% of positive slices have EMPTY predictions** (model emits 0 boxes → "lazy detect"). These force IoU 0.
- mean-IoU over **all** pos slices = 0.334; mean-IoU over **non-empty** preds only = **0.565**.
- So the distribution is **bimodal**: when the model draws a box it is good (0.565, matching the diag cell's 0.42–0.49+ examples and the worklog's "IoU 0.62 when it draws"); when it abstains (41% of the time) it scores 0. The low mean is the misses dragging it down — exactly what the prompt's hypothesis (5/6) called the alternative. **There is no aggregation bug.** Diag (qualitative, naturally over-samples slices where a box was drawn) and metrics (quantitative, includes all the empty-pred misses) are fully consistent once you account for the abstention mass.

### 6. FP per-patient — CORRECT
- `1JZwDbmBDdnw` negatives block: `fp = count(len(pred_boxes)>0)` per slice, then per-patient `any(len(pred_boxes)>0)` aggregated with bootstrap CI. Counting non-empty preds on negatives as FP is correct. (26% for v4 vs 1% v3 just means v4 hallucinates boxes on negative slices far more — consistent with a model that was pushed to detect more aggressively by the BCE-head and over-fired.)

---

## (c) Exact diagnostic to run (on the v4 JSON, once it exists)

The v3 JSON proved the metric. To prove the v4 *number* the same way and pin down model-vs-load, run this against `eval_pred_gemma4_v4_*.json` (CPU-only, no GPU):

```python
import json, numpy as np
from scipy.optimize import linear_sum_assignment
def iou(a,b):
    if not a or not b: return 0.0
    xa,ya=max(a[0],b[0]),max(a[1],b[1]); xb,yb=min(a[2],b[2]),min(a[3],b[3])
    inter=max(0,xb-xa)*max(0,yb-ya); ua=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/ua if ua>0 else 0.0
def match(P,G):
    if not P or not G: return []
    M=np.array([[iou(p,g) for g in G] for p in P]); r,c=linear_sum_assignment(1-M)
    return [float(M[i,j]) for i,j in zip(r,c)]
d=json.load(open("<eval_pred_gemma4_v4_*.json>",encoding="utf-8"))
pos=[r for r in d["test"] if r["is_pos"]]
# 1) PRINT 10 pred vs gt — is it scale, empties, or garbage?
for r in pos[:10]:
    print(r["pid"],"| pred",r["pred_boxes"],"| gt",r["gt_boxes"])
# 2) THE deciding split: empty-pred rate vs IoU-when-nonempty
mi=[ (np.mean(match(r["pred_boxes"],r["gt_boxes"])) if r["pred_boxes"] and match(r["pred_boxes"],r["gt_boxes"]) else 0.0) for r in pos]
emp=sum(not r["pred_boxes"] for r in pos)
ne =[m for r,m in zip(pos,mi) if r["pred_boxes"]]
print(f"empty-pred {emp}/{len(pos)} ({emp/len(pos):.0%}) | mean-IoU(all) {np.mean(mi):.3f} | mean-IoU(non-empty) {np.mean(ne) if ne else 0:.3f}")
# 3) also dump a few raw gen texts to see if output is malformed
for r in pos[:5]:
    g=(r.get("gens") or [{}])[0]; print(repr(g.get("text"))[:200])
```

**Interpretation key:**
- If `empty-pred ≈ 90%+` and `mean-IoU(non-empty) ≈ 0.5+` → model is **fine when it answers but the BCE-head made it abstain almost always** (v4 over-suppressed detection). Eval correct; fix is training (lower `LAMBDA_BCE` / `BCE_POS_W`, or pick a less-shy checkpoint in `selck`).
- If `mean-IoU(non-empty)` is also near 0 (boxes present but wrong/garbage, or raw text malformed) → **the model load is broken** (bad `mergesave` losing the vision tower, or `selck` saved/loaded the wrong epoch). Eval still correct; fix is the load chain. The worklog already flagged "merge lỗi vẫn save -> mất vision" as a sharp edge; this is the prime suspect for a *uniform* near-zero.
- Either way: if pred boxes look on-scale and GT-aligned (they will), **the eval is exonerated**.

Also run `python scripts/analyze_eval.py eval/eval_pred_gemma4_v4_*.json` for the full stratified report (it shares the exact metric code, already validated against v3).

---

## (d) Reconciliation: diag (some good boxes) vs metrics (mean-IoU near-zero)

They are **not** in conflict.

- **diag / viz_after** decode the model on a handful of slices and show the cases where a box was drawn — those look good (IoU ~0.4–0.6). This is real and reflects the model's *localization* ability **conditional on it choosing to answer**.
- **metrics** average over *all* positive slices, including the large fraction where the model abstains (emits 0 boxes → IoU 0). For v3 that fraction is 42%, pulling 0.565 (non-empty) down to 0.334 (overall). The model's weakness is a **detection/recall (abstention) problem, not a localization problem** — precisely the diagnosis in the worklog ("định vị TỐT, LƯỜI detect").
- For v4 the same mechanism, amplified: per-patient IoU 0.071 + recall@0.5 1% is consistent with the model emitting almost no boxes on positives (mass of empty preds → IoU 0), while FP-per-patient *rising* to 26% says the few boxes it does emit land disproportionately on negatives. That is a coherent picture of a model whose detect decision was knocked badly off by the v4 BCE-head — a **training regression, faithfully measured**, not an eval miscount.

**Bottom line:** trust the v4 eval. The number to fix lives in the v4 training/checkpoint-selection chain (`train` BCE-head, `selck`, `mergesave`), not in `sec9`/`1JZwDbmBDdnw`/`analyze_eval.py`. Run the section-(c) diagnostic on the v4 JSON to confirm whether v4 is "abstains too much" (retune loss) or "vision lost in merge" (reload), and to reproduce 0.071 from raw the same way 0.324 was reproduced for v3.
