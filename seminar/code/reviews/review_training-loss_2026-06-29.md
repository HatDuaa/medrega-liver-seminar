# Review: Is the v4 BCE-head TRAINING/LOSS the cause of the localization collapse?

- **Date:** 2026-06-29
- **Reviewer scope:** training-correctness only. (A separate reviewer owns the model-RELOAD/eval-path hypothesis.)
- **Artifact:** `seminar/code/medrega_finetune.ipynb` — cells `cfg`, `fmt`, `train`, `a6bc2ffe` (selck), `a5e04a0b` (mergesave), `load`.
- **Symptom under test:** v4 eval collapsed vs v3 — per-patient IoU 0.32→0.071, recall@0.25 54%→10%, FP 1%→26%.

---

## (a) VERDICT: The training/loss is almost certainly NOT the culprit.

**The decisive argument is a contradiction the training logs themselves expose.**

The v4 training log reports `eval_loss ≈ 0.33` (healthy, in line with v3's ~0.3 final loss per worklog line 40) and a neg-detect-rate of 0–2/10 (the model correctly stays silent on negatives during training).

Now look at what `eval_loss` actually measures in this code. In `WeightedTrainer.compute_loss`:

```python
w = (W_POS if pos else W_NEG) if model.training else 1.0   # NOT weighted at eval
loss = w * outputs.loss
if model.training and detect_pos is not None and LAMBDA_BCE > 0:
    ... loss = loss + LAMBDA_BCE * coef * BCE(diff, y)      # BCE only when training
```

Both the CE weighting **and** the BCE term are gated on `model.training`. During `Trainer.evaluate()` the model is in eval mode, so:

> **`eval_loss` is pure, unweighted cross-entropy over the entire answer span — including every coordinate token** (`<box>[[x1,y1,x2,y2],...]</box>`), since `build_train_example` unmasks the whole model turn (`labels[:, :prompt_len] = -100`, the rest is supervised).

This is the key. If v4 training had genuinely corrupted coordinate generation, the model would assign low probability to the correct coordinate tokens on the held-out `cal` split, and **`eval_loss` would be high** — not 0.33. A model that produces IoU 0.071 and 26% FP at eval time is, token-for-token, badly wrong about coordinates and about the detect/No decision; that disagreement would show up directly in teacher-forced CE on the same `cal` data.

Low `eval_loss` (teacher-forced, includes coords) + collapsed free-generation IoU/recall is **internally contradictory for a "training broke the weights" story.** The weights that produced eval_loss=0.33 cannot simultaneously be the weights that produce IoU=0.071 on overlapping data. The most parsimonious explanation is that **the weights evaluated at generation time are not the weights that produced eval_loss=0.33** — i.e. a reload/merge/checkpoint-selection problem, not a loss problem. This points firmly AWAY from the training math and TOWARD the eval/reload path (the other reviewer's domain). See (e) for the specific things that, if confirmed in the logs, nail this down.

Secondary support: the worklog already documents that the **v3** model (same optimizer, same vision full-FT fp32, same LRs, NO BCE) localizes well (IoU 0.62 on detected boxes, FP 1%). v4 changed exactly three things relative to v3: lowered W_POS (3→1.5), added the BCE-head, and added the checkpoint-selection + merge reordering. Of these, only the merge/selection reordering plausibly touches *which weights get evaluated*. The loss-function changes (BCE, W_POS) are gradient-shaping terms that, even if mis-tuned, degrade gracefully (more FP, or more abstention) — they do not produce simultaneous recall collapse, IoU collapse, AND FP explosion, which is the signature of evaluating a wrong/partially-loaded model.

---

## (b) Loss-code review — bugs found

I read the loss path line by line. **No correctness bug that would corrupt coordinates was found.** Details:

1. **`model.training` gating — CORRECT and important.** Both `w` and the BCE term are inside `if model.training`. This is exactly what makes best-by-loss selection valid and keeps `eval_loss` a clean CE signal. Confirmed.

2. **Off-by-one logit index — CORRECT.** `logit = outputs.logits[0, dp-1, :]` where `dp` is the first answer-token position. Position `t`'s logits predict token `t+1`, so `dp-1` is the position whose prediction is the first answer token (DETECT vs NO). The worklog notes this was a fixed bug; the fixed form is right.

3. **`diff = logit[DETECT_TOKEN_ID] - logit[NO_TOKEN_ID]`, `y=1` pos / `0` neg — CORRECT direction.** `BCE_with_logits(diff, 1)` pushes `diff` up (toward DETECT) on positives; `(diff, 0)` pushes it down on negatives. Asymmetry via `coef = BCE_POS_W(1.5)` on positives only is a deliberate recall-lean. Sign and asymmetry are right.

4. **W_POS/W_NEG application — CORRECT but coarse.** `w` is a scalar applied to the whole-sequence CE for that one example. With per-device batch size 1 and the custom `collate(f): return f[0]`, each step is a single example, so a single `pos` flag is well-defined. No bug. (Note: this means W_POS multiplies the *coordinate* CE too on positive examples, not just the detect decision — a slight inefficiency, not a corruption. It would, if anything, *help* coordinate fitting on positives, not hurt it.)

5. **`detect_pos` indexing — CORRECT.** `_detect_pos` is derived in `build_train_example` as the first non-masked label position, and re-validated in `train` by `_first_ans_tok` plus an **assert over 20 sampled examples** that pos→DETECT / neg→NO. If the token derivation were wrong, that assert would have aborted training. It did not (training ran to completion), so the BCE target tokens are sound.

6. **Gradient on the right tensor — YES.** The BCE flows from `outputs.logits` (live graph), not from a detached/saved tensor. Gradient reaches the LM head and back through shared layers, as intended.

**Net: the loss code is sound. No bug here explains the collapse.**

---

## (1) Could λ=2 BCE on ONE logit pair wreck IoU via shared-layer gradients?

**Very unlikely to be the primary cause, but λ=2 is on the high side and worth ablating.**

- The BCE term touches **two logit entries at one position**. Its gradient w.r.t. the LM-head rows for DETECT/NO tokens is local; the gradient that reaches *shared* transformer/vision layers is the backprop of a single scalar through the final hidden state at position `dp-1`. That is a tiny, low-rank signal compared to the full-sequence CE gradient (which supervises every coordinate token at every position).
- Mechanistically, for the BCE to "corrupt coordinate prediction," it would have to perturb shared representations enough to move coordinate-token logits at *other* positions. Possible in principle (shared trunk), but it would degrade *gradually* and would **raise eval_loss** — which it did not. So even if λ contributed pressure, it did not break the coordinate-fitting objective as measured.
- λ=2 means the detect-decision penalty can be up to ~2×1.5 = **3× the CE magnitude** at its peak (early training, when `diff` is wrong-signed and BCE is large). That is a genuinely strong nudge on the *first token's* logits and could, in a bad run, encourage the model to over-fire DETECT (consistent with the observed 26% FP if those weights were the ones evaluated). But again: this would not simultaneously collapse IoU on the boxes that *are* drawn — and the worklog's own root-cause for the FP/recall pattern is decision-side, not localization-side.

**Conclusion for (1):** λ=2 is plausibly too aggressive for FP control, but it is not a credible mechanism for IoU collapse given eval_loss stayed at 0.33.

## (2) CE weighting / optimizer / vision full-FT fp32 — degradation risk?

- **W_POS=1.5** is mild (down from v3's 3) and near-neutral. Not a degradation risk.
- **PagedAdamW8bit, LR_LLM=2e-4 (LoRA r=32), LR_VISION=1e-5 (full-FT vision, fp32):** this is the *exact* recipe that worked in v3/the "best so far" run (worklog lines 40, 129 — fp32 + low LR + 2 LR groups is the documented fix for vision-train NaN). It is a known-good configuration, not a new risk introduced in v4.
- **Catastrophic forgetting / overfit at 5–6 epochs:** a real generic concern for full-FT vision, but (i) it is identical to v3 which did not collapse, and (ii) overfitting would still keep teacher-forced `eval_loss` low on the held-out `cal` set only if it generalized — and a *forgetting* failure would actually *raise* eval_loss. The healthy eval_loss argues against catastrophic forgetting as the cause.

**Conclusion for (2):** optimizer/LR/dtype recipe is the proven v3 recipe. Not the likely culprit.

## (3) The eval_loss=0.33 contradiction — see (a). 

Stated there and front-and-center: low teacher-forced CE (incl. coordinates) is incompatible with the same weights generating IoU 0.071 / 26% FP. This is the single strongest signal and it points to reload/eval, not training.

## (4) Loss-code bugs — see (b). None that corrupt localization.

## (5) EPOCHS=5 but 6 checkpoints — off-by-one in eval cadence?

**Found a benign cadence quirk, not a corruption bug — but it has real consequences for checkpoint *selection*, which IS in the suspected eval/reload path.**

- `steps_per_epoch = len(train_ds) // GRAD_ACC`, `eval_steps = steps_per_epoch`, `num_train_epochs=5`. With integer flooring, the true number of optimizer steps is slightly more than `5 * steps_per_epoch` (the floor discards the remainder each epoch), so HF's step counter crosses an `eval_steps` boundary **6 times** over 5 epochs → 6 evals → `SaveEpochs` writes `epoch1..epoch6_trainable.pt`. This matches "EPOCHS=5 but 6 checkpoints." It is expected behavior of step-based eval with a floored cadence, **not** an off-by-one bug in the loss.
- **Why it matters anyway:** `epoch6` is a partial-epoch checkpoint (fewer than a full epoch's steps after epoch5's eval, depending on exact remainder). The selection cell (`a6bc2ffe`) ranks ALL six by Fβ+guardrail, and `SaveEpochs` also tracks best-by-loss across all six. If `epoch6` (or any late, possibly more FP-prone checkpoint) wins Fβ or best-by-loss and is then loaded via `load_state_dict(..., strict=False)`, the *selection/reload* mechanics — not the training — determine the evaluated model. `strict=False` is the load that the other reviewer should scrutinize: it **silently ignores key mismatches**, so a partial/empty load would produce a base-ish or half-trained model with exactly this collapse signature (low recall + bad IoU + FP up).

**Conclusion for (5):** the 6-vs-5 count is benign in origin but it feeds the suspect path. The risk is not "training ran an extra epoch and broke," it is "selection + `strict=False` reload may load the wrong/partial state."

---

## (c) λ=2 recommendation + ablation plan

Even though λ is not the prime suspect, it is the only safety knob and it is currently aggressive:

- **Recommend λ = 0.5–1.0** (start at **0.5**). Rationale: at λ=2 the detect penalty peaks at ~3× CE; that is enough to bias the first-token decision toward over-firing (FP-prone) before the guardrail catches it. A 0.5 setting still applies recall pressure (the worklog's goal) without dominating CE.
- **Ablation (cheap, decisive):**
  1. **λ=0 run** — pure CE + W_POS, BCE off. If recall is still ≥ v3 and IoU/FP recover, the collapse is *not* caused by BCE and the λ value is moot → confirms eval/reload hypothesis.
  2. **λ-sweep {0.5, 1.0, 2.0}** holding everything else fixed; plot eval_loss AND free-generation recall/IoU/FP per λ. If eval_loss is flat across λ but generation metrics swing wildly, that again localizes the problem to the generation/reload path, not the loss.
  3. **Same-weights consistency check** (most important): right after `trainer.train()` and after each `load_state_dict`, run the *same* `_box_only` inference on a fixed 10-slice probe and print recall/IoU. If the in-notebook PeftModel scores well but the merged/reloaded model scores badly, the loss is exonerated and the merge/`strict=False` reload is the bug.

---

## (d) What to check in the training logs to confirm/deny (decisive checklist)

1. **Per-epoch `eval_loss` series.** Confirm it is smooth and ~0.3 across epochs (no late spike). A flat/low series with collapsed generation = reload/eval bug. (Strong expectation: it is flat.)
2. **Per-epoch `neg detect-rate` line** (`[epoch~k] eval_loss=… | neg detect-rate=d/10`). 0–2/10 means the *trained* model abstains correctly on negatives — directly contradicts the 26% eval FP. If training says "abstains" and eval says "26% FP," the evaluated weights ≠ trained weights. **This single comparison is close to conclusive.**
3. **The selection table** printed by `a6bc2ffe`: `detR / rec@.5 / prec / FP / mIoU / Fb` per epoch checkpoint. If *every* checkpoint in that table already shows low recall / high FP, the collapse is real at selection time → look at how `epochK_trainable.pt` were saved/loaded (the `state_dict` only saves `requires_grad` params; LoRA+vision — verify nothing was dropped). If the table looks healthy but final eval is collapsed, the bug is downstream of selection (merge/save/predict).
4. **`unexpected_keys` / missing-keys counts** on every `load_state_dict(..., strict=False)` and on the merge (`_ld.unexpected_keys` is printed after best-by-loss load). Non-zero unexpected, or suspiciously large missing, on the *selected* checkpoint load = the smoking gun for a partial reload.
5. **DETECT/NO token print + the 20-sample assert** in `train`: confirm it printed all "OK" (no "<<< LỆCH"). If it aborted it would not have trained; if it printed OK, BCE targets are clean — close the "BCE learned noise" theory.
6. **`merge_and_unload` dtype**: vision was cast to fp32 for training but the base was loaded bf16 (`load` cell). Confirm the merged/saved model's dtype matches what predict reloads (worklog line 66 flags exactly this). A dtype/precision mismatch at merge is a localization-degrading candidate that lives in the *save/reload* path, not the loss.

---

## Bottom line

The v4 loss is correctly implemented and correctly gated to keep `eval_loss` a clean CE signal. **A healthy eval_loss of 0.33 (which includes coordinate tokens) is logically incompatible with the same weights generating IoU 0.071 / 26% FP**, so the training/loss is exonerated as the likely cause; the evidence points to the checkpoint-selection / `strict=False` reload / merge path. λ=2 is somewhat aggressive and should be reduced to ~0.5 and ablated, but it is not a credible mechanism for the IoU collapse. Confirm via the per-epoch `eval_loss` + `neg detect-rate` log lines and the `strict=False` key-mismatch counts.
