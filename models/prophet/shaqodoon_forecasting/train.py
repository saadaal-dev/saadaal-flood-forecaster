from .prophet import MODEL_REGISTRY as PROPHET_MODEL_REGISTRY

MODEL_REGISTRY = PROPHET_MODEL_REGISTRY


def train_and_serialize(data, model_type, output_model_path):
    M = MODEL_REGISTRY[model_type]
    m = M["train_fn"](data)
    M["serialize_fn"](m, output_model_path)


def eval(data, model_type, model_path, output_dir):
    M = MODEL_REGISTRY[model_type]
    M["eval_fn"](data, model_path, output_dir)


def infer(data, model_type, model_path):
    M = MODEL_REGISTRY[model_type]
    return M["infer_fn"](data, model_path).iloc[0, 1]
