from dataclasses import dataclass

from .modelling import eval
from .Prophet001.model import (
    eval_preprocess as Prophet001_eval_preprocess,
)
from .Prophet001.model import (
    infer as Prophet001_infer,
)
from .Prophet001.model import (
    load as Prophet001_load,
)
from .Prophet001.model import (
    train as Prophet001_train,
)
from .Prophet001.model import (
    train_and_serialize as Prophet001_train_and_serialize,
)
from .RandomForestRegressor001.model import (
    infer as RandomForestRegressor001_infer,
)
from .RandomForestRegressor001.model import (
    load as RandomForestRegressor001_load,
)
from .RandomForestRegressor001.model import (
    train as RandomForestRegressor001_train,
)
from .RandomForestRegressor001.model import (
    train_and_serialize as RandomForestRegressor001_train_and_serialize,
)
from .XGBoost001.model import (
    infer as XGBoost001_infer,
)
from .XGBoost001.model import (
    load as XGBoost001_load,
)
from .XGBoost001.model import (
    train as XGBoost001_train,
)
from .XGBoost001.model import (
    train_and_serialize as XGBoost001_train_and_serialize,
)


@dataclass
class ModelManager:
    train: callable
    train_and_serialize: callable
    load: callable
    eval: callable
    infer: callable


MODEL_MANAGER_REGISTRY = {
    "RandomForestRegressor_001": ModelManager(
        **{
            "train": RandomForestRegressor001_train,
            "train_and_serialize": RandomForestRegressor001_train_and_serialize,
            "load": RandomForestRegressor001_load,
            "eval": eval,
            "infer": RandomForestRegressor001_infer,
        }
    ),
    "XGBoost_001": ModelManager(
        **{
            "train": XGBoost001_train,
            "train_and_serialize": XGBoost001_train_and_serialize,
            "load": XGBoost001_load,
            "eval": eval,
            "infer": XGBoost001_infer,
        }
    ),
    "Prophet_001": ModelManager(
        **{
            "train": Prophet001_train,
            "train_and_serialize": Prophet001_train_and_serialize,
            "load": Prophet001_load,
            # TODO: move into Prophet001/model.py
            "eval": lambda model, df: eval(model, Prophet001_eval_preprocess(df), lambda model, df: model.predict(df)["yhat"]),
            "infer": Prophet001_infer,
        }
    ),
}
