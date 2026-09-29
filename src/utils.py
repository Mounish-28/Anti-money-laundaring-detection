import gc
import os
import random

import numpy as np


def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except ImportError:
        pass


def reduce_mem_usage(df):
    """Iterate through all columns of a dataframe and modify the data type
    to reduce memory usage.
    """
    import pandas as pd

    start_mem = df.memory_usage().sum() / 1024**2
    print(f"Memory usage of dataframe is {start_mem:.2f} MB")

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            c_min = df[col].min()
            c_max = df[col].max()
            col_type = df[col].dtype
            if str(col_type)[:3] == "int":
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
                else:
                    df[col] = df[col].astype(np.int64)
            elif str(col_type)[:5] == "float":
                if (
                    c_min > np.finfo(np.float32).min
                    and c_max < np.finfo(np.float32).max
                ):
                    df[col] = df[col].astype(np.float32)
                else:
                    df[col] = df[col].astype(np.float64)

    end_mem = df.memory_usage().sum() / 1024**2
    print(f"Memory usage after optimization is: {end_mem:.2f} MB")
    print(f"Decreased by {100 * (start_mem - end_mem) / start_mem:.1f}%")

    return df


def cleanup_memory():
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def optimize_threshold(y_true, y_probs, min_rec=0.75):
    return optimize_threshold_v4(y_true, y_probs, min_acc=0.97, min_rec=min_rec)


def optimize_threshold_v4(y_true, y_probs, min_acc=0.97, min_rec=0.90):
    """
    Validation threshold sweep T in [0.001, 0.999].
    Objective: Maximize (F1_Score + Accuracy) / 2 subject to Accuracy >= min_acc and Recall >= min_rec.
    Tier 1: Accuracy >= min_acc AND Recall >= min_rec -> Maximize (F1 + Accuracy) / 2
    Tier 2: Accuracy >= min_acc -> Maximize F1 (while strictly keeping Accuracy >= min_acc)
    Tier 3: Fallback -> Maximize (F1 + Accuracy) / 2
    """
    import numpy as np

    y_true = np.asarray(y_true, dtype=np.int32)
    y_probs = np.asarray(y_probs, dtype=np.float32)

    thresholds = np.linspace(0.001, 0.999, 999)
    P = int((y_true == 1).sum())
    N = int(len(y_true) - P)

    best_t_t1 = None
    best_score_t1 = -1.0
    best_t_t2 = None
    best_score_t2 = -1.0
    best_t_t3 = 0.5
    best_score_t3 = -1.0

    for t in thresholds:
        preds = y_probs >= t
        tp = int(np.logical_and(preds, y_true == 1).sum())
        fp = int(np.logical_and(preds, y_true == 0).sum())
        fn = P - tp
        tn = N - fp

        acc = (tp + tn) / (P + N) if (P + N) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        combined = (f1 + acc) / 2.0

        if acc >= min_acc and rec >= min_rec:
            if combined > best_score_t1:
                best_score_t1 = combined
                best_t_t1 = t

        if acc >= min_acc:
            if f1 > best_score_t2:
                best_score_t2 = f1
                best_t_t2 = t

        if combined > best_score_t3:
            best_score_t3 = combined
            best_t_t3 = t

    if best_t_t1 is not None:
        return float(best_t_t1)
    elif best_t_t2 is not None:
        return float(best_t_t2)
    else:
        return float(best_t_t3)


class PrefitIsotonicCalibrator:
    def __init__(self):
        from sklearn.isotonic import IsotonicRegression

        self.iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)

    def fit(self, val_probs, y_val):
        import numpy as np

        val_probs = np.asarray(val_probs, dtype=np.float64)
        y_val = np.asarray(y_val, dtype=np.float64)
        self.iso.fit(val_probs, y_val)
        return self

    def predict_proba(self, probs):
        import numpy as np

        probs = np.asarray(probs, dtype=np.float64)
        calibrated = self.iso.predict(probs)
        return np.clip(calibrated, 0.0, 1.0).astype(np.float32)


def optimize_threshold_phase_1_9(
    y_true,
    y_probs,
    min_acc=0.970,
    baseline_rec=0.0,
    baseline_prec=0.0,
    t_min=0.05,
    t_max=0.99,
    step=0.002,
):
    """
    Phase 1.9 Dynamic Pareto Threshold Sweeper:
    Sweeps T in [t_min, t_max] in increments of step.
    Objective:
      T* = argmax_T (F1(T)) subject to:
          Accuracy(T) >= min_acc
          Recall(T) >= baseline_rec
          Precision(T) >= baseline_prec
    Tiered fallback:
      Tier 1: Acc >= min_acc AND Recall >= baseline_rec AND Prec >= baseline_prec -> max F1
      Tier 2: Acc >= min_acc AND Prec >= baseline_prec * 0.95 -> max (Recall + F1)
      Tier 3: Acc >= min_acc AND Prec >= max(0.50, baseline_prec * 0.80) -> max F1
      Tier 4: Acc >= min_acc (strict global guardrail) -> max F1
      Tier 5: Global fallback -> max (F1 + Accuracy) / 2
    """
    import numpy as np

    y_true = np.asarray(y_true, dtype=np.int32)
    y_probs = np.asarray(y_probs, dtype=np.float32)

    thresholds = np.arange(t_min, t_max + 1e-6, step)
    P = int((y_true == 1).sum())
    N = int(len(y_true) - P)

    best_t_t1, best_score_t1 = None, -1.0
    best_t_t2, best_score_t2 = None, -1.0
    best_t_t3, best_score_t3 = None, -1.0
    best_t_t4, best_score_t4 = None, -1.0
    best_t_t5, best_score_t5 = 0.5, -1.0

    min_p_t2 = baseline_prec * 0.95 if baseline_prec > 0 else 0.0
    min_p_t3 = max(0.50, baseline_prec * 0.80) if baseline_prec > 0 else 0.0

    for t in thresholds:
        preds = y_probs >= t
        tp = int(np.logical_and(preds, y_true == 1).sum())
        fp = int(np.logical_and(preds, y_true == 0).sum())
        fn = P - tp
        tn = N - fp

        acc = (tp + tn) / (P + N) if (P + N) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        combined = (f1 + acc) / 2.0

        # Tier 1: Acc >= min_acc, Rec >= baseline_rec, Prec >= baseline_prec
        if acc >= min_acc and rec >= baseline_rec and prec >= baseline_prec:
            if f1 > best_score_t1:
                best_score_t1 = f1
                best_t_t1 = t

        # Tier 2: Acc >= min_acc, Prec >= min_p_t2 -> maximize (rec + f1) to push recall
        if acc >= min_acc and prec >= min_p_t2:
            score2 = rec + f1
            if score2 > best_score_t2:
                best_score_t2 = score2
                best_t_t2 = t

        # Tier 3: Acc >= min_acc, Prec >= min_p_t3 -> max F1
        if acc >= min_acc and prec >= min_p_t3:
            if f1 > best_score_t3:
                best_score_t3 = f1
                best_t_t3 = t

        # Tier 4: Acc >= min_acc (Global guardrail)
        if acc >= min_acc:
            if f1 > best_score_t4:
                best_score_t4 = f1
                best_t_t4 = t

        # Tier 5: Fallback
        if combined > best_score_t5:
            best_score_t5 = combined
            best_t_t5 = t

    if best_t_t1 is not None:
        return float(best_t_t1)
    elif best_t_t2 is not None:
        return float(best_t_t2)
    elif best_t_t3 is not None:
        return float(best_t_t3)
    elif best_t_t4 is not None:
        return float(best_t_t4)
    else:
        return float(best_t_t5)
