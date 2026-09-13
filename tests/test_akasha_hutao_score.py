from statistics import mean

import pytest

from genshin_opt.akasha import (HypothesisStatus, ScenarioConfig, load_hutao_builds,
                                normalize_hutao_akasha_input, score_hutao_akasha)
from genshin_opt.models import Artifact, Inventory, Slot, Stat, StatValue, Substat
from genshin_opt.optimizer import at_least_set_pieces, optimize


RAW_ROOT = "data/akasha/raw"
MAIN_STATS = {
    Slot.FLOWER: StatValue(Stat.HP_FLAT, 4780),
    Slot.PLUME: StatValue(Stat.ATK_FLAT, 311),
    Slot.SANDS: StatValue(Stat.HP_PERCENT, 0.466),
    Slot.GOBLET: StatValue(Stat.PYRO_DMG, 0.466),
    Slot.CIRCLET: StatValue(Stat.CRIT_RATE, 0.311),
}
SUBSTATS = {
    Slot.FLOWER: (Substat(Stat.CRIT_RATE, 0.10), Substat(Stat.CRIT_DMG, 0.20),
                  Substat(Stat.ELEMENTAL_MASTERY, 40), Substat(Stat.ATK_PERCENT, 0.05)),
    Slot.PLUME: (Substat(Stat.CRIT_RATE, 0.10), Substat(Stat.CRIT_DMG, 0.20),
                 Substat(Stat.ELEMENTAL_MASTERY, 40), Substat(Stat.HP_PERCENT, 0.05)),
    Slot.SANDS: (Substat(Stat.CRIT_RATE, 0.10), Substat(Stat.CRIT_DMG, 0.20),
                 Substat(Stat.ELEMENTAL_MASTERY, 40), Substat(Stat.ATK_FLAT, 20)),
    Slot.GOBLET: (Substat(Stat.CRIT_RATE, 0.10), Substat(Stat.CRIT_DMG, 0.20),
                  Substat(Stat.ELEMENTAL_MASTERY, 40), Substat(Stat.HP_PERCENT, 0.05)),
    Slot.CIRCLET: (Substat(Stat.CRIT_DMG, 0.20), Substat(Stat.ELEMENTAL_MASTERY, 40),
                   Substat(Stat.HP_PERCENT, 0.05), Substat(Stat.ATK_PERCENT, 0.05)),
}


def optimizer_build() -> tuple[Artifact, ...]:
    return tuple(Artifact(
        id=f"score-{slot.value}", slot=slot, set_name="火魔女" if slot != Slot.CIRCLET else "その他",
        rarity=5, level=20, main_stat=MAIN_STATS[slot], substats=SUBSTATS[slot]) for slot in Slot)


def test_public_score_matches_existing_engine_for_saved_raw_build() -> None:
    build = load_hutao_builds(RAW_ROOT)[0]
    result = score_hutao_akasha(build, ScenarioConfig())
    assert result.n1_non_vape_avg > 0
    assert result.n1_vape_avg > result.n1_non_vape_avg
    assert result.ca_vape_avg > result.n1_vape_avg
    assert result.q_vape_avg > result.ca_vape_avg
    assert result.debug_breakdown["components"]["aggregate"]["n1_vape_quantity"] == 4
    assert result.debug_breakdown["components"]["aggregate"]["n1_non_vape_quantity"] == 7
    assert result.debug_breakdown["components"]["aggregate"]["ca_vape_quantity"] == 11
    assert result.debug_breakdown["components"]["aggregate"]["q_vape_quantity"] == pytest.approx(2 / 3)
    shimenawa = next(item for item in load_hutao_builds(RAW_ROOT) if item.has_shimenawa_4pc)
    shimenawa_result = score_hutao_akasha(shimenawa)
    assert shimenawa_result.debug_breakdown["components"]["aggregate"]["q_vape_quantity"] == pytest.approx(1 / 3)


