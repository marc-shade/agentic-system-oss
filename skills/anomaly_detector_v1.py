"""Pattern matching: detect anomalies"""

def anomaly_detector(values: List[float], threshold: float = 2.0) -> List[int]:
    """
    Detect anomalies using standard deviation.

    Args:
        values: List of numeric values
        threshold: Standard deviation threshold

    Returns:
        Indices of anomalous values
    """
    if not values:
        return []

    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std_dev = variance ** 0.5

    anomalies = []
    for i, value in enumerate(values):
        if abs(value - mean) > threshold * std_dev:
            anomalies.append(i)

    return anomalies
