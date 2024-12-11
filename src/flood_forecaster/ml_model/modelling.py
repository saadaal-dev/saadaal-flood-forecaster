from math import ceil

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns



def make_eval_df(test_df, test_y, pred_y):
    return pd.DataFrame({
        "date": test_df["date"],
        "pred_y": pred_y,
        "test_y": test_y,
        "level__m": test_df["level__m"],
        "abs_pred_y": test_df["level__m"] + pred_y,
        "abs_test_y": test_df["level__m"] + test_y,
    }).set_index("date")


def __default_predict_fn(model, X):
    X = X.dropna()
    return model.predict(X)


def eval(model, test_df, predict_fn = __default_predict_fn):
    count_test_df_raw = len(test_df.index)
    test_df = test_df.dropna()
    count_test_df_no_na = len(test_df.index)

    if count_test_df_no_na < count_test_df_raw:
        print(f"WARNING: drop NA rows effect: {count_test_df_no_na}/{count_test_df_raw} ({count_test_df_no_na/count_test_df_raw:.2%})")

    test_X = test_df[[c for c in test_df.columns if c not in ["y", "date", "level__m"]]]
    test_y = test_df["y"]

    pred_y = predict_fn(model, test_X)

    eval_df = make_eval_df(test_df, test_y, pred_y)

    return eval_df


def corr_chart(df, store_path=None, show=False):
    dfs = []
    for station in df["location"].unique():
        station_df = df[df["location"] == station].select_dtypes('number')
        
        # plot the correlation between y (river level variation) and each numerical feature
        dfs.append(station_df.corr()["y"].drop(["y"]).to_frame(name="corr").assign(station=station))
    
    corr_df = pd.concat(dfs, axis=0)
    
    # plot heatmap (with correlation values) for each station, y is implicit.
    fig, ax = plt.subplots(1, 1, figsize=(24,40))
    ax.set_title("Correlation between river level variations and input features per each station")
    sns.heatmap(corr_df.pivot(columns="station", values="corr"), ax=ax, vmin=-1, vmax=1)

    # set left margin to ensure full station name is displayed
    plt.subplots_adjust(left=0.2)

    if store_path:
        fig.savefig(store_path)
    if show:
        fig.show()
    return fig, ax


def eval_chart(eval_df, level_moderate, level_high, level_full, store_path=None, show=False, abs=True):
    if abs:
        pred_y_col = "abs_pred_y"
        test_y_col = "abs_test_y"
    else:
        pred_y_col = "pred_y"
        test_y_col = "test_y"

    eval_df = eval_df.reset_index()
    fig, ax = plt.subplots(1, 1, figsize=(15,7))
    ax.set_title("Validation data (green) vs Forecasted (blue)")
    eval_df.plot(x="date", y=pred_y_col, ax=ax)
    eval_df.plot(x="date", y=test_y_col, ax=ax, color='green', alpha=0.3, marker='o')
    ax.set_xlabel("date")
    if abs:
        ax.set_ylabel("river level (m)")
        ax.axhline(y=level_moderate, color='orange', linestyle='--')
        ax.axhline(y=level_high, color='red', linestyle='--')
        ax.axhline(y=level_full, color='violet', linestyle='-')
        ax.set_ylim([0, ceil(level_full + 1)])
    else:
        ax.set_ylabel("river level variation (m)")
        ax.axhline(y=0, color='gray', linestyle='--')

    if store_path:
        fig.savefig(store_path)
    if show:
        fig.show()
    return fig, ax
