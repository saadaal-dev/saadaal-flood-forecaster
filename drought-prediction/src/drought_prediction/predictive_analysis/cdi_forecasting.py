"""Simple, explainable CDI forecasting models extracted from the notebook."""

import numpy as np
import pandas as pd


def prepare_indicator_data(indicator_dataframe: pd.DataFrame) -> pd.DataFrame:
    return (
        indicator_dataframe.loc[indicator_dataframe["indicator"].isin(["cdi", "rainfall"])]
        .assign(
            month=lambda data: pd.to_datetime(data["month"], errors="coerce")
            .dt.to_period("M").dt.to_timestamp(),
            value=lambda data: pd.to_numeric(data["value"], errors="coerce"),
        )
        .dropna(subset=["month", "value"])
        .pivot_table(index="month", columns="indicator", values="value", aggfunc="mean")
        .reset_index()
        .sort_values("month")
    )


def forecast_cdi(indicator_dataframe: pd.DataFrame, test_months: int = 6) -> pd.DataFrame:
    indicator_data = prepare_indicator_data(indicator_dataframe)
    required = {"month", "cdi", "rainfall"}
    if not required.issubset(indicator_data.columns):
        missing = ", ".join(sorted(required - set(indicator_data.columns)))
        raise ValueError(f"Missing required indicator columns: {missing}")

    cdi_data = indicator_data[["month", "cdi"]].dropna()
    predictor_data = (
        indicator_data[["month", "cdi", "rainfall"]].dropna()
        .assign(
            target_month=lambda data: data["month"] + pd.offsets.MonthBegin(1),
            log_rainfall=lambda data: np.log1p(data["rainfall"]),
        )
        .merge(
            cdi_data.rename(columns={"month": "target_month", "cdi": "target_cdi"}),
            on="target_month", how="inner",
        )
        .sort_values("target_month")
    )
    if len(predictor_data) <= test_months or len(predictor_data) < 3:
        raise ValueError("Not enough monthly observations for the requested holdout.")

    training_data = predictor_data.iloc[:-test_months]
    test_data = predictor_data.iloc[-test_months:].copy()
    persistence = test_data["cdi"].to_numpy()
    rainfall_predictions = []
    combined_predictions = []
    for position in range(len(training_data), len(predictor_data)):
        prior = predictor_data.iloc[:position]
        rainfall_slope, rainfall_intercept = np.polyfit(
            prior["log_rainfall"], prior["target_cdi"], 1
        )
        matrix = np.column_stack([np.ones(len(prior)), prior["cdi"], prior["log_rainfall"]])
        coefficients = np.linalg.lstsq(matrix, prior["target_cdi"], rcond=None)[0]
        row = predictor_data.iloc[position]
        rainfall_predictions.append(rainfall_intercept + rainfall_slope * row["log_rainfall"])
        combined_predictions.append(
            coefficients[0] + coefficients[1] * row["cdi"] + coefficients[2] * row["log_rainfall"]
        )

    predictions = {
        "Persistence": persistence,
        "Rainfall only": rainfall_predictions,
        "CDI and rainfall": combined_predictions,
    }
    model_mae = {
        name: float(np.abs(test_data["target_cdi"] - values).mean())
        for name, values in predictions.items()
    }
    selected_model = min(model_mae, key=model_mae.get)
    latest = predictor_data.iloc[-1]
    if selected_model == "Persistence":
        next_prediction = latest["cdi"]
    elif selected_model == "Rainfall only":
        slope, intercept = np.polyfit(predictor_data["log_rainfall"], predictor_data["target_cdi"], 1)
        next_prediction = intercept + slope * latest["log_rainfall"]
    else:
        matrix = np.column_stack([np.ones(len(predictor_data)), predictor_data["cdi"], predictor_data["log_rainfall"]])
        coefficients = np.linalg.lstsq(matrix, predictor_data["target_cdi"], rcond=None)[0]
        next_prediction = coefficients[0] + coefficients[1] * latest["cdi"] + coefficients[2] * latest["log_rainfall"]
    return pd.DataFrame({
        "month": [latest["target_month"]],
        "rainfall_used": [latest["rainfall"]],
        "predicted_cdi": [next_prediction],
        "selected_model": [selected_model],
        "test_mae": [model_mae[selected_model]],
    })