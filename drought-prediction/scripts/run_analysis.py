"""Run both extracted Baydhaba CDI prediction workflows.

The script reproduces the notebook preparation steps without plotting: it
cleans the indicator export, prepares the BAIDOA_MOH sensor dataframe, builds
weighted wind, and prints both model forecasts with their holdout MAE.
"""

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from drought_prediction.data_cleaning import (
    pivot_sensor_values,
    remove_error_rows,
    remove_quotes,
)
from drought_prediction.predictive_analysis import forecast_cdi


def main() -> None:
    # Indicator data supplies the Baydhaba CDI and rainfall history used by the
    # rainfall-context model.
    data_path = PROJECT_ROOT / "data"
    indicators = remove_quotes(
        pd.read_csv(next(data_path.glob("export_indicator_data*.csv")))
    )
    baydhaba = indicators.loc[indicators["district"] == "Baydhaba"]

    # Sensor data supplies the independent BAIDOA_MOH weather model features.
    sensor_data = remove_quotes(
        pd.read_csv(next(data_path.glob("export_sensor_readings_*.csv")))
    )
    sensor_data, _ = remove_error_rows(sensor_data)
    station_data = sensor_data.loc[sensor_data["station_id"] == "BAIDOA_MOH"]
    sensor_pivot = pivot_sensor_values(station_data)
    sensor_pivot[["00WD", "00WS"]] = sensor_pivot[["00WD", "00WS"]].apply(
        pd.to_numeric, errors="coerce"
    )
    # Preserve the notebook's weighted-wind definition before dropping its raw
    # direction and speed columns.
    sensor_pivot["WNDW"] = sensor_pivot["00WD"] * sensor_pivot["00WS"]
    weather_data = sensor_pivot.drop(columns=["00WD", "00WS"])

    print(forecast_cdi(weather_data, baydhaba).to_string(index=False))


if __name__ == "__main__":
    main()