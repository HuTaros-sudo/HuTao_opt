"""Akasha胡桃の4 componentを組み立て、途中値を追跡する。"""

from .hutao_damage import (CRIMSON_WITCH_SKILL_STACK_PYRO_BONUS, HUTAO_A4_PYRO_BONUS,
                           KAZUHA_A4_BONUS_PER_EM,
                           SHIMENAWA_NORMAL_CHARGED_BONUS, aggregate_akasha_result,
                           ca_vape_damage, character_base_stats, crit_multiplier, damage_bonus,
                           enemy_def_multiplier, enemy_res_multiplier, external_combat_atk_bonus,
                           final_combat_atk, hutao_skill_atk_bonus, max_hp_from_observed,
                           normalized_precombat_atk_from_artifacts, normalized_precombat_atk_from_raw,
                           n1_non_vape_damage, n1_vape_damage, q_vape_damage,
                           resolve_talent_multipliers, vaporize_multiplier)
from .hutao_models import (ArtifactReconstructedAtkInput, AttackTypeDamageBonus,
                           CommonPyroDamageBonus, FinalCombatAtk, ObservedComponents,
                           HutaoAkashaInput, PredictedComponents, ScenarioConfig)


def damage_bonus_inputs(build: HutaoAkashaInput, scenario: ScenarioConfig) -> tuple[CommonPyroDamageBonus, AttackTypeDamageBonus]:
    """raw由来の共通炎Bonusと、N1/CA固有Bonusを型で分離する。"""
    a4_bonus = HUTAO_A4_PYRO_BONUS if scenario.low_hp_for_a4 else 0.0
    kazuha_bonus = scenario.kazuha_em_for_a4 * KAZUHA_A4_BONUS_PER_EM
    set_pyro_bonus = (CRIMSON_WITCH_SKILL_STACK_PYRO_BONUS
                      if build.has_crimson_witch_4pc and scenario.apply_crimson_witch_skill_stack else 0.0)
    shimenawa_bonus = (SHIMENAWA_NORMAL_CHARGED_BONUS
                       if build.has_shimenawa_4pc and scenario.apply_shimenawa_damage_bonus else 0.0)
    common = CommonPyroDamageBonus(build.pyro_dmg_bonus, a4_bonus, kazuha_bonus, set_pyro_bonus)
    attack_type = AttackTypeDamageBonus(scenario.freedom_sworn_normal_charged_bonus, shimenawa_bonus)
    return common, attack_type


def predict_components(build: HutaoAkashaInput, config: ScenarioConfig | None = None) -> PredictedComponents:
    scenario = config or ScenarioConfig()
    base_hp, _ = character_base_stats(scenario.character_level)
    talents = resolve_talent_multipliers(scenario)
    hp = max_hp_from_observed(build.max_hp, base_hp, scenario.raw_max_hp_includes_homa_hp)
    normalized_atk = normalized_precombat_atk_from_raw(build.sheet_atk, build.base_atk, build.input_source)
    external_atk = external_combat_atk_bonus(build.base_atk, scenario.external_atk_pct, scenario.amber_c6_atk_pct)
    skill_atk = hutao_skill_atk_bonus(hp.value, build.base_atk, talents.skill_hp_to_atk)
    atk = final_combat_atk(normalized_atk, external_atk, skill_atk)
    return _predict_from_final_combat_atk(build, atk, scenario)


def predict_components_from_artifacts(build: HutaoAkashaInput, artifact_input: ArtifactReconstructedAtkInput,
                                      config: ScenarioConfig | None = None) -> PredictedComponents:
    """raw stats.atkを参照せず、聖遺物ATK内訳から作った境界で予測する。"""
    scenario = config or ScenarioConfig()
    base_hp, _ = character_base_stats(scenario.character_level)
    talents = resolve_talent_multipliers(scenario)
    hp = max_hp_from_observed(build.max_hp, base_hp, scenario.raw_max_hp_includes_homa_hp)
    normalized_atk = normalized_precombat_atk_from_artifacts(
        build.base_atk, hp.value, artifact_input.artifact_atk_pct, artifact_input.artifact_flat_atk,
        artifact_input.artifact_set_atk_pct, artifact_input.pyro_resonance_atk_pct, scenario.low_hp_for_homa)
    external_atk = external_combat_atk_bonus(build.base_atk, scenario.external_atk_pct, scenario.amber_c6_atk_pct)
    skill_atk = hutao_skill_atk_bonus(hp.value, build.base_atk, talents.skill_hp_to_atk)
    atk = final_combat_atk(normalized_atk, external_atk, skill_atk)
    return _predict_from_final_combat_atk(build, atk, scenario)


