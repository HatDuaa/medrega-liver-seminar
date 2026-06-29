# Review: v4 eval collapse — root cause = unfaithful recovery from `best_trainable.pt`

**Date:** 2026-06-29
**Run:** `gemma4_v4_binary_loss`
**Notebook:** `seminar/code/medrega_finetune.ipynb`
**Symptom:** v4 eval collapsed vs v3 (same data/split). per-patient mean-IoU 0.32 → 0.071, recall@0.25 54% → 10%, recall@0.5 → 1%, FP per-patient 1% → 26%. Model still emits valid `<ref>liver tumor</ref><box>[[...]]</box>` format, boxes land roughly in-region but imprecise (per-slice IoU 0.0–0.49). High FP + near-random IoU = signature of a model that **barely learned the task** ≈ base / zero-shot behavior.

**Central contradiction:** training looked healthy (eval_loss ~0.33, neg-detect-rate 0–2/10 during training) but the EVALED model behaves like base. Conclusion: the **reconstructed model ≠ the actually-trained model**. The recovery cell `-ZYQq8xYEkuD` loaded weights that pass `assert unexpected_keys == 0` yet leave the model effectively at base.

---

## VERDICT (one line)

**v4 training is almost certainly FINE — the model was mis-loaded.** The trained deltas (LoRA + vision full-FT) never actually entered the merged model: the LoRA adapter stayed at init (lora_B = 0 → no-op) and/or the vision deltas were dropped, so `merge_and_unload()` folded a near-identity adapter into the base. Re-load `best_trainable.pt` correctly (or, better, re-run merge with name-verification) and the v3-level numbers should return. No evidence the training itself broke.

---

## Ranked root-cause hypotheses

### #1 (PRIME SUSPECT) — Saved trainable keys land in `missing_keys`, not `unexpected_keys`; assert passes while LoRA stays at init

**Why this is the prime suspect.** The recovery's only integrity check is:

```python
ld = model.load_state_dict(sd, strict=False)
assert len(ld.unexpected_keys) == 0
```

`strict=False` splits the diff into two disjoint lists:
- **`unexpected_keys`** = keys present in `sd` (the file) but **absent from the model**.
- **`missing_keys`** = keys present in the model but **absent from `sd`** (these silently keep their current/initialized values).

The assert ONLY guards `unexpected_keys`. It says nothing about `missing_keys`. So the failure mode is precisely:

> Every key in `sd` happens to be a subset of (or a prefix-shifted view that still resolves into) the model's key space → `unexpected_keys == 0` (assert passes), **but** the model's real LoRA / vision params were never written because the names didn't line up the way the loader expected → those params sit in `missing_keys` at their **initialization** value. For LoRA, init means `lora_A` = kaiming, **`lora_B` = 0**, so `BA = 0` and the adapter is a **no-op**. `merge_and_unload()` then folds `W + (alpha/r)·B·A = W + 0 = W` → the merged model **== base**. Result: valid format (base Gemma already speaks the template after a few in-context tokens), boxes vaguely in-region (vision encoder is base), near-random IoU, high FP. Exactly the observed signature.

**The concrete naming mechanism that makes this fire (the key-prefix shift).** `best_trainable.pt` was saved during training as:

```python
sd = {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad}
```

…where `model` at save time was **`get_peft_model(base)`** — a `PeftModelForCausalLM` wrapping the base. PEFT inserts a `base_model.model.` prefix on every name, and LoRA params are named like:

```
base_model.model.model.language_model.layers.0.self_attn.q_proj.lora_A.default.weight
base_model.model.model.language_model.layers.0.self_attn.q_proj.lora_B.default.weight
```

In the recovery cell the model is **also** `get_peft_model(...)`, so in principle the prefixes match. **BUT** there are three concrete ways the names diverge between train-time and recovery-time, any one of which routes the saved keys into `missing_keys`:

1. **`enable_input_require_grads()` ordering / hook param.** In *training* the order is `enable_input_require_grads()` → `get_peft_model(...)`. In *recovery* it is `model.enable_input_require_grads()` → `get_peft_model(...)`. Same order — good. But `enable_input_require_grads` registers a forward hook on the input embeddings; on some transformers/PEFT versions this is fine, on others it changes nothing in names. This one is low-risk; flagged only for completeness.

2. **PEFT / transformers version drift between the training session and the recovery session.** The recovery was run in a *fresh runtime* (the old one was killed by `unassign`). If the reinstalled `peft`/`transformers` differs by even a minor version, the **LoRA submodule naming or the `.default` adapter infix can change** (e.g. `lora_A.weight` vs `lora_A.default.weight`, or a different wrapper class inserting/removing a `.base_layer.` segment). Saved key `...q_proj.lora_A.default.weight` then has **no slot** in the new model (→ would be `unexpected`) OR the new model expects `...q_proj.lora_A.weight` which is **absent from the file** (→ `missing`). When the mismatch is "model expects a name the file doesn't have," it is **silent** and the assert passes. **This is the most plausible concrete trigger** given the fresh-runtime reinstall.

