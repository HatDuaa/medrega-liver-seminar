# Review — `eval_visualize.ipynb` (liver-tumor detection, local/no-GPU analysis)

**Reviewer pass:** 2026-06-30
**Scope:** numerical correctness, honesty/overclaim, story coherence, consistency, caveats, bugs, seminar-completeness.
**Method:** split replicated from `data.jsonl` (SEED=0, rng.shuffle, 60/20/20 by patient); JSON `test[]` re-linked 1:1 to replicated `test_rows`; every headline metric recomputed from `eval/eval_pred_gemma4_v3_0628_050605.json`.

## Recompute vs notebook (ground truth)

| Metric | Recomputed | Notebook prints | Match? |
|---|---|---|---|
| Split alignment (pid + gt_boxes) | exact, 255 test / 60 cal | asserted in cell [0] | YES |
| Slices / positive / lesions | 255 / 120 / 206 | 255 / 120 / 206 | YES |
| Size tertiles | q1=0.076%, q2=0.263% | computed live | YES |
| Median lesion area | 0.139% | 0.14% (cell [1]) | YES |
| overlap-detect recall | 60% (123/206) | 60% | YES |
| recall@IoU>0.25 | 54% (112/206) | 54% | YES |
| recall@IoU>0.5 | 38% (79/206) | 38% | YES |
| Full-slice miss (0 box) | 49/120 | 49/120 | YES |
| **per-patient pIoU (penalized)** | **0.270**, CI95 [0.186, 0.359], n=25 | 0.270 + bootstrap CI | YES |
| matched-pair IoU (optimistic) | 0.324 | 0.324 ("reference only") | YES |
| Negative slices / FP | 135 / 2 (1.5%) | computed live | YES |
| FP per-patient | 2/27 (7.4%) | computed live | YES |
| Missed patients | 5/25; pids {116,95,121,73,59} | computed live | YES |
| Missed vs detected max-area | 1.28% vs 1.32% | computed live | YES |
| pid=116 missed, 5.63% | YES | computed live | YES |
| Recall by size (det/r@.25): NHO 43/35, VUA 60/54, LON 76/74 | matches | matches | YES |
| Spearman(cal): logprob +0.863, selfconf +0.729, spatial −0.154 | matches, BEST=logprob | matches | YES |

**Bottom line on numbers:** every printed/plotted number in the notebook reproduces from the JSON. The split replication is exact (the `assert` in cell [0] is real and passes). No fabricated or mis-rounded numbers found in the live-computed cells.

---

## Findings (numbered)

1. **[WARNING] — cell [0] markdown table in the brief / "established facts" mismatch on FALSE POSITIVES (notebook is RIGHT, brief is STALE).** The brief's "established facts" say per-slice FP ≈ 6% (8/135) and per-patient ≈ 26%. The actual JSON gives **2/135 = 1.5%** per-slice and **2/27 = 7.4%** per-patient (the two FP slices are pid 14 and pid 78). The notebook computes these live and prints the correct low numbers. **No fix to the notebook** — but whoever wrote the slide narrative from the "26% FP" figure must update it; do not present 6%/26%. Flagging because a reviewer reading the brief would otherwise "correct" the notebook the wrong way.

2. **[WARNING] — cell [0] / brief: per-patient localization headline is 0.270 (penalized), not 0.32.** The "≈0.32" established fact is the *optimistic matched-pair* IoU (recomputed 0.324), which the notebook correctly demotes to "reference only: matched-pair IoU (optimistic)". The honest headline the notebook leads with is **pIoU 0.270, CI95 [0.186, 0.359]**. This is good and honest, but slide text must quote **0.27 (not 0.32)** as the localization quality, and the CI is **[0.19, 0.36]**, *wider and lower* than the brief's "[0.24, 0.42]". Make sure the deck doesn't cite the friendlier 0.32/[0.24,0.42] pair as the headline.

3. **[BLOCKING for seminar-completeness] — the patient-level DETECTION table (Sens 80% / Spec 100% / Prec 100% / F1 0.89) is ABSENT from this notebook.** Grep confirms no sens/spec/prec/F1 block here; it lives in the *other* notebook (`medrega_finetune` per git log "Thêm metric NHẬN BIẾT"). This eval/presentation notebook only shows overlap-detect recall (60%) and negative-slice FP. For a seminar the clean "did we catch the patient" story (20/25 caught, 0 false-alarm patients) is the single most quotable result and it is missing here. **Fix:** port the binary detection block (patient + slice level) into this notebook, right after cell [4]/[6], OR explicitly state in a markdown cell that detection metrics live in the companion notebook. Recomputed values for the port: patient Sens 80.0% (20/25), Spec 100% (2/2), Prec 100%, F1 0.889; slice Sens 59.2% (71/120), Spec 98.5% (133/135).

4. **[BLOCKING] — "Specificity 100%" rests on n=2 negative patients and MUST carry the caveat wherever shown.** There are only **2 fully tumor-free patients in the test split (pid 38, 119)**. 125 of the 135 "negative slices" are *intra-patient* tumor-free slices from the 25 tumor patients; only 10 negative slices come from genuinely tumor-free patients. The notebook's cell [10] DOES print the right note ("these are tumor-free slices from patients with tumors, not clinical specificity on healthy patients") — keep it. But if the detection Sens/Spec table from finding #3 is added or shown on a slide, "Spec 100%" with denominator 2 is near-meaningless and **must** state n=2 and "not clinical specificity." Do not let "100% specificity" stand unqualified on any slide.

