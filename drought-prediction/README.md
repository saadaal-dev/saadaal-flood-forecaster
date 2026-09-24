# Drought Prediction

This project extracts the drought data preparation and CDI forecasting work from
the exploratory notebook in the parent workspace.

## Structure

- `data/`: CSV inputs used by the analysis.
- `data_cleaning/`: reusable sensor and indicator cleaning helpers.
- `predictive_analysis/`: CDI forecasting and evaluation functions.
- `notebooks/drought_prediction_analysis.ipynb`: renamed copy of the original notebook.
- `scripts/run_analysis.py`: small command-line entry point for a Baydhaba forecast.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python scripts/run_analysis.py
```

The script expects the CSV files in `data/` and prints the selected forecast
model, its holdout MAE, and the next-month CDI prediction.