from dataclasses import replace

import pytest

from genshin_opt.akasha.atk_boundary_validation import (boundary_residual_rows,
                                                        legacy_double_counted_predictions)
from genshin_opt.akasha.hutao_engine import debug_build, predict_components_from_artifacts
from genshin_opt.akasha.hutao_models import ArtifactReconstructedAtkInput, ScenarioConfig
from genshin_opt.akasha.hutao_raw import load_hutao_builds


def test_real_raw_build_adds_millennial_and_skill_exactly_once() -> None:
    build = load_hutao_builds("data/akasha/raw")[0]
    debug = debug_build(build)
    expected_skill = min(build.max_hp * 0.0626, build.base_atk * 4)
    assert debug["normalized_precombat_atk"] == build.sheet_atk
    assert debug["external_combat_atk_bonus"] == pytest.approx(build.base_atk * 0.20)
    assert debug["hutao_skill_atk_bonus"] == pytest.approx(expected_skill)
    assert debug["final_atk"] == pytest.approx(build.sheet_atk + build.base_atk * 0.20 + expected_skill)


def test_raw_build_does_not_readd_homa_or_pyro_when_low_hp_switch_changes() -> None:
    build = load_hutao_builds("data/akasha/raw")[0]
    enabled = debug_build(build, ScenarioConfig(low_hp_for_homa=True))
    disabled = debug_build(build, ScenarioConfig(low_hp_for_homa=False))
    assert enabled["normalized_precombat_atk"] == disabled["normalized_precombat_atk"] == build.sheet_atk
    assert enabled["final_atk"] == disabled["final_atk"]
    assert enabled["raw_included_atk_readded"] == 0.0


def test_amber_is_absent_at_baseline_and_remains_configurable_once() -> None:
    build = load_hutao_builds("data/akasha/raw")[0]
    baseline = debug_build(build)
    amber = debug_build(build, replace(ScenarioConfig(), amber_c6_atk_pct=0.15))
    assert baseline["amber_c6_atk_pct"] == 0.0
    assert amber["final_atk"] - baseline["final_atk"] == pytest.approx(build.base_atk * 0.15)


def test_legacy_diagnostic_diff_is_exactly_the_removed_homa_term() -> None:
    build = load_hutao_builds("data/akasha/raw")[0]
    corrected = debug_build(build)["final_atk"]
    legacy = legacy_double_counted_predictions(build)
    rows = boundary_residual_rows((build,))
    assert rows[0]["legacy_double_counted_homa_low_hp_atk"] == pytest.approx(build.max_hp * 0.01)
    scale = (corrected + build.max_hp * 0.01) / corrected
    assert legacy["aggregate"] / rows[0]["after_aggregate"] == pytest.approx(scale)


def test_artifact_prediction_path_does_not_read_raw_stats_atk() -> None:
    build = load_hutao_builds("data/akasha/raw")[0]
    artifact_input = ArtifactReconstructedAtkInput(0.053, 311, 0.0)
    original = predict_components_from_artifacts(build, artifact_input)
    changed_raw = replace(build, sheet_atk=build.sheet_atk + 9999)
    changed = predict_components_from_artifacts(changed_raw, artifact_input)
    assert changed.aggregate.value == pytest.approx(original.aggregate.value)
