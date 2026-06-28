from backend.features.zscore import rolling_zscore


def test_rolling_zscore_calculation() -> None:
    result = rolling_zscore([1, 2, 3], window=3)
    assert result[:2] == [None, None]
    assert round(result[2], 4) == 1.2247


def test_rolling_zscore_zero_std_returns_zero() -> None:
    assert rolling_zscore([5, 5, 5], window=3)[2] == 0.0
