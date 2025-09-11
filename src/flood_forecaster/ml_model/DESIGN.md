## Structure of the `ml_model` Package

### Introduction

The `ml_model` package is responsible for managing the machine learning (ML) pipeline. It includes functions for data preprocessing, model training, and model evaluation.
The package is designed to be modular, allowing for easy integration of new models and data preprocessing techniques.

### Package Structure

The `ml_model` package consists of the following files:

- **api.py**: This module contains the main ML pipeline commands such as preprocess, split data, train, and evaluate. It serves as the main entry point of the package and is used by the CLI companion module.
- **preprocess.py**: Contains internal functions used by `api.py` for data preprocessing.
- **inference.py**: Contains internal functions used by `api.py` for making predictions.
- **modelling.py**: Contains internal functions used by `api.py` for model training and evaluation.
- **registry.py**: Indexes various ML modeling functions. It includes modules such as `Prophet001`, `RandomForestRegressor001`, and `XGBoost001`, each implementing their own model management functions.

## Known Issues

- upstream stations need to be processed before downstream stations
  (this is a bug in the current implementation, but it is not critical for the initial release as doing this step manually solves the issue).
- inference in future with lacking data is not handled gracefully 
  (getting empty DataFrame with error like `pandera.errors.SchemaError: expected series 'month_sin' to have type float64, got int32`).
- only one preprocessor is currently implemented and hardcoded (following the `preprocessor_type` in the config file).
- error handling is not graceful.
- date reference as target date instead of prediction date is convoluted and not intuitive.
  This is mostly due to how the training data is built: the target is the time reference at which we are asking for a prediction.
  If `forecast_days` is set to 1, the target date is the same as the prediction date (we predict the same day).
  This is not intuitive, considering how the weather forcast date is set (0 = today, 1 = tomorrow, etc.).
- logging is not implemented in the ML pipeline, only print statements are used.
- river_stations_metadata used in the eval function to load the threshold values.
  It is not used in the training or inference. 
  Will be removed in the future as it is handled by the data module.
- @Adina: Might be useful to add a _Const(object) class to keep all const definitions in one place, like STDOUT, DB, ENVFILE, but also other static params used like PREDICTION_LEVEL, .. see [PR#59](https://github.com/saadaal-dev/saadaal-flood-forecaster/pull/59#discussion_r2143111696)
- Preprocessing configuration is in config.ini.
  It should be moved on it's own since changing the lag / forecast paramters has an impact on the model itself.
  A model should reference a preprocessor by name.
- refactor models as a common Class with methods like `train`, `predict`, `evaluate`, etc.
  This would allow to have a common interface for all models and make it easier to add new models in the future.
- refactor models so that they return absolute river levels instead of relative levels (diff).
  This to have models returning the expected output and not requiring a postprocessing step to convert the output to absolute levels.
