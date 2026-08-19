# src/training

Not built yet. This is where model-training scripts will live once
we start on the ML stage (e.g. `train_price_model.py`, hyperparameter
search, cross-validation setup).

When you get here, pull your feature list from
`config.column_manifest.TRAINING_FEATURES` rather than hand-listing
columns -- it's already curated to exclude the target and every
analysis-only / leakage-risk column (see
`config/column_manifest.py` and the "Target leakage" section of the
root README for why those are excluded).

Trained artifacts should be saved under `saved models/`.