3. **Vision full-FT keys.** Saved vision keys are plain base names (`...vision_tower....weight`) and *should* match. But see #3-dtype below: if their dtype differs they may load-but-cast, or if a wrapper renamed them they go to `missing` too.

**The damning tell:** the training cell's own reload after training prints
`"unexpected={len(_ld.unexpected_keys)} (phải 0; missing lớn là BT)"` — i.e. the author already KNOWS missing-keys is normally large and chose to ignore it. In the *same-process* reload right after training, large `missing` is benign (the non-trainable base is simply not in `sd`). But in the *recovery* process the author copied the same "ignore missing" mindset into a context where a large/poisoned `missing` set is FATAL, because there the missing keys include the **LoRA and vision deltas themselves**.

**How to verify (run in Colab, right after the `load_state_dict` line, BEFORE the assert/merge):**

```python
ld = model.load_state_dict(sd, strict=False)
print("unexpected:", len(ld.unexpected_keys))
print("missing   :", len(ld.missing_keys))

# (a) Did any TRAINED key fail to load? Saved keys that are NOT in the model = unexpected;
#     saved keys that the model HAS but were overwritten correctly = good.
model_keys = set(dict(model.named_parameters()).keys())
saved_keys = set(sd.keys())
not_in_model = saved_keys - model_keys          # these silently did NOTHING
print("saved keys NOT present in model:", len(not_in_model))
for k in list(not_in_model)[:10]: print("   ", k)

# (b) Are any lora_ keys sitting in missing_keys (=> stayed at init)?
lora_missing = [k for k in ld.missing_keys if "lora_" in k.lower()]
print("lora_ keys in MISSING:", len(lora_missing), lora_missing[:5])

# (c) THE decisive test — is lora_B actually non-zero after load?
import torch
for n, p in model.named_parameters():
    if "lora_B" in n:
        print("lora_B sample:", n, "||", float(p.float().abs().sum()))
        break   # if this is ~0.0, the adapter is a NO-OP => model == base => collapse explained
```

**Decision rule:** if `saved keys NOT present in model > 0` (esp. any `lora_`), **OR** the sampled `lora_B` abs-sum ≈ 0, hypothesis #1 is **confirmed**. (A correctly-loaded trained adapter has `lora_B` with a clearly non-zero norm.)

---

### #2 — `lora_alpha` / scaling mismatch in recovery vs training

Direct read of both cells:

- Training: `LoraConfig(r=32, lora_alpha=64, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM", target_modules=r".*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)$")`
- Recovery: `LoraConfig(r=32, lora_alpha=64, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM", target_modules=<same regex>)`

**They are identical.** So scaling/alpha is NOT the cause. Note this also means the LoRA module *structure* and target set are correct — which is exactly why the keys mostly match and `unexpected==0` — making #1's silent-missing path the live failure, not a structural rejection. **Ruled out** as a standalone cause; it only matters as evidence that #1's mechanism (right structure, wrong fill) is what's in play.

---

### #3 — dtype / float-order corruption of vision weights

Order in recovery: `get_peft_model` → loop sets VIS params `.float()` + `requires_grad` → **then** `load_state_dict(sd)`. This is the *correct* order (vision cast to float32 BEFORE load, matching the float32 dtype of the saved vision tensors), so the vision keys should match by dtype and load.