5. **[WARNING] — cell [5] markdown leans toward a "model/decision/training" failure narrative that the data only weakly supports.** Cell [5] sets up the "if large + not-low-contrast and still missed → model fault" framing; cell [7] then computes `easy_miss` (no-overlap misses that are neither small nor low-contrast). The contrast metric is, by the code's own comment, a "rough proxy from PNG windowed CT, not a true tumor mask." With n=83 no-overlap misses and a bottom-third contrast cutoff, the "easy-looking miss" bucket is small and noisy. The prose is appropriately hedged ("nghieng ve…", "dung de soi xu huong chu khong ket luan"), which is good — **keep the hedge**, and do not upgrade this to a firm "the model is under-trained" claim on a slide.

6. **[NIT] — cell [1] vs cell [2] pixel-size phrasing.** Cell [1] annotates the **median** lesion as "~19px" (recompute: sqrt(0.139%·512²)=19.1px, correct). Cell [2] title says small tumors are "~10-15px". These are different tiers (median vs small-tertile); small tertile side ≈ sqrt(0.076%·512²)=14px, so "10-15px" is accurate for the small tier. Not contradictory, but a viewer flipping between slides may read it as inconsistent — consider saying "median ~19px, smallest tier ~10-15px" once.

7. **[NIT] — threshold operator inconsistency: `>` vs `>=` at IoU 0.25.** Cell [3] uses `iou >= 0.25` for the per-size localization rate; cell [10] uses `matched_ious > th` (strict) for the recall@IoU table and `B[m] > 0.25` in recall-by-size. Recomputed both ways the displayed integer percentages are identical here (no lesion sits exactly at 0.25), so no number changes — but standardize on one operator to avoid a future off-by-epsilon discrepancy between the two cells.

8. **[NIT] — cell [10] recall@IoU table uses precision/recall over Hungarian-matched pairs only.** `precision = TP/npd` with npd = total predicted boxes on positive slices (163). This omits boxes the model drew on *negative* slices from FP (the 2 FP boxes), so the printed "precision" is localization-precision on positive slices, not a global detection precision. That is a legitimate choice, but label it "localization precision (positive slices)" so it isn't read as detection precision. No number is wrong.

9. **[NIT] — Spearman / risk-coverage rests on n=13 cal patients.** Cell [9] correctly prints the "n small → proof-of-concept" caveat and cell [6]'s table is honest. logprob +0.863 is genuinely the strongest signal (recomputed), spatial is anti-correlated (−0.154). Fine to present as "logprob is the usable confidence signal," but keep the n=13 caveat visible on the slide, not just in the cell output.

10. **[NIT] — cell [2] `single`-lesion-only sampling for the size gallery.** The GT-by-size gallery filters to `len(gt_boxes)==1`. That's a reasonable visualization choice (clean single-box panels) but it means the displayed examples are not a random draw from all 206 lesions; multi-lesion slices (which drive part of the under-count story in cell [10]) are never shown in cell [2]. Purely cosmetic; mention "single-lesion slices shown for clarity" if asked.

---

## What's good

- **Honest headline.** Leads localization with the *penalized* per-patient IoU (0.270) and explicitly demotes the optimistic 0.324 to "reference only." This is the right call and resists overclaiming.
- **Split replication is real and asserted.** Cell [0] re-derives the split and asserts pid + gt_boxes alignment on all 255 test rows; it passes. Everything downstream is therefore trustworthy.
- **No-box misses are NOT hidden.** Cell [4]/[10] surface 49/120 full-slice misses and 5/25 fully-missed patients, and cell [6] makes the key non-obvious point: missed patients' tumors are the same size as detected ones (1.28% vs 1.32%), with pid=116 carrying a large 5.63% lesion yet missed → "miss is not about size, it's isointensity." That is the most valuable scientific finding in the deck and it's correctly evidenced.
- **Detect-vs-localize separation** (overlap IoU>0 as coarse detect vs IoU≥0.25 as localization) is a clean framing and is applied consistently in cells [3], [7], [10].
- **Caveats mostly present where they matter:** intra-patient specificity note (cell [10]), contrast-proxy disclaimer (cells [5], [7]), n-small for selective prediction (cell [9]), bootstrap CI on per-patient IoU (cell [10]).
- Recall-by-size monotonicity (NHO 35% → VUA 54% → LON 74% @IoU.25) reproduces exactly and supports the "small/faint missed" story.

---

## Verdict

**FIX-FIRST** — the numbers are correct and the analysis is honest, but two seminar-blocking gaps remain.

**Three most important fixes:**
1. **Add (or explicitly cross-reference) the patient-level detection table** Sens 80% (20/25) / Spec 100% (2/2) / Prec 100% / F1 0.89 — it's the headline result and is currently absent from this notebook (finding #3).
2. **Never show "Specificity 100%" without "n=2 tumor-free patients / intra-patient, not clinical specificity"** (finding #4).
3. **Quote 0.27 (CI [0.19, 0.36]) — not 0.32 — as the localization headline, and 1.5% slice / 7.4% patient — not 6%/26% — as the false-positive rate** on every slide; the friendlier numbers in the brief are stale/optimistic (findings #1, #2).
