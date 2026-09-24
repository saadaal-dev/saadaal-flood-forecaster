"""Machine-learning CDI forecasts extracted from the analysis notebook."""

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error


def prepare_indicator_data(indicator_dataframe: pd.DataFrame) -> pd.DataFrame:
    return (
        indicator_dataframe.loc[
            indicator_dataframe["indicator"].isin(["cdi", "rainfall"])
        ]
        .assign(
            month=lambda data: pd.to_datetime(data["month"], errors="coerce")
            .dt.to_period("M")
            .dt.to_timestamp(),
            value=lambda data: pd.to_numeric(data["value"], errors="coerce"),
        )
        .dropna(subset=["month", "value"])
        .pivot_table(
            index="month",
            columns="indicator",
            values="value",
            aggfunc="mean",
        )
        .reset_index()
        .sort_values("month")
    )


def _monthly_cdi(indicator_dataframe: pd.DataFrame) -> pd.DataFrame:
    indicator_data = prepare_indicator_data(indicator_dataframe)
    if "cdi" not in indicator_data.columns:
        raise ValueError("Indicator data must contain CDI values.")
    return indicator_data[["month", "cdi"]].dropna()


def _validate_holdout(dataframe: pd.DataFrame, test_months: int) -> None:
    if test_months < 1 or len(dataframe) <= test_months:
        raise ValueError("Not enough monthly observations for the requested holdout.")


def _monthly_weather(weather_dataframe: pd.DataFrame) -> pd.DataFrame:
    feature_columns = ["00AT", "00RH", "WNDW", "RAIN"]
    missing = [column for column in feature_columns if column not in weather_dataframe]
    if missing:
        raise ValueError(f"Weather data is missing required features: {missing}")

    weather_data = weather_dataframe.copy()
    weather_data["month"] = pd.to_datetime(
        weather_data["original_date"], errors="coerce"
    ).dt.to_period("M").dt.to_timestamp()
    weather_data[feature_columns] = weather_data[feature_columns].apply(
        pd.to_numeric, errors="coerce"
    )
    return (
        weather_data.groupby("month", as_index=False)
        .agg({"00AT": "mean", "00RH": "mean", "WNDW": "mean", "RAIN": "sum"})
        .dropna(subset=feature_columns)
    )


def forecast_weather_cdi(
    weather_dataframe: pd.DataFrame,
    indicator_dataframe: pd.DataFrame,
    test_months: int = 6,
) -> pd.DataFrame:
    """Forecast CDI from monthly BAIDOA_MOH weather features."""
    feature_columns = ["00AT", "00RH", "WNDW", "RAIN"]
    monthly_weather = _monthly_weather(weather_dataframe)
    cdi_data = _monthly_cdi(indicator_dataframe)
    model_data = (
        monthly_weather.assign(
            target_month=lambda data: data["month"] + pd.offsets.MonthBegin(1)
        )
        .merge(
            cdi_data.rename(columns={"month": "target_month", "cdi": "target_cdi"}),
            on="target_month",
            how="inner",
        )
        .sort_values("target_month")
    )
    _validate_holdout(model_data, test_months)

    X = model_data[feature_columns]
    y = model_data["target_cdi"]
    X_train, X_test = X.iloc[:-test_months], X.iloc[-test_months:]
    y_train, y_test = y.iloc[:-test_months], y.iloc[-test_months:]
    model = RandomForestRegressor(
        n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)
    test_mae = mean_absolute_error(y_test, model.predict(X_test))

    model.fit(X, y)
    latest_weather = monthly_weather.sort_values("month").iloc[-1]
    next_month = latest_weather["month"] + pd.offsets.MonthBegin(1)
    next_prediction = model.predict(latest_weather[feature_columns].to_frame().T)[0]
    return pd.DataFrame(
        {
            "forecast_source": ["BAIDOA_MOH weather"],
            "month": [next_month],
            "predicted_cdi": [next_prediction],
            "model": ["RandomForestRegressor"],
            "features": [", ".join(feature_columns)],
            "test_mae": [test_mae],
        }
    )


def forecast_rainfall_cdi(
    indicator_dataframe: pd.DataFrame,
    test_months: int = 6,
) -> pd.DataFrame:
    """Forecast CDI from rainfall and the current month's CDI value."""
    indicator_data = prepare_indicator_data(indicator_dataframe)
    required = {"month", "cdi", "rainfall"}
    if not required.issubset(indicator_data.columns):
        missing = ", ".join(sorted(required - set(indicator_data.columns)))
        raise ValueError(f"Indicator data is missing required columns: {missing}")

    model_data = (
        indicator_data[["month", "cdi", "rainfall"]]
        .dropna()
        .assign(
            log_rainfall=lambda data: np.log1p(data["rainfall"].clip(lower=0)),
            target_month=lambda data: data["month"] + pd.offsets.MonthBegin(1),
        )
        .merge(
            indicator_data[["month", "cdi"]].rename(
                columns={"month": "target_month", "cdi": "target_cdi"}
            ),
            on="target_month",
            how="inner",
        )
        .sort_values("target_month")
    )
    _validate_holdout(model_data, test_months)

    feature_columns = ["rainfall", "log_rainfall", "cdi"]
    X = model_data[feature_columns]
    y = model_data["target_cdi"]
    X_train, X_test = X.iloc[:-test_months], X.iloc[-test_months:]
    y_train, y_test = y.iloc[:-test_months], y.iloc[-test_months:]
    model = GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=0.03,
        max_depth=2,
        loss="huber",
        random_state=42,
    )
    model.fit(X_train, y_train)
    test_mae = mean_absolute_error(y_test, model.predict(X_test))

    model.fit(X, y)
    latest = indicator_data.dropna(subset=["cdi", "rainfall"]).iloc[-1]
    prediction_input = pd.DataFrame(
        {
            "rainfall": [latest["rainfall"]],
            "log_rainfall": [np.log1p(max(latest["rainfall"], 0))],
            "cdi": [latest["cdi"]],
        }
    )
    next_month = latest["month"] + pd.offsets.MonthBegin(1)
    next_prediction = model.predict(prediction_input)[0]
    return pd.DataFrame(
        {
            "forecast_source": ["Indicator rainfall + current CDI"],
            "month": [next_month],
            "predicted_cdi": [next_prediction],
            "model": ["GradientBoostingRegressor"],
            "features": [", ".join(feature_columns)],
            "test_mae": [test_mae],
        }
    )


def forecast_cdi(
    weather_dataframe: pd.DataFrame,
    indicator_dataframe: pd.DataFrame,
    test_months: int = 6,
) -> pd.DataFrame:
    """Return both weather-based and rainfall-context CDI forecasts."""
    return pd.concat(
        [
            forecast_weather_cdi(weather_dataframe, indicator_dataframe, test_months),
            forecast_rainfall_cdi(indicator_dataframe, test_months),
        ],
        ignore_index=True,
    )