from backend.features.time_decay import exponential_time_decay


def test_time_decay_half_life() -> None:
    assert exponential_time_decay(0, 60) == 1.0
    assert round(exponential_time_decay(60, 60), 4) == 0.5
    assert round(exponential_time_decay(120, 60), 4) == 0.25
