from bench.metrics.calibration import expected_calibration_error, reliability_bins


def test_perfectly_calibrated_scores_give_zero_ece():
    # Half the items score exactly 0.2 and are positive 20% of the time;
    # half score exactly 0.8 and are positive 80% of the time.
    scores = [0.2] * 10 + [0.8] * 10
    outcomes = [True] * 2 + [False] * 8 + [True] * 8 + [False] * 2
    ece = expected_calibration_error(scores, outcomes, n_bins=10)
    assert ece is not None
    assert ece < 0.01


def test_overconfident_scores_give_high_ece():
    # Every item scores 0.95 "risky" but only 10% actually are.
    scores = [0.95] * 20
    outcomes = [True] * 2 + [False] * 18
    ece = expected_calibration_error(scores, outcomes, n_bins=10)
    assert ece is not None
    assert ece > 0.5


def test_empty_input_returns_none():
    assert expected_calibration_error([], [], n_bins=10) is None


def test_mismatched_lengths_raises():
    try:
        expected_calibration_error([0.1], [], n_bins=10)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_reliability_bins_cover_full_range_and_empty_bins_are_none():
    scores = [0.05, 0.95]
    outcomes = [False, True]
    bins = reliability_bins(scores, outcomes, n_bins=10)
    assert len(bins) == 10
    assert bins[0].count == 1
    assert bins[0].observed_frequency == 0.0
    assert bins[-1].count == 1
    assert bins[-1].observed_frequency == 1.0
    # every bin in between got no items
    assert all(b.count == 0 for b in bins[1:-1])


def test_score_of_exactly_one_lands_in_last_bin():
    bins = reliability_bins([1.0], [True], n_bins=10)
    assert bins[-1].count == 1
