import joblib

from sklearn.ensemble import RandomForestRegressor


EXCLUDED_COLUMNS = ["location", "sin_month", "cos_month", "sin_dayofyear", "cos_dayofyear"]


def filter_columns(df, remove_y=False, remove_level=False, remove_date=False):
    # # CUSTOM FILTER FOR TRAINING DATA TO EXCLUDE FURTHER COLUMNS
    df = df[[
        # Exclude lag abs features (absolute water levels in the past)
        c for c in df.columns if "lagabs" not in c
    ]]

    excluded_columns = EXCLUDED_COLUMNS.copy()
    if remove_date:
        excluded_columns.append("date")
    if remove_y:
        excluded_columns.append("y")
    if remove_level:
        excluded_columns.append("level__m")

    return df[[c for c in df.columns if c not in excluded_columns]]


def train(train_df):
    max_depth = 30
    min_samples_leaf = 5
    n_estimators = 100
    clf = RandomForestRegressor(max_depth=max_depth, min_samples_leaf=min_samples_leaf, n_estimators=n_estimators, random_state=0)

    train_X = filter_columns(train_df, remove_y=True, remove_level=True, remove_date=True)
    train_y = train_df["y"]
    clf.fit(train_X, train_y)

    for c in train_X.columns:
        print(f"Feature importances: {c}: {clf.feature_importances_[train_X.columns.get_loc(c)]:.4f}")

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


def eval_preprocess(test_df):
    test_df = filter_columns(test_df)
    return test_df


def infer(model, infer_df):
    infer_X = filter_columns(infer_df, remove_y=True, remove_level=True, remove_date=True)
    infer_y = model.predict(infer_X)

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
    # Load model from .pkl file
    with open(__model_full_path(model_path, model_name), 'rb') as f:
        return joblib.load(f)