def _predict_from_final_combat_atk(build: HutaoAkashaInput, atk: FinalCombatAtk,
                                   scenario: ScenarioConfig) -> PredictedComponents:
    talents = resolve_talent_multipliers(scenario)
    crit = crit_multiplier(build.crit_rate, build.crit_dmg)
    final_em = build.elemental_mastery + scenario.hutao_external_em
    reaction_bonus = (scenario.crimson_witch_vape_bonus
                      if build.has_crimson_witch_4pc and scenario.apply_crimson_witch_vape_bonus else 0.0)
    vaporize = vaporize_multiplier(final_em, reaction_bonus, scenario.vaporize_base_multiplier,
                                   scenario.vaporize_em_coefficient, scenario.vaporize_em_denominator)
    common, attack_type = damage_bonus_inputs(build, scenario)
    normal_bonus = damage_bonus(common.raw_pyro_bonus, attack_type.total, common.hutao_a4_bonus,
                                common.kazuha_a4_bonus, common.crimson_witch_stack_bonus)
    charged_bonus = damage_bonus(common.raw_pyro_bonus, attack_type.total, common.hutao_a4_bonus,
                                 common.kazuha_a4_bonus, common.crimson_witch_stack_bonus)
    burst_bonus = damage_bonus(common.raw_pyro_bonus, 0.0, common.hutao_a4_bonus,
                               common.kazuha_a4_bonus, common.crimson_witch_stack_bonus)
    defense = enemy_def_multiplier(scenario.character_level, scenario.enemy_level)
    resistance = enemy_res_multiplier(scenario.enemy_base_pyro_res, scenario.vv_res_reduction)
    rounding = scenario.internal_rounding_mode
    n1_non_vape = n1_non_vape_damage(atk.value, talents.n1, normal_bonus.value, crit.value,
                                     defense.value, resistance.value, rounding)
    n1_vape = n1_vape_damage(atk.value, talents.n1, normal_bonus.value, crit.value,
                             defense.value, resistance.value, vaporize.value, rounding)
    ca_vape = ca_vape_damage(atk.value, talents.charged, charged_bonus.value, crit.value,
                             defense.value, resistance.value, vaporize.value, rounding)
    burst_talent = talents.burst_low_hp if scenario.low_hp_for_burst else talents.burst_normal_hp
    q_vape = q_vape_damage(atk.value, burst_talent, burst_bonus.value, crit.value,
                           defense.value, resistance.value, vaporize.value, rounding)
    values = ObservedComponents(n1_vape.value, n1_non_vape.value, ca_vape.value, q_vape.value)
    aggregate = aggregate_akasha_result(values, build.has_shimenawa_4pc, scenario)
    return PredictedComponents(n1_vape, n1_non_vape, ca_vape, q_vape, aggregate)


