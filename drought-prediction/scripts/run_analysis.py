"""Run the extracted Baydhaba CDI prediction workflow."""

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from drought_prediction.data_cleaning import remove_quotes
from drought_prediction.predictive_analysis import forecast_cdi


def main() -> None:
    input_path = next((PROJECT_ROOT / "data").glob("export_indicator_data*.csv"))
    indicators = remove_quotes(pd.read_csv(input_path))
    baydhaba = indicators.loc[indicators["district"] == "Baydhaba"]
    print(forecast_cdi(baydhaba).to_string(index=False))


if __name__ == "__main__":
    main()