def test_default_scenario_records_current_fixed_boundaries() -> None:
    config = ScenarioConfig()
    assert config.character_level == 90
    assert config.skill_talent_level == 10
    assert config.raw_max_hp_includes_homa_hp is True
    assert config.low_hp_for_a4 is True
    assert config.kazuha_em_for_a4 == pytest.approx(1420)
    assert config.freedom_sworn_normal_charged_bonus == pytest.approx(0.16)
    assert config.apply_crimson_witch_skill_stack is True
    assert config.apply_shimenawa_damage_bonus is True
    assert config.burst_uptime_non_shimenawa == pytest.approx(2 / 3)
    assert config.burst_uptime_shimenawa == pytest.approx(1 / 3)


def test_result_exposes_hypothesis_states_and_estimate_marker() -> None:
    result = score_hutao_akasha(load_hutao_builds(RAW_ROOT)[0])
    states = {state.hypothesis_id: state.status for state in result.hypothesis_states}
    assert result.is_estimate is True
    assert result.debug_breakdown["model_status"] == "estimated_not_fully_reproduced"
    assert states == {
        "H1": HypothesisStatus.STRONGLY_SUPPORTED, "H3": HypothesisStatus.UNRESOLVED,
        "H4": HypothesisStatus.STRONGLY_SUPPORTED, "H5": HypothesisStatus.STRONGLY_SUPPORTED,
        "H6": HypothesisStatus.STRONGLY_SUPPORTED, "H7": HypothesisStatus.STRONGLY_SUPPORTED,
        "aggregate": HypothesisStatus.CONFIRMED,
    }


def test_scenario_keeps_unresolved_enemy_conditions_replaceable() -> None:
    build = load_hutao_builds(RAW_ROOT)[0]
    baseline = score_hutao_akasha(build, ScenarioConfig())
    alternative = score_hutao_akasha(build, ScenarioConfig(enemy_level=100, enemy_base_pyro_res=0.0,
                                                            vv_res_reduction=0.0))
    assert alternative.aggregate_score != pytest.approx(baseline.aggregate_score)
    assert alternative.debug_breakdown["scenario_config"]["enemy_level"] == 100


def test_optimizer_build_is_normalized_and_scores_through_plain_lambda() -> None:
    build = optimizer_build()
    normalized = normalize_hutao_akasha_input(build)
    assert normalized.base_atk == pytest.approx(714)
    assert normalized.pyro_dmg_bonus == pytest.approx(0.616)
    assert normalized.has_crimson_witch_4pc
    config = ScenarioConfig()
    inventory = Inventory(1, build)
    result = optimize(inventory, lambda candidate: score_hutao_akasha(candidate, config).aggregate_score,
                      at_least_set_pieces("火魔女", 4))
    assert result.artifacts == build
    assert result.score > 0


def test_saved_20_build_baseline_diagnostic_does_not_regress() -> None:
    builds = load_hutao_builds(RAW_ROOT)
    expected = {
        "n1_non_vape": (-0.07217040315371896, 0.07770731470452852),
        "n1_vape": (-0.0719037086070898, 0.07741191069798575),
        "ca_vape": (-0.07119548537593076, 0.07670789073400816),
        "q_vape": (-0.07201040249488526, 0.07751797136323618),
        "aggregate": (-0.07140289807310361, 0.07691408260994405),
    }
    errors = {component: [] for component in expected}
    for build in builds:
        result = score_hutao_akasha(build)
        observed = {
            "n1_non_vape": build.observed.n1_non_vape, "n1_vape": build.observed.n1_vape,
            "ca_vape": build.observed.ca_vape, "q_vape": build.observed.q_vape,
            "aggregate": build.observed_result,
        }
        predicted = {
            "n1_non_vape": result.n1_non_vape_avg, "n1_vape": result.n1_vape_avg,
            "ca_vape": result.ca_vape_avg, "q_vape": result.q_vape_avg,
            "aggregate": result.aggregate_score,
        }
        for component in expected:
            errors[component].append((predicted[component] - observed[component]) / observed[component])
    assert len(builds) == 20
    for component, (expected_mean, expected_max_abs) in expected.items():
        assert mean(errors[component]) == pytest.approx(expected_mean, abs=1e-12)
        assert max(map(abs, errors[component])) == pytest.approx(expected_max_abs, abs=1e-12)
