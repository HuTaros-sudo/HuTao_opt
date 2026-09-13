"""docs/akasha_hutao_spec.mdに基づく、小さな純粋Damage計算。"""

import math

from .hutao_models import (CalculationBreakdown, ExternalCombatAtkBonus, FinalCombatAtk,
                           HutaoModelError, HutaoSkillAtkBonus, InternalRoundingMode,
                           NormalizedPrecombatAtk, ObservedComponents, ScenarioConfig,
                           TalentMultipliers)


# 仕様書でconfirmedのLv.90/Lv.100基礎値と、表示上のLv.10天賦倍率。
CHARACTER_BASE_STATS = {90: (15552.0, 106.0), 100: (16658.0, 130.0)}
DISPLAYED_LEVEL_10_TALENTS = TalentMultipliers(0.836, 2.426, 0.0626, 4.94, 6.17)
HOMA_BASE_HP_PCT = 0.20
HOMA_BASE_ATK_FROM_HP = 0.008
HOMA_LOW_HP_EXTRA_ATK_FROM_HP = 0.010
HUTAO_A4_PYRO_BONUS = 0.33
KAZUHA_A4_BONUS_PER_EM = 0.0004
CRIMSON_WITCH_2PC_PYRO_BONUS = 0.15
CRIMSON_WITCH_SKILL_STACK_PYRO_BONUS = 0.075
CRIMSON_WITCH_VAPE_BONUS = 0.15
SHIMENAWA_NORMAL_CHARGED_BONUS = 0.50
E_ATK_CAP_BASE_ATK_MULTIPLIER = 4.0
PYRO_VAPE_BASE_MULTIPLIER = 1.5
EM_REACTION_COEFFICIENT = 2.78
EM_REACTION_DENOMINATOR = 1400.0


def _breakdown(value: float, **details: object) -> CalculationBreakdown:
    return CalculationBreakdown(float(value), tuple(details.items()))


def character_base_stats(level: int) -> tuple[float, float]:
    try:
        return CHARACTER_BASE_STATS[level]
    except KeyError as error:
        raise HutaoModelError(f"仕様書に基礎値がないcharacter_levelです: {level}") from error


def resolve_talent_multipliers(config: ScenarioConfig) -> TalentMultipliers:
    levels = (config.normal_attack_talent_level, config.skill_talent_level, config.burst_talent_level)
    if config.talent_multiplier_override is not None:
        return config.talent_multiplier_override
    if levels != (10, 10, 10):
        raise HutaoModelError("Lv.10以外はtalent_multiplier_overrideも指定してください")
    return DISPLAYED_LEVEL_10_TALENTS


def max_hp(base_hp: float, hp_pct: float, flat_hp: float, homa_hp_pct: float = HOMA_BASE_HP_PCT) -> CalculationBreakdown:
    value = base_hp * (1 + hp_pct + homa_hp_pct) + flat_hp
    return _breakdown(value, base_hp=base_hp, hp_pct=hp_pct, homa_hp_pct=homa_hp_pct, flat_hp=flat_hp)


def max_hp_from_observed(observed_max_hp: float, base_hp: float,
                         raw_includes_homa_hp: bool = True) -> CalculationBreakdown:
    """Leaderboard rawが既に集約したMax HPを、再分解せず計算へ渡す。"""
    homa_hp_to_add = 0.0 if raw_includes_homa_hp else base_hp * HOMA_BASE_HP_PCT
    value = observed_max_hp + homa_hp_to_add
    return _breakdown(value, base_hp=base_hp, observed_max_hp=observed_max_hp,
                      raw_includes_homa_hp=raw_includes_homa_hp, homa_hp_added_after_raw=homa_hp_to_add,
                      hp_pct=None, homa_hp_pct=None, flat_hp=None,
                      decomposition="rawにはHP%とflat HPの内訳がないため集約値を使用")


def normalized_precombat_atk_from_raw(raw_stats_atk: float, base_atk: float,
                                      source: str = "akasha_raw_stats_atk") -> NormalizedPrecombatAtk:
    """raw値を同義の型へ変換する。raw内のATK要素を再加算する引数は受け取らない。"""
    if raw_stats_atk < 0 or base_atk <= 0:
        raise HutaoModelError("raw stats.atkは0以上、base ATKは正で指定してください")
    return NormalizedPrecombatAtk(raw_stats_atk, base_atk, source)


def normalized_precombat_atk_from_artifacts(base_atk: float, max_hp_value: float, artifact_atk_pct: float,
                                            artifact_flat_atk: float, artifact_set_atk_pct: float,
                                            pyro_resonance_atk_pct: float, low_hp_for_homa: bool) -> NormalizedPrecombatAtk:
    """5聖遺物からrawと同じ段階を独立再構築する診断経路。"""
    homa_atk = max_hp_value * (HOMA_BASE_ATK_FROM_HP + (HOMA_LOW_HP_EXTRA_ATK_FROM_HP if low_hp_for_homa else 0.0))
    value = (base_atk * (1 + artifact_atk_pct + artifact_set_atk_pct + pyro_resonance_atk_pct)
             + artifact_flat_atk + homa_atk)
    return NormalizedPrecombatAtk(value, base_atk, "artifact_reconstructed")


