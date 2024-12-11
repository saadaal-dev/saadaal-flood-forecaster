from prophet import Prophet
from prophet.serialize import model_to_json, model_from_json


EXCLUDED_COLUMNS = ["location", "y", "date", "level__m", "sin_month", "cos_month", "sin_dayofyear", "cos_dayofyear"]


def train(train_df):
    # Initialize the Prophet model
    m = Prophet(weekly_seasonality=False, growth='flat')

    # Adapt the dataframe to Prophet's requirements
    train_df["ds"] = train_df["date"]

    # Add the regressors to the model
    for r in [c for c in train_df.columns if c not in EXCLUDED_COLUMNS + ["ds"]]:
        m.add_regressor(r)

    # Fit the model
    m.fit(train_df)

    return m


def serialize(model, model_path):
    with open(model_path, 'w') as f:
        f.write(model_to_json(model))


def __model_full_path(model_path, model_name):
    return model_path + model_name + ".json"


def train_and_serialize(train_df, model_path, model_name):
    model = train(train_df)

    model_full_path = __model_full_path(model_path, model_name)
    serialize(model, model_full_path)
    
    return model, model_full_path


def eval_preprocess(test_df):
    test_df["ds"] = test_df["date"]
    return test_df


def infer(model, infer_df):
    # Adapt the dataframe to Prophet's requirements
    infer_df["ds"] = infer_df["date"]

    infer_X = infer_df[[c for c in infer_df.columns if c not in EXCLUDED_COLUMNS]]
    infer_y = model.predict(infer_X)["yhat"]

    # add prediction uncertainty (assume model is RandomForestRegressor, extract output variance)
    # sum(i, N): (infer_y - model.estimator(i).predict(infer_X))**2 / N
    def add_columns_to_est(est):
        # QUICKFIX: individual estimators do not have feature_names_in_ attribute
        #           warning is raised otherwise at predict time
        est.feature_names_in_ = infer_X.columns
        return est
    infer_y_var = sum((infer_y - add_columns_to_est(est).predict(infer_X))**2 for est in model.estimators_) / len(model.estimators_)

    return infer_df.assign(y=infer_y, y_var=infer_y_var)


def load(model_path, model_name):
    with open(__model_full_path(model_path, model_name), 'r') as f:
        return model_from_json(f.read())
