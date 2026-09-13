import csv
from pathlib import Path

import pytest

from genshin_opt.akasha.hutao_damage import aggregate_akasha_result
from genshin_opt.akasha.hutao_engine import debug_build, predict_components
from genshin_opt.akasha.hutao_models import ScenarioConfig
from genshin_opt.akasha.hutao_raw import load_hutao_builds
from genshin_opt.akasha.hutao_validation import compare_builds, save_comparison_csv


RAW_ROOT = Path(__file__).resolve().parents[1] / "data" / "akasha" / "raw"


@pytest.fixture(scope="module")
def builds():
    return load_hutao_builds(RAW_ROOT)


def test_duplicate_collection_runs_are_deduplicated(builds) -> None:
    assert len(builds) == 20
    assert builds[0].rank == 1


def test_confirmed_non_shimenawa_aggregate_matches_saved_akasha_raw(builds) -> None:
    build = next(item for item in builds if item.rank == 1)
    aggregate = aggregate_akasha_result(build.observed, False)
    assert aggregate.value == build.observed_result
    assert aggregate.as_dict()["q_vape_quantity"] == pytest.approx(2 / 3)


def test_confirmed_shimenawa_aggregate_matches_saved_akasha_raw(builds) -> None:
    build = next(item for item in builds if item.has_shimenawa_4pc)
    aggregate = aggregate_akasha_result(build.observed, True)
    assert aggregate.value == pytest.approx(build.observed_result, abs=1e-9)
    assert aggregate.as_dict()["q_vape_quantity"] == pytest.approx(1 / 3)


def test_prediction_exposes_all_four_components_and_aggregate(builds) -> None:
    predicted = predict_components(builds[0], ScenarioConfig())
    assert predicted.n1_vape.value > predicted.n1_non_vape.value > 0
    assert predicted.ca_vape.value > predicted.n1_vape.value
    assert predicted.q_vape.value > predicted.ca_vape.value
    assert predicted.aggregate.value > 0


def test_scenario_hypotheses_change_predictions(builds) -> None:
    build = builds[0]
    initial = predict_components(build, ScenarioConfig())
    no_external_em = predict_components(build, ScenarioConfig(hutao_external_em=0))
    no_low_hp = predict_components(build, ScenarioConfig(low_hp_for_a4=False, low_hp_for_homa=False,
                                                          low_hp_for_burst=False))
    no_vv = predict_components(build, ScenarioConfig(vv_res_reduction=0))
    assert no_external_em.n1_vape.value < initial.n1_vape.value
    assert no_low_hp.q_vape.value < initial.q_vape.value
    assert no_vv.n1_non_vape.value < initial.n1_non_vape.value


def test_debug_output_contains_required_intermediates(builds) -> None:
    debug = debug_build(builds[0])
    required = {
        "base_hp", "max_hp", "base_atk", "normalized_precombat_atk", "external_combat_atk_bonus",
        "millennial_movement_atk_pct", "amber_c6_atk_pct", "hutao_skill_atk_bonus",
        "hutao_e_atk", "final_atk", "crit_rate", "crit_dmg", "crit_multiplier",
        "em_before_external_buffs", "final_reaction_em", "vaporize_multiplier",
        "pyro_dmg_bonus", "n1_bonus", "ca_bonus", "q_bonus", "def_multiplier", "res_multiplier",
    }
    assert required <= debug.keys()
    assert debug["raw_included_atk_readded"] == 0.0


def test_raw_low_hp_homa_switch_cannot_change_final_atk(builds) -> None:
    build = builds[0]
    enabled = debug_build(build, ScenarioConfig(low_hp_for_homa=True))
    disabled = debug_build(build, ScenarioConfig(low_hp_for_homa=False))
    assert enabled["final_atk"] == disabled["final_atk"]


def test_comparison_csv_contains_observed_predicted_and_relative_errors(builds, tmp_path: Path) -> None:
    comparisons = compare_builds(builds[:3])
    output = save_comparison_csv(comparisons, tmp_path / "comparison.csv")
    with output.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 3
    assert rows[0]["observed_n1_vape"] == str(builds[0].observed.n1_vape)
    assert float(rows[0]["predicted_n1_vape"]) > 0
    assert float(rows[0]["n1_vape_relative_error"]) != 0
    assert float(rows[0]["result_relative_error"]) != 0