def external_combat_atk_bonus(base_atk: float, millennial_movement_atk_pct: float,
                              amber_c6_atk_pct: float) -> ExternalCombatAtkBonus:
    value = base_atk * (millennial_movement_atk_pct + amber_c6_atk_pct)
    return ExternalCombatAtkBonus(value, millennial_movement_atk_pct, amber_c6_atk_pct)


def hutao_skill_atk_bonus(max_hp_value: float, base_atk: float, skill_hp_to_atk: float) -> HutaoSkillAtkBonus:
    uncapped = max_hp_value * skill_hp_to_atk
    cap = base_atk * E_ATK_CAP_BASE_ATK_MULTIPLIER
    return HutaoSkillAtkBonus(min(uncapped, cap), uncapped, cap)


def final_combat_atk(normalized: NormalizedPrecombatAtk, external: ExternalCombatAtkBonus,
                     skill: HutaoSkillAtkBonus) -> FinalCombatAtk:
    """意味を型で固定した3段階だけを合成する。"""
    return FinalCombatAtk(normalized, external, skill)


def crit_multiplier(crit_rate: float, crit_dmg: float) -> CalculationBreakdown:
    clamped_rate = min(max(crit_rate, 0.0), 1.0)
    value = 1 + clamped_rate * crit_dmg
    return _breakdown(value, crit_rate=crit_rate, clamped_crit_rate=clamped_rate,
                      crit_dmg=crit_dmg, crit_multiplier=value)


def vaporize_multiplier(elemental_mastery: float, reaction_bonus: float = 0.0,
                        base_multiplier: float = PYRO_VAPE_BASE_MULTIPLIER,
                        em_coefficient: float = EM_REACTION_COEFFICIENT,
                        em_denominator: float = EM_REACTION_DENOMINATOR) -> CalculationBreakdown:
    if elemental_mastery < 0:
        raise HutaoModelError("Elemental Masteryは0以上で指定してください")
    if base_multiplier < 0 or em_coefficient < 0 or em_denominator <= 0:
        raise HutaoModelError("Vaporize倍率とEM係数は0以上、EM分母は正で指定してください")
    em_bonus = em_coefficient * elemental_mastery / (em_denominator + elemental_mastery)
    value = base_multiplier * (1 + em_bonus + reaction_bonus)
    return _breakdown(value, elemental_mastery=elemental_mastery, base_multiplier=base_multiplier,
                      em_coefficient=em_coefficient, em_denominator=em_denominator,
                      em_bonus=em_bonus, reaction_bonus=reaction_bonus, vaporize_multiplier=value)


def damage_bonus(pyro_dmg_bonus: float, attack_type_bonus: float = 0.0,
                 a4_pyro_bonus: float = 0.0, kazuha_pyro_bonus: float = 0.0,
                 set_pyro_bonus: float = 0.0) -> CalculationBreakdown:
    total_bonus = pyro_dmg_bonus + attack_type_bonus + a4_pyro_bonus + kazuha_pyro_bonus + set_pyro_bonus
    return _breakdown(1 + total_bonus, pyro_dmg_bonus=pyro_dmg_bonus,
                      attack_type_bonus=attack_type_bonus, a4_pyro_bonus=a4_pyro_bonus,
                      kazuha_pyro_bonus=kazuha_pyro_bonus, set_pyro_bonus=set_pyro_bonus,
                      total_dmg_bonus=total_bonus, damage_bonus_multiplier=1 + total_bonus)


def enemy_def_multiplier(character_level: int, enemy_level: int,
                         def_reduction: float = 0.0, def_ignore: float = 0.0) -> CalculationBreakdown:
    reduction = min(def_reduction, 0.90)
    numerator = character_level + 100
    denominator = numerator + (enemy_level + 100) * (1 - reduction) * (1 - def_ignore)
    value = numerator / denominator
    return _breakdown(value, character_level=character_level, enemy_level=enemy_level,
                      def_reduction=reduction, def_ignore=def_ignore, def_multiplier=value)


def enemy_res_multiplier(base_resistance: float, resistance_reduction: float = 0.0) -> CalculationBreakdown:
    resistance = base_resistance - resistance_reduction
    if resistance < 0:
        value = 1 - resistance / 2
        branch = "negative"
    elif resistance < 0.75:
        value = 1 - resistance
        branch = "zero_to_75_percent"
    else:
        value = 1 / (4 * resistance + 1)
        branch = "75_percent_or_more"
    return _breakdown(value, base_resistance=base_resistance, resistance_reduction=resistance_reduction,
                      final_resistance=resistance, branch=branch, res_multiplier=value)


