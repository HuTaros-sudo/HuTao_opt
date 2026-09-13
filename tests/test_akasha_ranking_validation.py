from genshin_opt.akasha.hutao_raw import load_hutao_builds
from genshin_opt.akasha.ranking_validation import pairwise_rows, ranking_rows, ranking_summary


BUILDS = load_hutao_builds("data/akasha/raw")


def test_ranking_validation_covers_20_builds_and_all_pairs():
    rows = ranking_rows(BUILDS)
    pairs = pairwise_rows(rows)
    assert len(rows) == 20
    assert len(pairs) == 190
    assert {float(row["observed_rank"]) for row in rows} == set(range(1, 21))


def test_diagnostic_common_scale_does_not_change_ranking():
    rows = ranking_rows(BUILDS)
    summary = ranking_summary(rows, pairwise_rows(rows))
    assert summary["diagnostic_common_scale"] > 1
    assert summary["scale_preserves_all_predicted_ranks"] is True


def test_pairwise_summary_is_bounded_and_contains_nearby_buckets():
    rows = ranking_rows(BUILDS)
    summary = ranking_summary(rows, pairwise_rows(rows))
    assert 0 <= summary["pairwise_ordering_accuracy"] <= 1
    assert set(summary["nearby"]) == {"under_0.1_percent", "under_0.25_percent", "under_0.5_percent", "under_1_percent"}
