from dataclasses import replace

import pytest

from genshin_opt.akasha.h6_validation import (freedom_candidate_rows, kazuha_candidate_rows,
                                               raw_pyro_bonus_rows)
from genshin_opt.akasha.hutao_engine import damage_bonus_inputs, predict_components
from genshin_opt.akasha.hutao_models import ScenarioConfig
from genshin_opt.akasha.hutao_raw import load_hutao_builds


def test_raw_pyro_bonus_is_only_goblet_and_static_crimson_witch_2pc() -> None:
    rows = raw_pyro_bonus_rows(load_hutao_builds("data/akasha/raw"))
    assert len(rows) == 20
    for row in rows:
        assert row["a_artifact_only"] == pytest.approx(row["raw_stats_pyro_damage_bonus"], abs=1e-8)
    shimenawa = next(row for row in rows if row["has_shimenawa_4pc"])
    assert shimenawa["raw_stats_pyro_damage_bonus"] == pytest.approx(0.466, abs=1e-8)
    assert shimenawa["crimson_witch_2pc_bonus"] == 0.0


def test_damage_bonus_boundary_separates_common_and_attack_type_sources() -> None:
    builds = load_hutao_builds("data/akasha/raw")
    crimson = next(build for build in builds if build.has_crimson_witch_4pc)
    shimenawa = next(build for build in builds if build.has_shimenawa_4pc)
    common, attack_type = damage_bonus_inputs(crimson, ScenarioConfig())
    assert common.raw_pyro_bonus == pytest.approx(0.616, abs=1e-8)
    assert common.hutao_a4_bonus == pytest.approx(0.33)
    assert common.kazuha_a4_bonus == pytest.approx(0.568)
    assert common.crimson_witch_stack_bonus == pytest.approx(0.075)
    assert attack_type.freedom_sworn_bonus == pytest.approx(0.16)
    assert attack_type.shimenawa_bonus == 0.0
    shim_common, shim_attack_type = damage_bonus_inputs(shimenawa, ScenarioConfig())
    assert shim_common.crimson_witch_stack_bonus == 0.0
    assert shim_attack_type.shimenawa_bonus == pytest.approx(0.50)


def test_kazuha_candidate_changes_all_components_but_not_other_settings() -> None:
    build = load_hutao_builds("data/akasha/raw")[0]
    no_kazuha = predict_components(build, replace(ScenarioConfig(), kazuha_em_for_a4=0))
    em1420 = predict_components(build, replace(ScenarioConfig(), kazuha_em_for_a4=1420))
    assert em1420.n1_non_vape.value > no_kazuha.n1_non_vape.value
    assert em1420.n1_vape.value > no_kazuha.n1_vape.value
    assert em1420.ca_vape.value > no_kazuha.ca_vape.value
    assert em1420.q_vape.value > no_kazuha.q_vape.value
    rows = kazuha_candidate_rows((build,))
    assert {row["candidate_id"] for row in rows} == {
        "kazuha_raw_included_0", "kazuha_1000_em_40", "kazuha_1420_em_56_8"}


def test_freedom_sworn_changes_n1_and_ca_but_never_q() -> None:
    build = load_hutao_builds("data/akasha/raw")[0]
    enabled = predict_components(build, ScenarioConfig(freedom_sworn_normal_charged_bonus=0.16))
    disabled = predict_components(build, ScenarioConfig(freedom_sworn_normal_charged_bonus=0.0))
    assert enabled.n1_non_vape.value > disabled.n1_non_vape.value
    assert enabled.n1_vape.value > disabled.n1_vape.value
    assert enabled.ca_vape.value > disabled.ca_vape.value
    assert enabled.q_vape.value == pytest.approx(disabled.q_vape.value)


def test_shimenawa_50_percent_is_attack_type_specific_for_single_build() -> None:
    builds = load_hutao_builds("data/akasha/raw")
    rows = freedom_candidate_rows(builds)
    enabled = next(row for row in rows if row["candidate_id"] == "shimenawa_50")
    disabled = next(row for row in rows if row["candidate_id"] == "shimenawa_0")
    assert enabled["uid"] == disabled["uid"]
    assert enabled["predicted_n1_non_vape"] > disabled["predicted_n1_non_vape"]
    assert enabled["predicted_ca_vape"] > disabled["predicted_ca_vape"]
    assert enabled["predicted_q_vape"] == pytest.approx(disabled["predicted_q_vape"])
