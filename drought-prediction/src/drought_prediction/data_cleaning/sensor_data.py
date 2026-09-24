"""Cleaning and aggregation helpers for sensor and indicator data."""

import re

import numpy as np
import pandas as pd


def create_station_datasets(dataframe: pd.DataFrame) -> dict[str, pd.DataFrame]:
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
    cleaned_dataframe = dataframe.copy()
    for column in cleaned_dataframe.columns:
        cleaned_dataframe[column] = cleaned_dataframe[column].map(
            lambda value: value.strip("'\"") if isinstance(value, str) else value
        )
    return cleaned_dataframe


def clean_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
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
    daily_dataframe = dataframe.copy()
    daily_dataframe["original_date"] = pd.to_datetime(
        daily_dataframe["original_date"], errors="coerce"
    ).dt.normalize()
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
    return dataframe.select_dtypes(include="number").corr()