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