def debug_build(build: HutaoAkashaInput, config: ScenarioConfig | None = None) -> dict[str, object]:
    """1 buildの要求済み中間値と、raw残差の注記を返す。"""
    scenario = config or ScenarioConfig()
    base_hp, _ = character_base_stats(scenario.character_level)
    talents = resolve_talent_multipliers(scenario)
    hp = max_hp_from_observed(build.max_hp, base_hp, scenario.raw_max_hp_includes_homa_hp)
    normalized_atk = normalized_precombat_atk_from_raw(build.sheet_atk, build.base_atk, build.input_source)
    external_atk = external_combat_atk_bonus(build.base_atk, scenario.external_atk_pct, scenario.amber_c6_atk_pct)
    skill_atk = hutao_skill_atk_bonus(hp.value, build.base_atk, talents.skill_hp_to_atk)
    atk = final_combat_atk(normalized_atk, external_atk, skill_atk)
    crit = crit_multiplier(build.crit_rate, build.crit_dmg)
    final_em = build.elemental_mastery + scenario.hutao_external_em
    reaction_bonus = (scenario.crimson_witch_vape_bonus
                      if build.has_crimson_witch_4pc and scenario.apply_crimson_witch_vape_bonus else 0.0)
    vaporize = vaporize_multiplier(final_em, reaction_bonus, scenario.vaporize_base_multiplier,
                                   scenario.vaporize_em_coefficient, scenario.vaporize_em_denominator)
    common, attack_type = damage_bonus_inputs(build, scenario)
    normal = damage_bonus(common.raw_pyro_bonus, attack_type.total, common.hutao_a4_bonus,
                          common.kazuha_a4_bonus, common.crimson_witch_stack_bonus)
    charged = damage_bonus(common.raw_pyro_bonus, attack_type.total, common.hutao_a4_bonus,
                           common.kazuha_a4_bonus, common.crimson_witch_stack_bonus)
    burst = damage_bonus(common.raw_pyro_bonus, 0.0, common.hutao_a4_bonus,
                         common.kazuha_a4_bonus, common.crimson_witch_stack_bonus)
    defense = enemy_def_multiplier(scenario.character_level, scenario.enemy_level)
    resistance = enemy_res_multiplier(scenario.enemy_base_pyro_res, scenario.vv_res_reduction)
    return {
        "input_type": type(build).__name__, "input_source": build.input_source,
        "leaderboard_id": getattr(build, "leaderboard_id", None),
        "rank": getattr(build, "rank", None), "uid": getattr(build, "uid", None),
        "base_hp": base_hp, "max_hp": hp.value, "base_atk": build.base_atk,
        "normalized_precombat_atk": normalized_atk.value, "normalized_precombat_atk_source": normalized_atk.source,
        "external_combat_atk_pct": scenario.external_atk_pct + scenario.amber_c6_atk_pct,
        "external_combat_atk_bonus": external_atk.value,
        "millennial_movement_atk_pct": scenario.external_atk_pct,
        "amber_c6_atk_pct": scenario.amber_c6_atk_pct,
        "hutao_skill_atk_bonus": skill_atk.value, "hutao_e_atk": skill_atk.value,
        "hutao_e_atk_uncapped": skill_atk.uncapped_value, "hutao_e_atk_cap": skill_atk.cap,
        "final_atk": atk.value, "raw_included_atk_readded": 0.0,
        "crit_rate": build.crit_rate, "crit_dmg": build.crit_dmg, "crit_multiplier": crit.value,
        "em_before_external_buffs": build.elemental_mastery, "final_reaction_em": final_em,
        "vaporize_multiplier": vaporize.value, "pyro_dmg_bonus": build.pyro_dmg_bonus,
        "common_pyro_bonus": common.total, "raw_pyro_bonus": common.raw_pyro_bonus,
        "hutao_a4_pyro_bonus": common.hutao_a4_bonus, "kazuha_a4_pyro_bonus": common.kazuha_a4_bonus,
        "crimson_witch_stack_pyro_bonus": common.crimson_witch_stack_bonus,
        "freedom_sworn_attack_type_bonus": attack_type.freedom_sworn_bonus,
        "shimenawa_attack_type_bonus": attack_type.shimenawa_bonus,
        "n1_bonus": normal.as_dict()["total_dmg_bonus"],
        "ca_bonus": charged.as_dict()["total_dmg_bonus"],
        "q_bonus": burst.as_dict()["total_dmg_bonus"],
        "def_multiplier": defense.value, "res_multiplier": resistance.value,
        "artifact_sets": dict(build.artifact_sets),
        "decomposition_note": ("raw stats.atk + raw未包含の外部ATK + 胡桃E。護摩・炎共鳴・聖遺物はrawから再加算しない"
                               if build.input_source == "akasha_leaderboard_raw"
                               else "5聖遺物から再構築したraw相当ATK + 外部ATK + 胡桃E"),
    }
