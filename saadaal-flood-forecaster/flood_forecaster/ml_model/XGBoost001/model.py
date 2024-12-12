import joblib

from xgboost import XGBRegressor

EXCLUDED_COLUMNS = ["location", "y", "date", "level__m", "sin_month", "cos_month", "sin_dayofyear", "cos_dayofyear"]


def train(train_df):
    clf = XGBRegressor(n_estimators=1000, max_depth=7, eta=0.1, subsample=0.7, colsample_bytree=0.8)
    train_X = train_df[[c for c in train_df.columns if c not in EXCLUDED_COLUMNS]]
    train_y = train_df["y"]
    clf.fit(train_X, train_y)

    return clf


def serialize(model, model_path):
    with open(model_path, 'wb') as f:
        joblib.dump(model, f)


def __model_full_path(model_path, model_name):
    return model_path + model_name + ".joblib"


def train_and_serialize(train_df, model_path, model_name):
    model = train(train_df)

    model_full_path = __model_full_path(model_path, model_name)
    serialize(model, model_full_path)
    
    return model, model_full_path


def infer(model, infer_df):
    infer_X = infer_df[[c for c in infer_df.columns if c not in EXCLUDED_COLUMNS]]
    infer_y = model.predict(infer_X)

    # TODO: add prediction uncertainty
    # # add prediction uncertainty (assume model is RandomForestRegressor, extract output variance)
    # # sum(i, N): (infer_y - model.estimator(i).predict(infer_X))**2 / N
    # def add_columns_to_est(est):
    #     # QUICKFIX: individual estimators do not have feature_names_in_ attribute
    #     #           warning is raised otherwise at predict time
    #     est.feature_names_in_ = infer_X.columns
    #     return est
    # infer_y_var = sum((infer_y - add_columns_to_est(est).predict(infer_X))**2 for est in model.estimators_) / len(model.estimators_)

    # return infer_df.assign(y=infer_y, y_var=infer_y_var)
    return infer_df.assign(y=infer_y)


def load(model_path, model_name):
    # Load model from .pkl file
    with open(__model_full_path(model_path, model_name), 'rb') as f:
        return joblib.load(f)
