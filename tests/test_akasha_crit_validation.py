import pytest

from genshin_opt.akasha.crit_validation import (candidate_summaries, input_reconstruction_rows,
                                                multiplier_residual_rows)
from genshin_opt.akasha.hutao_raw import load_hutao_builds


BUILDS = load_hutao_builds("data/akasha/raw")


def test_raw_crit_boundary_contains_base_weapon_and_artifact_terms() -> None:
    rows = input_reconstruction_rows(BUILDS)
    assert len(rows) == 20
    assert all(row["crit_rate_difference"] == pytest.approx(0) for row in rows)
    assert all(row["crit_damage_difference"] == pytest.approx(0) for row in rows)
    assert all(row["other_fixed_crit_rate"] == 0 for row in rows)
    cv_differences = [float(row["artifact_crit_value_difference"]) for row in rows]
    assert min(cv_differences) == pytest.approx(-0.049996047000036015, abs=1e-9)
    assert max(cv_differences) == pytest.approx(-0.04999032400000525, abs=1e-9)


def test_current_multiplier_is_one_plus_clamped_raw_cr_times_raw_cd() -> None:
    rows = multiplier_residual_rows(BUILDS)
    for row in rows:
        expected = 1 + min(float(row["raw_crit_rate"]), 1.0) * float(row["raw_crit_damage"])
        assert row["current_crit_multiplier"] == pytest.approx(expected)
        assert row["b_raw_clamped_multiplier"] == pytest.approx(row["c_current_raw_multiplier"])


def test_required_crit_multiplier_is_observed_over_predicted_precrit_damage() -> None:
    row = multiplier_residual_rows(BUILDS)[0]
    expected = float(row["observed_aggregate"]) / float(row["predicted_precrit_aggregate"])
    assert row["required_crit_multiplier"] == pytest.approx(expected)
    assert row["required_to_current_ratio"] == pytest.approx(
        float(row["observed_aggregate"]) / float(row["predicted_aggregate"]))


def test_only_one_saved_build_exceeds_100_percent_crit_rate() -> None:
    rows = multiplier_residual_rows(BUILDS)
    over = [row for row in rows if row["crit_rate_exceeds_100"]]
    assert len(over) == 1
    assert over[0]["rank"] == 10
    assert over[0]["rank"] == 10
    assert float(over[0]["a_raw_no_clamp_multiplier"]) > float(over[0]["b_raw_clamped_multiplier"])


def test_baseline_crit_diagnostic_is_stable() -> None:
    rows = multiplier_residual_rows(BUILDS)
    first = rows[0]
    assert first["required_to_current_ratio_mean"] == pytest.approx(1.0768989018983555, abs=1e-12)
    assert first["required_to_current_ratio_std"] == pytest.approx(0.0024572389989734396, abs=1e-12)
    assert first["aggregate_residual_vs_crit_rate_pearson"] == pytest.approx(-0.025265114944462125, abs=1e-12)
    assert first["aggregate_residual_vs_crit_damage_pearson"] == pytest.approx(-0.34732577681264315, abs=1e-12)
    assert first["aggregate_residual_vs_current_crit_multiplier_pearson"] == pytest.approx(-0.48809328541779184, abs=1e-12)
    summaries = {row["candidate"]: row for row in candidate_summaries(rows)}
    for metric in ("mean_relative_error", "median_relative_error", "residual_std", "maximum_absolute_relative_error"):
        assert summaries["b_raw_clamped_multiplier"][metric] == summaries["c_current_raw_multiplier"][metric]
