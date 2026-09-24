"""Cleaning and aggregation helpers for sensor and indicator data.

The exported sensor files contain quoted identifiers, mixed numeric/text values,
and sentinel values for failed readings. These helpers make those files usable
for monthly CDI prediction while retaining the original dataframe structure.
"""

import re

import numpy as np
import pandas as pd


def create_station_datasets(dataframe: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split sensor readings into one dataframe per normalized station ID."""
    station_datasets = {}
    normalized_station_ids = dataframe["station_id"].astype(str).str.strip("'\"")
    for station_id in normalized_station_ids.dropna().unique():
        station_label = re.sub(r"[^A-Za-z0-9_]+", "_", station_id).strip("_")
        station_datasets[f"df_{station_label}"] = dataframe.loc[
            normalized_station_ids == station_id
        ].copy()
    return station_datasets


def remove_error_rows(
    source_df: pd.DataFrame, error_df: pd.DataFrame | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Remove ``---`` and ``-999`` sensor readings and collect them separately.

    The source exports use both string and numeric representations, so values
    are normalized before the error mask is calculated. The returned error
    dataframe keeps the rejected rows available for quality-control reporting.
    """
    normalized_values = source_df["value"].map(
        lambda value: value.strip("'\"") if isinstance(value, str) else value
    )
    numeric_values = pd.to_numeric(normalized_values, errors="coerce")
    error_mask = normalized_values.eq("---") | numeric_values.eq(-999)
    removed_rows = source_df.loc[error_mask].copy()
    cleaned_source_df = source_df.loc[~error_mask].copy()
    if error_df is None:
        error_df = pd.DataFrame(columns=source_df.columns)
    return cleaned_source_df, pd.concat([error_df, removed_rows], ignore_index=True)


def remove_quotes(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Remove export-layer single or double quotes from every string field."""
    cleaned_dataframe = dataframe.copy()
    for column in cleaned_dataframe.columns:
        cleaned_dataframe[column] = cleaned_dataframe[column].map(
            lambda value: value.strip("'\"") if isinstance(value, str) else value
        )
    return cleaned_dataframe


def clean_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normalize quoted fields, sensor dates, and numeric sensor values."""
    cleaned_dataframe = remove_quotes(dataframe)
    if "original_date" in cleaned_dataframe:
        cleaned_dataframe["original_date"] = pd.to_datetime(
            cleaned_dataframe["original_date"], format="%Y/%m/%d", errors="coerce"
        )
    if "value" in cleaned_dataframe:
        cleaned_dataframe["value"] = pd.to_numeric(
            cleaned_dataframe["value"], errors="coerce"
        )
    return cleaned_dataframe


def pivot_sensor_values(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Turn one row per sensor reading into one row per timestamp.

    Sensor IDs become columns so downstream aggregation and machine-learning
    code can select weather variables directly. Duplicate readings at one
    timestamp are reduced to the first available value.
    """
    return (
        dataframe.pivot_table(
            index=["original_date", "original_time"],
            columns="sensor_id",
            values="value",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(columns=None)
    )


def aggregate_sensor_values_by_day(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Aggregate sensor readings by day using rules tied to sensor meaning.

    Atmospheric measurements use means, rainfall and solar radiation use sums,
    and wind direction uses a circular mean so directions near 0/360 degrees do
    not produce an artificial average near 180 degrees.
    """
    daily_dataframe = dataframe.copy()
    daily_dataframe["original_date"] = pd.to_datetime(
        daily_dataframe["original_date"], errors="coerce"
    ).dt.normalize()
    # Each sensor's physical meaning determines whether daily values are means,
    # totals, or circular directional averages.
    aggregation_rules = {
        "00AP": "mean", "00AT": "mean", "00DP": "mean", "00RH": "mean",
        "00WD": "circular_mean", "00WS": "mean", "RAIN": "sum", "SOLR": "sum",
    }
    sensor_columns = [column for column in aggregation_rules if column in daily_dataframe]
    daily_dataframe[sensor_columns] = daily_dataframe[sensor_columns].apply(
        pd.to_numeric, errors="coerce"
    )

    def circular_mean(values):
        radians = pd.Series(values).dropna().to_numpy() * np.pi / 180
        if len(radians) == 0:
            return np.nan
        angle = np.degrees(np.arctan2(np.sin(radians).mean(), np.cos(radians).mean())) % 360
        return 0.0 if np.isclose(angle, 360.0) else angle

    aggregated = {}
    for column in sensor_columns:
        rule = aggregation_rules[column]
        aggregated[column] = daily_dataframe.groupby("original_date")[column].agg(
            circular_mean if rule == "circular_mean" else rule
        )
    return pd.DataFrame(aggregated).reset_index()


def calculate_column_correlations(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Calculate pairwise correlations for numeric columns only."""
    return dataframe.select_dtypes(include="number").corr()