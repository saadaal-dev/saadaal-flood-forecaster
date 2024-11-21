import pandas as pd
import joblib
import numpy as np

# Open inputs CSV
inputs_df = pd.read_csv('inference_inputs.csv')
# Open model
model = joblib.load('model.pkl')
# Open PCA
pca = joblib.load('pca.pkl')
# Process inputs
values = []
for column in inputs_df.columns:
    if column != "day":
        temp = inputs_df[column].dropna().to_numpy()
        for element in temp:
            values.append(element)
X = np.array(values).reshape(1,-1)
X = pca.transform(X)
y = model.predict(X)
print(f"River level tomorrow: {y[0]} meters")