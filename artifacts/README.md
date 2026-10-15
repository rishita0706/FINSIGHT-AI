# Generated artifacts

Evaluation reports and optional model artifacts are generated locally. They are not checked in by default.

- `python scripts/train_categorizer.py` writes a synthetic evaluation report.
- Add `--save-artifact` to write the optional local `categorizer-v1.joblib`.

Model artifact files are ignored by Git and should be regenerated from the documented synthetic dataset.
