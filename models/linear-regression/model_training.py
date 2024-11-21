# Imports
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn import linear_model
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.decomposition import PCA
import joblib

station_jowhar_river_level_df = pd.read_csv('data/Jowhar_river_station.csv', parse_dates=['date'], date_format="%d/%m/%Y")
rainfall_ethiopia_gabredarre_df = pd.read_csv('data/Ethiopia_Gabredarre_Fafen_river_midpoint_historical_weather_daily_2024-11-19.csv', parse_dates=['date'], date_format="%Y-%m-%d %H:%M:%S+00:00")
rainfall_ethiopia_gode_df = pd.read_csv('data/Ethiopia_Gode_city_historical_weather_daily_2024-11-19.csv', parse_dates=['date'], date_format="%Y-%m-%d %H:%M:%S+00:00")
rainfall_ethiopia_haren_df = pd.read_csv('data/Ethiopia_Haren_Fafen_river_source_historical_weather_daily_2024-11-19.csv', parse_dates=['date'], date_format="%Y-%m-%d %H:%M:%S+00:00")
rainfall_jowhar_df = pd.read_csv('data/historical_weather_daily_2024-11-12.csv', parse_dates=['date'], date_format="%Y-%m-%d %H:%M:%S+00:00")
rainfall_jowhar_df = rainfall_jowhar_df.drop(columns=['Unnamed: 0'])
rainfall_ethiopia_haren_df = rainfall_ethiopia_haren_df.drop(columns=['Unnamed: 0'])
rainfall_ethiopia_gabredarre_df = rainfall_ethiopia_gabredarre_df.drop(columns=['Unnamed: 0'])
rainfall_ethiopia_gode_df = rainfall_ethiopia_gode_df.drop(columns=['Unnamed: 0'])

# Preprocessing

mask = ((station_jowhar_river_level_df.date >= '2021-11-10') & (station_jowhar_river_level_df.date <= '2024-11-10'))
station_jowhar_river_level_df = station_jowhar_river_level_df.loc[mask]
# Drop columns
rainfall_jowhar_df = rainfall_jowhar_df[['date', 'precipitation_sum']]
rainfall_ethiopia_gode_df = rainfall_ethiopia_gode_df[['date', 'precipitation_sum']]
rainfall_ethiopia_gabredarre_df = rainfall_ethiopia_gabredarre_df[['date', 'precipitation_sum']]
rainfall_ethiopia_haren_df = rainfall_ethiopia_haren_df[['date', 'precipitation_sum']]
# Rename columns
rainfall_jowhar_df = rainfall_jowhar_df.rename(columns={'precipitation_sum': 'precipitation_sum_jowhar'})
rainfall_ethiopia_gode_df = rainfall_ethiopia_gode_df.rename(columns={'precipitation_sum': 'precipitation_sum_gode'})
rainfall_ethiopia_gabredarre_df = rainfall_ethiopia_gabredarre_df.rename(columns={'precipitation_sum': 'precipitation_sum_gabredarre'})
rainfall_ethiopia_haren_df = rainfall_ethiopia_haren_df.rename(columns={'precipitation_sum': 'precipitation_sum_haren'})
# Date formating
rainfall_jowhar_df['date'] = rainfall_jowhar_df['date'].dt.strftime('%Y-%m-%d')
rainfall_ethiopia_gode_df['date'] = rainfall_ethiopia_gode_df['date'].dt.strftime('%Y-%m-%d')
rainfall_ethiopia_gabredarre_df['date'] = rainfall_ethiopia_gabredarre_df['date'].dt.strftime('%Y-%m-%d')
rainfall_ethiopia_haren_df['date'] = rainfall_ethiopia_haren_df['date'].dt.strftime('%Y-%m-%d')
station_jowhar_river_level_df = station_jowhar_river_level_df[['date', 'level(m)']]
# Ensure 'date' columns are in datetime format
station_jowhar_river_level_df['date'] = pd.to_datetime(station_jowhar_river_level_df['date'])
rainfall_jowhar_df['date'] = pd.to_datetime(rainfall_jowhar_df['date'])
rainfall_ethiopia_gode_df['date'] = pd.to_datetime(rainfall_ethiopia_gode_df['date'])
rainfall_ethiopia_gabredarre_df['date'] = pd.to_datetime(rainfall_ethiopia_gabredarre_df['date'])
rainfall_ethiopia_haren_df['date'] = pd.to_datetime(rainfall_ethiopia_haren_df['date'])
# Shifting precipitation and enrinching
shift = 20
for i in range(1,shift):
    rainfall_jowhar_df[f'precipitation_sum_jowhar_shift_{i}'] = rainfall_jowhar_df['precipitation_sum_jowhar'].shift(i)
    rainfall_ethiopia_gode_df[f'precipitation_sum_gode_shift_{i}'] = rainfall_ethiopia_gode_df['precipitation_sum_gode'].shift(i)
    rainfall_ethiopia_gabredarre_df[f'precipitation_sum_gabredarre_shift_{i}'] = rainfall_ethiopia_gabredarre_df['precipitation_sum_gabredarre'].shift(i)
    rainfall_ethiopia_haren_df[f'precipitation_sum_haren_shift_{i}'] = rainfall_ethiopia_haren_df['precipitation_sum_haren'].shift(i)
