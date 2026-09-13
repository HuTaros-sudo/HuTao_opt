import pytest

from genshin_opt.akasha.h3_validation import (baseline_candidate, build_residual_rows,
                                               enemy_multiplier_breakdown, make_candidates)
from genshin_opt.akasha.hutao_damage import enemy_res_multiplier
from genshin_opt.akasha.hutao_raw import load_hutao_builds


def test_enemy_res_multiplier_uses_all_three_piecewise_branches() -> None:
    assert enemy_res_multiplier(0.10, 0.40).value == pytest.approx(1.15)
    assert enemy_res_multiplier(0.10, 0.0).value == pytest.approx(0.90)
    assert enemy_res_multiplier(0.75, 0.0).value == pytest.approx(0.25)
    assert enemy_res_multiplier(1.00, 0.0).value == pytest.approx(0.20)


def test_baseline_enemy_multiplier_is_explicit() -> None:
    values = enemy_multiplier_breakdown(baseline_candidate())
    assert values["def_multiplier"] == pytest.approx(0.5)
    assert values["res_after_vv"] == pytest.approx(-0.30)
    assert values["res_multiplier"] == pytest.approx(1.15)
    assert values["common_enemy_multiplier"] == pytest.approx(0.575)


def test_candidate_grid_contains_only_documented_discrete_values() -> None:
    candidates = make_candidates()
    assert len(candidates) == 12
    assert {candidate.enemy_level for candidate in candidates} == {80, 90, 100}
    assert {candidate.base_pyro_res for candidate in candidates} == {0.0, 0.10}
    assert {candidate.vv_res_reduction for candidate in candidates} == {0.0, 0.40}


def test_h3_candidate_scales_every_component_by_same_enemy_ratio() -> None:
    build = load_hutao_builds("data/akasha/raw")[0]
    baseline = baseline_candidate()
    changed = next(candidate for candidate in make_candidates() if candidate.candidate_id == "enemy80_res0_vv40")
    rows = build_residual_rows((build,), (baseline, changed))
    baseline_row, changed_row = rows
    expected_scale = (float(changed_row["common_enemy_multiplier"])
                      / float(baseline_row["common_enemy_multiplier"]))
    for component in ("n1_non_vape", "n1_vape", "ca_vape", "q_vape", "aggregate"):
        actual_scale = float(changed_row[f"predicted_{component}"]) / float(baseline_row[f"predicted_{component}"])
        assert actual_scale == pytest.approx(expected_scale)
    assert changed_row["component_ratio_relative_spread"] == pytest.approx(
        baseline_row["component_ratio_relative_spread"])
