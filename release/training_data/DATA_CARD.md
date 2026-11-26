# CRAG-MM P5 Training Data

Generated: 2026-11-24

## Scope

- Development source positions: `0–399` only.
- External held-out positions: `400–599`; excluded from every output file.
- Images are referenced by repository-relative path and are not duplicated.
- Train/dev split is stable by SHA-256 of `session_id`.

## Counts

- SFT records: 1413
- Preference records: 368
- Hard negatives: 91
- Train/dev SFT: 1087 / 326

## Label policy

- Ground-truth text appears only as an assistant target or preference `chosen`, never as an explicitly named input field.
- Lookup/comparison answers without matching retrieved evidence are converted to `I don't know.` targets.
- OCR labels are weak labels from the structured Llama pass and require manual sampling before training.
- Wrong model answers are retained only as `rejected` or hard-negative examples.

## Files

See `manifest.json` for counts, byte sizes and SHA-256 values.

## Training caution

Do not train on positions 400–599. Use them only once for held-out evaluation after the adapter and refusal threshold are frozen.
