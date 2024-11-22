import pandas as pd

from prophet import Prophet
from prophet.serialize import model_to_json, model_from_json


def serialize_to_json(m, output_model_path):
    with open(output_model_path, 'w') as fout:
        fout.write(model_to_json(m))  # Save model


def train_001(train_df):
    # Initialize the Prophet model
    m = Prophet(weekly_seasonality=False, growth='flat')

    # Add the regressors to the model
    for r in [c for c in train_df.columns if c not in ["y", "ds"]]:
        m.add_regressor(r)

    # Fit the model
    m.fit(train_df)

    return m


def eval_fn(eval_df, model_path, output_dir):
    with open(model_path) as fp:
        model = model_from_json(fp.read())
    forecast = model.predict(eval_df)

    # TODO: Implement evaluation output

    return forecast


def infer_fn(infer_df, model_path):
    with open(model_path) as fp:
        model = model_from_json(fp.read())
    forecast = model.predict(infer_df)
    return forecast


MODEL_REGISTRY = {
    "prophet_001": {
        "train_fn": train_001,
        "serialize_fn": serialize_to_json,
        "eval_fn": eval_fn,
        "infer_fn": infer_fn,
    },
}
