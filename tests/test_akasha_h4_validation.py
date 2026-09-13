from dataclasses import replace

import pytest

from genshin_opt.akasha import ScenarioConfig, load_hutao_builds, score_hutao_akasha
from genshin_opt.akasha.h4_validation import (EXTERNAL_EM_CANDIDATES, candidate_summaries,
                                              em_candidate_rows, vape_ratio_residual_rows)


BUILDS = load_hutao_builds("data/akasha/raw")


def test_external_em_candidates_are_only_the_requested_discrete_values() -> None:
    assert [value for value, _ in EXTERNAL_EM_CANDIDATES.values()] == [0.0, 100.0, 220.0, 300.0, 420.0]
    summaries = candidate_summaries(em_candidate_rows(BUILDS))
    assert len(summaries) == 5
    assert min(summaries, key=lambda row: abs(float(row["n1_ratio_mean_error"])))["external_em"] == 420.0


def test_crimson_witch_reaction_bonus_only_changes_vape_for_crimson_builds() -> None:
    crimson = next(build for build in BUILDS if build.has_crimson_witch_4pc)
    shimenawa = next(build for build in BUILDS if build.has_shimenawa_4pc)
    enabled = ScenarioConfig(hutao_external_em=420, apply_crimson_witch_vape_bonus=True)
    disabled = replace(enabled, apply_crimson_witch_vape_bonus=False)
    crimson_on, crimson_off = score_hutao_akasha(crimson, enabled), score_hutao_akasha(crimson, disabled)
    assert crimson_on.n1_non_vape_avg == pytest.approx(crimson_off.n1_non_vape_avg)
    assert crimson_on.n1_vape_avg > crimson_off.n1_vape_avg
    assert crimson_on.ca_vape_avg > crimson_off.ca_vape_avg
    assert crimson_on.q_vape_avg > crimson_off.q_vape_avg
    shim_on, shim_off = score_hutao_akasha(shimenawa, enabled), score_hutao_akasha(shimenawa, disabled)
    assert shim_on.aggregate_score == pytest.approx(shim_off.aggregate_score)


def test_n1_vape_ratio_cancels_non_vaporize_common_terms() -> None:
    build = BUILDS[0]
    result = score_hutao_akasha(build)
    ratio = result.n1_vape_avg / result.n1_non_vape_avg
    assert ratio == pytest.approx(result.debug_breakdown["vaporize_multiplier"])


def test_em420_with_crimson_bonus_matches_observed_n1_ratio_diagnostic() -> None:
    summaries = candidate_summaries(vape_ratio_residual_rows(BUILDS))
    best = next(row for row in summaries if row["candidate_id"] == "em_420_all_cw_on")
    assert best["n1_ratio_mean_error"] == pytest.approx(0.000287447422607185, abs=1e-12)
    assert best["n1_ratio_median_error"] == pytest.approx(0.0002861842260728764, abs=1e-12)
    assert best["n1_ratio_std"] == pytest.approx(0.000012160550389479703, abs=1e-12)
    assert best["n1_ratio_maximum_absolute_error"] == pytest.approx(0.00032029312522204327, abs=1e-12)
    assert best["ca_ratio_mean_error"] == pytest.approx(0.0010507591766475415, abs=1e-12)
    assert best["q_ratio_mean_error"] == pytest.approx(0.0001724544443265226, abs=1e-12)
    assert best["aggregate_mean_error"] == pytest.approx(-0.07140289807310361, abs=1e-12)


def test_raw_em_cannot_contain_any_universal_external_candidate() -> None:
    raw_em = [build.elemental_mastery for build in BUILDS]
    assert min(raw_em) == pytest.approx(39.6300000187666)
    assert min(raw_em) < 100 < max(raw_em)
    zero_rows = [row for row in em_candidate_rows(BUILDS) if row["candidate_id"] == "em_0"]
    assert all(row["artifact_em_input"] == row["raw_stats_elemental_mastery"] for row in zero_rows)
    assert all(row["character_fixed_em"] == row["weapon_fixed_em"] == row["external_em_added"] == 0 for row in zero_rows)
