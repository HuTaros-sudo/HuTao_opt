from dataclasses import replace

import pytest

from genshin_opt.akasha.calibration import (HOMA_R1_CALIBRATION, UnsupportedCalibrationError,
                                             calibrate_score, comparison_confidence,
                                             leave_one_out_validation)
from genshin_opt.akasha.hutao_raw import load_hutao_builds
from genshin_opt.akasha.hutao_score import score_hutao_akasha
from genshin_opt.optimizer import optimize
from genshin_opt.reshape_adoption import compare_artifact_adoption
from genshin_opt.storage import load_inventory


BUILDS = load_hutao_builds("data/akasha/raw", "1000004605")


def test_homa_leave_one_out_uses_training_rows_only() -> None:
    rows, summary = leave_one_out_validation(BUILDS)
    assert len(rows) == 20
    assert all(row["train_sample_count"] == 19 for row in rows)
    assert summary["full_sample_scale"] == pytest.approx(1.0768838049202214)
    assert summary["scale_min"] < summary["scale_max"]
    assert summary["uncertainty_description"] == "保存済みvalidation buildに対する経験的誤差"


def test_homa_profile_cannot_be_applied_to_another_weapon_or_leaderboard() -> None:
    with pytest.raises(UnsupportedCalibrationError):
        calibrate_score(1_000_000, HOMA_R1_CALIBRATION, "1000004607", "Ballad of the Fjords R5")
    with pytest.raises(UnsupportedCalibrationError):
        calibrate_score(1_000_000, HOMA_R1_CALIBRATION, "1000004605", "Ballad of the Fjords R5")


def test_positive_calibration_scale_preserves_optimizer_selection_and_improvement() -> None:
    inventory = load_inventory("data/sample_inventory.json")
    core_evaluator = lambda build: score_hutao_akasha(build).aggregate_score
    calibrated_evaluator = lambda build: calibrate_score(
        core_evaluator(build), HOMA_R1_CALIBRATION, "1000004605", "Staff of Homa R1").calibrated_score
    core_best = optimize(inventory, core_evaluator)
    calibrated_best = optimize(inventory, calibrated_evaluator)
    assert tuple(item.id for item in core_best.artifacts) == tuple(item.id for item in calibrated_best.artifacts)
    assert calibrated_best.score == pytest.approx(core_best.score * HOMA_R1_CALIBRATION.scale)

    lower_core, higher_core = 1_800_000.0, 1_809_000.0
    core_improvement = higher_core / lower_core - 1
    calibrated_improvement = ((higher_core * HOMA_R1_CALIBRATION.scale)
                              / (lower_core * HOMA_R1_CALIBRATION.scale) - 1)
    assert calibrated_improvement == pytest.approx(core_improvement)


def test_artifact_adoption_improvement_is_calibration_invariant() -> None:
    inventory = load_inventory("data/sample_inventory.json")
    original = inventory.artifacts[0]
    first_substat = original.substats[0]
    reconstructed = replace(original, substats=(replace(first_substat, value=first_substat.value + 0.01),
                                                 *original.substats[1:]))
    evaluator = lambda build: score_hutao_akasha(build).aggregate_score
    comparison = compare_artifact_adoption(inventory, original.id, original, reconstructed, evaluator)
    core_improvement = comparison.improvement_percent / 100
    calibrated_original = comparison.original.best.score * HOMA_R1_CALIBRATION.scale
    calibrated_reconstructed = comparison.reconstructed.best.score * HOMA_R1_CALIBRATION.scale
    calibrated_improvement = calibrated_reconstructed / calibrated_original - 1
    assert calibrated_improvement == pytest.approx(core_improvement)
    assert comparison.verdict.value in {"reconstructed_better", "original_better", "uncertain"}


def test_confidence_labels_use_absolute_relative_difference() -> None:
    assert comparison_confidence(0.001).label == "very uncertain"
    assert comparison_confidence(-0.003).label == "uncertain"
    assert comparison_confidence(0.007).label == "moderate confidence"
    assert comparison_confidence(-0.02).label == "higher confidence"


def test_core_model_v1_score_is_bit_identical() -> None:
    result = score_hutao_akasha(BUILDS[0])
    actual = tuple(value.hex() for value in (result.n1_non_vape_avg, result.n1_vape_avg,
                                              result.ca_vape_avg, result.q_vape_avg,
                                              result.aggregate_score))
    assert actual == (
        "0x1.26b0389b5c47cp+14", "0x1.a8f0c17e4e4c6p+15", "0x1.3448ff839809ep+17",
        "0x1.7135f0da10e1ep+18", "0x1.1d635d97b334fp+21",
    )