Two residual risks:
- If any VIS key was renamed by the wrapper (same mechanism as #1), the float32 vision deltas land in `missing` and the model keeps base bf16 vision → contributes to collapse. This is really a facet of #1.
- `merge_and_unload()` on a model whose base is bf16 but whose vision is float32 is fine (vision isn't part of the LoRA merge), but verify no silent down-cast clipped values.

**This is secondary to #1** and largely a sub-case of it. Verify with the same key-set diff in #1 plus:
```python
for n,p in model.named_parameters():
    if "vision_tower" in n.lower(): print(n, p.dtype); break
```
**Likelihood: medium-low as an independent cause; medium as a co-symptom of #1.**

---

### #4 — `best_trainable.pt` is itself a degenerate/near-base checkpoint

`SaveEpochs` writes `best_trainable.pt` = the epoch with the lowest `eval_loss`. The training log showed eval_loss ~0.33 and healthy neg-detect-rate, so the BEST epoch was a *good* epoch. For this to explain the collapse, the file on disk would have to be wrong content (e.g. epoch1 saved into the BEST slot, or a truncated write). Possible but unlikely given the reported loss. **Likelihood: low.** Cheap to rule out: `epoch{k}_trainable.pt` files also exist — load each and eval; if ALL of them collapse identically, the problem is the *loader* (#1), not the *file* (#4). (Strong tie-breaker: if every epoch ckpt collapses the same way, #1 is proven and #4 is dead.)

---

### #5 — Eval-pipeline parsing bug inflating badness

Reviewed `sec8`/`sec9`/`util`. `parse_boxes` is robust and unit-tested (`<box>[[...]]`, xywh json, negative phrasing), `match_boxes` is Hungarian, `box_metrics` is standard. The `diag` cell prints **real model text** with **non-zero IoU** boxes — the model is clearly alive and emitting plausible boxes, just imprecise. A parsing bug would more likely zero out IoU entirely or break format, not produce the "vaguely-right but imprecise + high FP" base-like profile. **Ruled out** as the cause of collapse. (The eval is faithfully reporting a genuinely degraded model.)

---

## Top-hypothesis confirmation: exact Colab diagnostic (copy/paste)

Run this as a standalone cell *after re-running the recovery up to and including* `load_state_dict`, replacing the bare assert:

```python
import torch
ld = model.load_state_dict(sd, strict=False)
mk = set(dict(model.named_parameters()).keys())
sk = set(sd.keys())

print("unexpected:", len(ld.unexpected_keys), "| missing:", len(ld.missing_keys))
print("saved-but-NOT-in-model (silently ignored):", len(sk - mk))
for k in list(sk - mk)[:8]: print("   ignored:", k)

lora_missing = [k for k in ld.missing_keys if "lora_" in k.lower()]
print("lora_ keys left at INIT (in missing):", len(lora_missing))
for k in lora_missing[:5]: print("   init:", k)

# decisive: a correctly-loaded adapter has non-zero lora_B
b = next(p for n,p in model.named_parameters() if "lora_B" in n)
print("lora_B abs-sum:", float(b.float().abs().sum()), "(≈0 => adapter is NO-OP => model==base)")

# cross-check one saved-vs-model name pair
print("sample SAVED key  :", sorted(k for k in sk if 'lora_A' in k)[0])
print("sample MODEL key  :", sorted(k for k in mk if 'lora_A' in k)[0])
```

If `saved-but-NOT-in-model > 0`, or `lora_B abs-sum ≈ 0`, or the two sample key strings differ → **#1 confirmed**.

---

## THE FIX

The goal: make `best_trainable.pt`'s trained tensors actually land on the matching params, then merge. Two levels:

### Fix A — hard-fail the silent path (minimal, always do this)

Replace the recovery's weak assert with a check that the trained keys actually applied:

```python
sd = torch.load(PT, map_location="cpu")
mk = set(dict(model.named_parameters()).keys())
sk = set(sd.keys())
ignored = sk - mk
ld = model.load_state_dict(sd, strict=False)

assert len(ld.unexpected_keys) == 0, f"unexpected={ld.unexpected_keys[:5]}"
assert len(ignored) == 0, f"{len(ignored)} TRAINED keys did NOT match the model: {list(ignored)[:5]}"
# every saved (trained) key MUST have been consumed; none may be in missing
still_missing_trained = [k for k in ld.missing_keys if k in sk]
assert not still_missing_trained, f"trained keys stayed at init: {still_missing_trained[:5]}"
b = next(p for n,p in model.named_parameters() if "lora_B" in n)
assert float(b.float().abs().sum()) > 0, "lora_B is zero -> adapter no-op, load FAILED silently"
print("Load verified: all trained keys applied, lora_B non-zero.")
```

This converts the silent collapse into a loud failure so you never merge a no-op again.

### Fix B — make the names line up (the actual repair)

If Fix A's asserts fire because of a name prefix/infix mismatch (PEFT version drift), realign the keys before loading. Pick whichever the diagnostic shows:

```python
# Case 1: file has '...lora_A.default.weight' but model wants '...lora_A.weight' (or vice-versa)
def remap(sd, model):
    mk = set(dict(model.named_parameters()).keys())
    out = {}
    for k, v in sd.items():
        if k in mk:
            out[k] = v; continue
        for cand in (k.replace(".default.", "."), k.replace("lora_A.", "lora_A.default.").replace("lora_B.","lora_B.default."),
                     k.replace("base_model.model.", ""), "base_model.model." + k):
            if cand in mk:
                out[cand] = v; break
        else:
            raise KeyError(f"cannot map saved key: {k}")
    return out

sd = remap(torch.load(PT, map_location="cpu"), model)
ld = model.load_state_dict(sd, strict=False)   # now re-run Fix A asserts
```

### Fix C — guarantee version parity (root prevention)

The recovery ran in a fresh runtime after the original died. Before reconstructing, pin the **exact** `peft` and `transformers` versions used during training (record them in the train cell going forward), then reconstruct. Identical versions ⇒ identical PEFT naming ⇒ keys match ⇒ no silent missing.

### Then

After a verified load (`lora_B` non-zero, zero ignored trained keys), run `merge_and_unload()` + `save_pretrained` as the recovery already does, then re-run `diag` (5 test images) — IoU should jump back toward v3 levels, and FP should drop. That confirms the fix end-to-end.

---

## Summary of what to tell the user

- The collapse is a **loading artifact, not a training failure**. `best_trainable.pt` is good; the recovery loaded it onto mismatched parameter names so the LoRA stayed at init (lora_B = 0 → no-op) and merged into base.
- `assert unexpected_keys == 0` is **insufficient** — it ignores `missing_keys`, which is exactly where the trained deltas silently went.
- Confirm with the `lora_B abs-sum` test (≈0 = proven). Fix by re-loading with key-match asserts (Fix A) + name remap / version pin (Fix B/C), then re-merge.
- Expect v3-level metrics back after a verified reload — no retrain needed.