# Shift river level
level_shift = 2
for i in range(1, shift+1):
    station_jowhar_river_level_df[f"level(m)_shift_{i}"] = station_jowhar_river_level_df['level(m)'].shift(i)
# Merge the dataframes
merged_df = pd.merge(rainfall_jowhar_df, station_jowhar_river_level_df, on='date', how='left')
merged_df = pd.merge(merged_df, rainfall_ethiopia_gode_df, on='date', how='left')
merged_df = pd.merge(merged_df, rainfall_ethiopia_gabredarre_df, on='date', how='left')
merged_df = pd.merge(merged_df, rainfall_ethiopia_haren_df, on='date', how='left')
split_index = merged_df[merged_df.date == '2023-10-01'].iloc[0].name
merged_df = merged_df.dropna()
dates = merged_df.date.to_numpy()
arrays = []
Y = merged_df['level(m)'].to_numpy()
for column in merged_df.columns:
    if column != 'level(m)' and column != 'date':
        arrays.append(merged_df[column].to_numpy())

# Linear regression

# Create the X matrix concatenating each array in arrays for the linear regression
for array in arrays:
    array = array
X = np.concatenate([array.reshape(-1, 1) for array in arrays], axis=1)

# Apply PCA on the input to only keep the relevent features
pca = PCA(n_components=42)
X = pca.fit_transform(X)
# Save the PCA model
joblib.dump(pca, 'pca.pkl')
dates_test = dates[:-split_index]
dates_train = dates[-split_index:]
# Split the data into training/testing sets
X_train = X[:-split_index]
X_test = X[-split_index:]
# Split the targets into training/testing sets
y_train = Y[:-split_index]
y_test = Y[-split_index:]
# Create linear regression object
regr = linear_model.LinearRegression()
# Train the model using the training sets
regr.fit(X_train, y_train)
# Make predictions using the testing set
y_pred = regr.predict(X_test)
# The coefficients
print("Coefficients: \n", regr.coef_)
# The mean squared error
print("Mean squared error: %.2f" % mean_squared_error(y_test, y_pred))
# The coefficient of determination: 1 is perfect prediction
print("Coefficient of determination: %.2f" % r2_score(y_test, y_pred))

# Optional plots: Plot y_test and y_pred
# plt.plot(dates_train, y_test, color="blue", linewidth=1)
# plt.plot(dates_train, y_pred, color="red", linewidth=1)

# plt.show()

# Save the model
joblib.dump(regr, 'model.pkl')
