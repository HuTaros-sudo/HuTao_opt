import pytest

from genshin_opt.akasha.h1_validation import (ARTIFACT_HP_BY_UID, E_SKILL_RATIOS,
                                               e_bonus_comparison_rows, maxhp_reconstruction_rows,
                                               reconstruct_max_hp)
from genshin_opt.akasha.hutao_raw import load_hutao_builds


def test_max_hp_reconstruction_formula_keeps_flat_hp_outside_percent_multiplier() -> None:
    assert reconstruct_max_hp(10000, 0.50, 1000, 0.20) == pytest.approx(18000)


def test_all_saved_builds_have_five_independent_artifact_hp_entries() -> None:
    builds = load_hutao_builds("data/akasha/raw")
    assert len(builds) == 20
    assert set(ARTIFACT_HP_BY_UID) == {build.uid for build in builds}
    assert all(len(ARTIFACT_HP_BY_UID[build.uid or ""]) == 5 for build in builds)


def test_lv90_homa_r1_reconstruction_is_within_display_rounding_bound() -> None:
    rows = maxhp_reconstruction_rows(load_hutao_builds("data/akasha/raw"))
    for row in rows:
        difference = abs(float(row["a_lv90_artifacts_homa_r1_absolute_difference"]))
        assert difference <= float(row["lv90_display_rounding_error_bound"])


def test_e_bonus_uses_known_discrete_ratio_and_400_percent_cap() -> None:
    builds = load_hutao_builds("data/akasha/raw")
    maxhp_rows = maxhp_reconstruction_rows(builds)
    rows = e_bonus_comparison_rows(builds[:1], maxhp_rows)
    level13 = next(row for row in rows if row["max_hp_model"] == "a_lv90_artifacts_homa_r1" and row["skill_talent_model"] == "fixed_13")
    expected_uncapped = float(level13["max_hp"]) * E_SKILL_RATIOS[13]
    assert level13["uncapped_e_atk_bonus"] == pytest.approx(expected_uncapped)
    assert level13["e_atk_cap"] == pytest.approx(builds[0].base_atk * 4)
    assert level13["final_e_atk_bonus"] == pytest.approx(min(expected_uncapped, builds[0].base_atk * 4))


def test_diagnostic_scale_is_output_only_and_does_not_replace_prediction() -> None:
    builds = load_hutao_builds("data/akasha/raw")
    maxhp_rows = maxhp_reconstruction_rows(builds)
    rows = e_bonus_comparison_rows(builds, maxhp_rows)
    row = rows[0]
    assert row["predicted_aggregate"] != pytest.approx(float(row["predicted_aggregate"]) * float(row["diagnostic_least_squares_scale"]))
    assert row["relative_error"] == pytest.approx((float(row["predicted_aggregate"]) - float(row["observed_aggregate"])) / float(row["observed_aggregate"]))
