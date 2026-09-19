from dataclasses import replace

import pytest

from genshin_opt.akasha.hutao_models import AkashaHutaoBuild, ObservedComponents
from genshin_opt.akasha.hutao_score import score_hutao_akasha
from genshin_opt.akasha.required_e_validation import (e_candidate_rows, e_candidate_summary,
                                                       linear_diagnostic, required_final_atk_rows)


def synthetic_build(rank: int = 1, max_hp: float = 32000.0) -> AkashaHutaoBuild:
    return AkashaHutaoBuild(
        input_source="akasha_leaderboard_raw", max_hp=max_hp, sheet_atk=1800.0, base_atk=714.5089773,
        crit_rate=0.75, crit_dmg=2.10, elemental_mastery=120.0, pyro_dmg_bonus=0.616,
        artifact_sets=(("Crimson Witch of Flames", 5),), leaderboard_id="test", rank=rank,
        uid=f"test-{rank}", build_md5=f"build-{rank}", entry_id=f"entry-{rank}", raw_path="synthetic",
        observed=ObservedComponents(1.0, 1.0, 1.0, 1.0), observed_result=1.0)


def test_required_final_atk_inverse_recovers_predicted_atk() -> None:
    build = synthetic_build()
    score = score_hutao_akasha(build)
    observed = ObservedComponents(score.n1_vape_avg, score.n1_non_vape_avg,
                                  score.ca_vape_avg, score.q_vape_avg)
    build = replace(build, observed=observed, observed_result=score.aggregate_score)
    row = required_final_atk_rows((build,))[0]
    assert row["required_final_atk"] == pytest.approx(score.debug_breakdown["final_atk"])
    assert row["required_e_atk_bonus"] == pytest.approx(score.debug_breakdown["hutao_e_atk"])
    assert row["required_minus_predicted_e"] == pytest.approx(0)


def test_linear_diagnostic_reports_exact_line() -> None:
    rows = [{"raw_max_hp": x, "required_e_atk_bonus": 0.06 * x + 120} for x in (30000, 32000, 35000)]
    result = linear_diagnostic(rows)
    assert result["slope"] == pytest.approx(0.06)
    assert result["intercept"] == pytest.approx(120)
    assert result["r_squared"] == pytest.approx(1)
    assert result["residual_std"] == pytest.approx(0)


def test_only_known_discrete_e_candidates_are_compared() -> None:
    builds = tuple(synthetic_build(rank, 30000 + rank * 1000) for rank in range(1, 5))
    normalized = []
    for build in builds:
        score = score_hutao_akasha(build)
        observed = ObservedComponents(score.n1_vape_avg, score.n1_non_vape_avg,
                                      score.ca_vape_avg, score.q_vape_avg)
        normalized.append(replace(build, observed=observed, observed_result=score.aggregate_score))
    builds = tuple(normalized)
    required = required_final_atk_rows(builds)
    rows = e_candidate_rows(builds, required)
    summaries = e_candidate_summary(rows)
    assert {row["candidate_level"] for row in summaries} == {9, 10, 11, 13}
    level_10 = next(row for row in summaries if row["candidate_level"] == 10)
    assert level_10["mean_absolute_required_minus_candidate_e"] == pytest.approx(0)
    assert level_10["n1_pairwise_ordering_accuracy"] == pytest.approx(1)
