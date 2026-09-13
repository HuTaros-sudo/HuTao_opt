import pytest

from genshin_opt.akasha.hutao_damage import (aggregate_akasha_result, ca_vape_damage,
                                              crit_multiplier, damage_bonus,
                                              enemy_def_multiplier, enemy_res_multiplier, external_combat_atk_bonus,
                                              final_combat_atk, hutao_skill_atk_bonus,
                                              max_hp, max_hp_from_observed, n1_non_vape_damage, n1_vape_damage,
                                              normalized_precombat_atk_from_artifacts,
                                              normalized_precombat_atk_from_raw, q_vape_damage,
                                              vaporize_multiplier)
from genshin_opt.akasha.hutao_models import (InternalRoundingMode, ObservedComponents,
                                             ScenarioConfig)


def test_max_hp_uses_base_percent_homa_and_flat_hp() -> None:
    result = max_hp(15552, 0.466, 4780)
    assert result.value == pytest.approx(15552 * (1 + 0.466 + 0.20) + 4780)
    assert result.as_dict()["homa_hp_pct"] == pytest.approx(0.20)


def test_observed_max_hp_homa_inclusion_is_switchable() -> None:
    included = max_hp_from_observed(30000, 15552, True)
    excluded = max_hp_from_observed(30000, 15552, False)
    assert included.value == 30000
    assert excluded.value == pytest.approx(30000 + 15552 * 0.20)


def test_raw_atk_boundary_adds_only_external_and_hutao_skill_once() -> None:
    normalized = normalized_precombat_atk_from_raw(1800, 714)
    external = external_combat_atk_bonus(714, 0.20, 0.0)
    skill = hutao_skill_atk_bonus(30000, 714, 0.0626)
    result = final_combat_atk(normalized, external, skill)
    assert normalized.value == 1800
    assert external.value == pytest.approx(714 * 0.20)
    assert skill.value == pytest.approx(30000 * 0.0626)
    assert result.value == pytest.approx(1800 + 714 * 0.20 + 30000 * 0.0626)


def test_hutao_skill_bonus_is_capped_independently() -> None:
    capped = hutao_skill_atk_bonus(100000, 714, 0.0626)
    assert capped.value == pytest.approx(714 * 4)
    assert capped.uncapped_value == pytest.approx(6260)


def test_raw_path_cannot_readd_homa_or_pyro_resonance() -> None:
    normalized = normalized_precombat_atk_from_raw(1800, 714)
    assert normalized.value == 1800
    assert normalized.source == "akasha_raw_stats_atk"


def test_artifact_path_reconstructs_homa_and_pyro_before_combat() -> None:
    normalized = normalized_precombat_atk_from_artifacts(714, 30000, 0.10, 311, 0.18, 0.25, True)
    expected = 714 * (1 + 0.10 + 0.18 + 0.25) + 311 + 30000 * 0.018
    assert normalized.value == pytest.approx(expected)
    assert normalized.source == "artifact_reconstructed"


def test_baseline_has_one_millennial_buff_and_no_amber_c6() -> None:
    config = ScenarioConfig()
    result = external_combat_atk_bonus(714, config.external_atk_pct, config.amber_c6_atk_pct)
    assert config.external_atk_pct == pytest.approx(0.20)
    assert config.amber_c6_atk_pct == 0.0
    assert result.value == pytest.approx(714 * 0.20)


def test_crit_expected_value_clamps_rate() -> None:
    assert crit_multiplier(0.75, 2.0).value == pytest.approx(2.5)
    assert crit_multiplier(1.2, 2.0).value == pytest.approx(3.0)
    assert crit_multiplier(-0.2, 2.0).value == pytest.approx(1.0)


def test_pyro_vaporize_uses_em_and_reaction_bonus() -> None:
    assert vaporize_multiplier(0).value == pytest.approx(1.5)
    expected = 1.5 * (1 + 2.78 * 500 / 1900 + 0.15)
    assert vaporize_multiplier(500, 0.15).value == pytest.approx(expected)


def test_damage_bonus_keeps_each_source_visible() -> None:
    result = damage_bonus(0.466, 0.16, 0.33, 0.568, 0.075)
    assert result.as_dict()["total_dmg_bonus"] == pytest.approx(1.599)
    assert result.value == pytest.approx(2.599)


def test_enemy_def_equal_levels_without_shred_is_half() -> None:
    assert enemy_def_multiplier(90, 90).value == pytest.approx(0.5)


@pytest.mark.parametrize("base,reduction,expected", [
    (0.10, 0.40, 1.15), (0.10, 0.0, 0.90), (0.80, 0.0, 1 / 4.2),
])
def test_enemy_res_piecewise_formula(base: float, reduction: float, expected: float) -> None:
    assert enemy_res_multiplier(base, reduction).value == pytest.approx(expected)


def test_named_hit_functions_use_reaction_only_for_vape() -> None:
    args = (4000.0, 0.836, 2.5, 3.0, 0.5, 1.15)
    non_vape = n1_non_vape_damage(*args)
    n1_vape = n1_vape_damage(*args, 2.8)
    ca_vape = ca_vape_damage(4000, 2.426, 2.5, 3.0, 0.5, 1.15, 2.8)
    q_vape = q_vape_damage(4000, 6.17, 2.3, 3.0, 0.5, 1.15, 2.8)
    assert n1_vape.value == pytest.approx(non_vape.value * 2.8)
    assert ca_vape.value > n1_vape.value
    assert q_vape.value > ca_vape.value


def test_internal_rounding_mode_is_switchable() -> None:
    value = n1_non_vape_damage(1, 1.9, 1, 1, 1, 1, InternalRoundingMode.NONE)
    floored = n1_non_vape_damage(1, 1.9, 1, 1, 1, 1, InternalRoundingMode.FLOOR_PER_HIT)
    rounded = n1_non_vape_damage(1, 1.9, 1, 1, 1, 1, InternalRoundingMode.ROUND_PER_HIT)
    assert value.value == pytest.approx(1.9)
    assert floored.value == 1
    assert rounded.value == 2


def test_aggregate_quantities_are_confirmed_defaults_but_uptime_is_configurable() -> None:
    values = ObservedComponents(10, 20, 30, 40)
    normal = aggregate_akasha_result(values, False)
    shimenawa = aggregate_akasha_result(values, True)
    custom = aggregate_akasha_result(values, False, ScenarioConfig(burst_uptime_non_shimenawa=0.5))
    assert normal.value == pytest.approx(4 * 10 + 7 * 20 + 11 * 30 + (2 / 3) * 40)
    assert shimenawa.value == pytest.approx(4 * 10 + 7 * 20 + 11 * 30 + (1 / 3) * 40)
    assert custom.value == pytest.approx(4 * 10 + 7 * 20 + 11 * 30 + 0.5 * 40)
