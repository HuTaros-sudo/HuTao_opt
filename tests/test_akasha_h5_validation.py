import pytest

from genshin_opt.akasha.h5_validation import (ARTIFACT_ATK_BY_UID, model_comparison_rows,
                                              reconstruct_atk_stages, residual_rows)
from genshin_opt.akasha.hutao_raw import load_hutao_builds


RAW_ROOT = "data/akasha/raw"


def test_all_20_builds_have_independently_observed_artifact_atk_breakdown():
    builds = load_hutao_builds(RAW_ROOT)
    assert len(builds) == 20
    assert {build.uid for build in builds} == set(ARTIFACT_ATK_BY_UID)


def test_raw_atk_is_reconstructed_by_low_hp_homa_and_pyro_resonance():
    builds = load_hutao_builds(RAW_ROOT)
    errors = [reconstruct_atk_stages(build)["raw_atk_reconstruction_error"] for build in builds]
    # AkashaカードのATK%は小数第1位、flat ATKは整数表示なので1未満の差を許容する。
    assert max(abs(error) for error in errors) < 1.0


def test_model_comparison_covers_two_bases_five_models_and_five_components():
    rows = model_comparison_rows(load_hutao_builds(RAW_ROOT))
    assert len(rows) == 2 * 5 * 5
    assert {row["model"] for row in rows} == {"A", "B", "C", "D", "E"}


def test_component_ratios_are_constant_within_each_build_for_external_atk_change():
    rows = residual_rows(load_hutao_builds(RAW_ROOT))
    assert max(float(row["component_ratio_range"]) for row in rows) < 0.002
