from dataclasses import replace

import pytest

from genshin_opt.akasha.atk_buff_validation import (ATK_BUFF_CANDIDATES, _pair_accuracy,
                                                     candidate_comparison_rows, constant_residual_rows)
from genshin_opt.akasha.hutao_models import AkashaHutaoBuild, ObservedComponents
from genshin_opt.akasha.hutao_score import score_hutao_akasha
from genshin_opt.akasha.required_e_validation import required_final_atk_rows


def synthetic_build(rank: int, max_hp: float, sheet_atk: float) -> AkashaHutaoBuild:
    build = AkashaHutaoBuild(
        input_source="akasha_leaderboard_raw", max_hp=max_hp, sheet_atk=sheet_atk, base_atk=714.5089773,
        crit_rate=.7, crit_dmg=2.0, elemental_mastery=100.0, pyro_dmg_bonus=.616,
        artifact_sets=(("Crimson Witch of Flames", 5),), leaderboard_id="test", rank=rank,
        uid=f"test-{rank}", build_md5=f"build-{rank}", entry_id=f"entry-{rank}", raw_path="synthetic",
        observed=ObservedComponents(1, 1, 1, 1), observed_result=1,
    )
    score = score_hutao_akasha(build)
    observed = ObservedComponents(score.n1_vape_avg, score.n1_non_vape_avg, score.ca_vape_avg, score.q_vape_avg)
    return replace(build, observed=observed, observed_result=score.aggregate_score)


def test_candidates_are_known_discrete_combinations() -> None:
    by_name = {candidate.name: candidate for candidate in ATK_BUFF_CANDIDATES}
    assert by_name["current_mm20"].raw_added_pct == pytest.approx(.20)
    assert by_name["mm20_pyro25"].raw_added_pct == pytest.approx(.45)
    assert by_name["mm20_amber15"].raw_added_pct == pytest.approx(.35)
    assert by_name["pyro25_amber15"].raw_added_pct == pytest.approx(.40)
    assert by_name["mm20_pyro25_amber15"].raw_added_pct == pytest.approx(.60)
    assert by_name["millennial40_rejected"].rules_status.startswith("rejected")


def test_pair_accuracy_filters_nearby_pairs() -> None:
    observed = [100.0, 100.05, 102.0]
    predicted = [100.0, 99.0, 102.0]
    count, accuracy = _pair_accuracy(observed, predicted, .001)
    assert count == 1
    assert accuracy == pytest.approx(0)


def test_synthetic_required_atk_has_no_missing_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    from genshin_opt.akasha.h5_validation import ARTIFACT_ATK_BY_UID, ArtifactAtkBreakdown

    builds = (synthetic_build(1, 30000, 1700), synthetic_build(2, 32000, 1750))
    for build in builds:
        monkeypatch.setitem(ARTIFACT_ATK_BY_UID, build.uid, ArtifactAtkBreakdown(.20, 100.0, "test"))
    required = required_final_atk_rows(builds)
    rows, summary = constant_residual_rows(builds, required)
    assert [row["actual_missing_atk"] for row in rows] == pytest.approx([0, 0])
    assert summary["actual_missing_std"] == pytest.approx(0)


def test_real_data_raw_and_independent_paths_use_each_buff_once() -> None:
    from genshin_opt.akasha.h5_validation import ARTIFACT_ATK_BY_UID
    from genshin_opt.akasha.hutao_raw import load_hutao_builds

    builds = load_hutao_builds("data/akasha/raw")
    if not builds or any(build.uid not in ARTIFACT_ATK_BY_UID for build in builds):
        pytest.skip("保存済みAkasha rawまたはローカル聖遺物観測値がありません")
    required = required_final_atk_rows(builds)
    rows = candidate_comparison_rows(builds, required)
    baseline = next(row for row in rows if row["candidate"] == "current_mm20")
    assert baseline["independent_minus_raw_final_atk_max_abs"] < 2.0