def _apply_rounding(value: float, mode: InternalRoundingMode) -> float:
    mode = InternalRoundingMode(mode)
    if mode is InternalRoundingMode.NONE:
        return value
    if mode is InternalRoundingMode.FLOOR_PER_HIT:
        return float(math.floor(value))
    return float(round(value))


def _single_hit_damage(total_atk_value: float, talent_multiplier: float, damage_bonus_multiplier: float,
                       crit_multiplier_value: float, def_multiplier: float, res_multiplier: float,
                       reaction_multiplier: float, rounding_mode: InternalRoundingMode,
                       component: str) -> CalculationBreakdown:
    unrounded = (total_atk_value * talent_multiplier * damage_bonus_multiplier * crit_multiplier_value
                 * def_multiplier * res_multiplier * reaction_multiplier)
    value = _apply_rounding(unrounded, rounding_mode)
    return _breakdown(value, component=component, total_atk=total_atk_value,
                      talent_multiplier=talent_multiplier, damage_bonus_multiplier=damage_bonus_multiplier,
                      crit_multiplier=crit_multiplier_value, def_multiplier=def_multiplier,
                      res_multiplier=res_multiplier, reaction_multiplier=reaction_multiplier,
                      unrounded=unrounded, rounding_mode=str(InternalRoundingMode(rounding_mode)))


def n1_non_vape_damage(total_atk_value: float, talent_multiplier: float, damage_bonus_multiplier: float,
                       crit_multiplier_value: float, def_multiplier: float, res_multiplier: float,
                       rounding_mode: InternalRoundingMode = InternalRoundingMode.NONE) -> CalculationBreakdown:
    return _single_hit_damage(total_atk_value, talent_multiplier, damage_bonus_multiplier,
                              crit_multiplier_value, def_multiplier, res_multiplier, 1.0,
                              rounding_mode, "NA Avg DMG")


def n1_vape_damage(total_atk_value: float, talent_multiplier: float, damage_bonus_multiplier: float,
                   crit_multiplier_value: float, def_multiplier: float, res_multiplier: float,
                   vaporize_multiplier_value: float,
                   rounding_mode: InternalRoundingMode = InternalRoundingMode.NONE) -> CalculationBreakdown:
    return _single_hit_damage(total_atk_value, talent_multiplier, damage_bonus_multiplier,
                              crit_multiplier_value, def_multiplier, res_multiplier,
                              vaporize_multiplier_value, rounding_mode, "NA Vape Avg DMG")


def ca_vape_damage(total_atk_value: float, talent_multiplier: float, damage_bonus_multiplier: float,
                   crit_multiplier_value: float, def_multiplier: float, res_multiplier: float,
                   vaporize_multiplier_value: float,
                   rounding_mode: InternalRoundingMode = InternalRoundingMode.NONE) -> CalculationBreakdown:
    return _single_hit_damage(total_atk_value, talent_multiplier, damage_bonus_multiplier,
                              crit_multiplier_value, def_multiplier, res_multiplier,
                              vaporize_multiplier_value, rounding_mode, "CA Vape Avg DMG")


def q_vape_damage(total_atk_value: float, talent_multiplier: float, damage_bonus_multiplier: float,
                  crit_multiplier_value: float, def_multiplier: float, res_multiplier: float,
                  vaporize_multiplier_value: float,
                  rounding_mode: InternalRoundingMode = InternalRoundingMode.NONE) -> CalculationBreakdown:
    return _single_hit_damage(total_atk_value, talent_multiplier, damage_bonus_multiplier,
                              crit_multiplier_value, def_multiplier, res_multiplier,
                              vaporize_multiplier_value, rounding_mode, "Q Vape Avg DMG")


def aggregate_akasha_result(components: ObservedComponents, shimenawa_4pc: bool,
                            config: ScenarioConfig | None = None) -> CalculationBreakdown:
    scenario = config or ScenarioConfig()
    q_quantity = scenario.burst_uptime_shimenawa if shimenawa_4pc else scenario.burst_uptime_non_shimenawa
    n1_vape_total = 4 * components.n1_vape
    n1_non_vape_total = 7 * components.n1_non_vape
    ca_vape_total = 11 * components.ca_vape
    q_vape_total = q_quantity * components.q_vape
    value = n1_vape_total + n1_non_vape_total + ca_vape_total + q_vape_total
    return _breakdown(value, n1_vape_quantity=4, n1_vape_total=n1_vape_total,
                      n1_non_vape_quantity=7, n1_non_vape_total=n1_non_vape_total,
                      ca_vape_quantity=11, ca_vape_total=ca_vape_total,
                      q_vape_quantity=q_quantity, q_vape_total=q_vape_total,
                      shimenawa_4pc=shimenawa_4pc)
