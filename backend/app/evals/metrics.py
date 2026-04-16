def precision(tp: int, fp: int) -> float:
    denominator = tp + fp
    return tp / denominator if denominator else 0.0


def recall(tp: int, fn: int) -> float:
    denominator = tp + fn
    return tp / denominator if denominator else 0.0


def f1_score(precision_value: float, recall_value: float) -> float:
    denominator = precision_value + recall_value
    return 2 * precision_value * recall_value / denominator if denominator else 0.0
