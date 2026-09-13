"""Akasha胡桃単発Damage検証の入力・設定・出力データ型。"""

from dataclasses import dataclass
from enum import StrEnum
import math


class HutaoModelError(ValueError):
    """入力または仮説設定が計算不能な場合の例外。"""


class InternalRoundingMode(StrEnum):
    NONE = "none"
    FLOOR_PER_HIT = "floor_per_hit"
    ROUND_PER_HIT = "round_per_hit"


@dataclass(frozen=True)
class TalentMultipliers:
    n1: float
    charged: float
    skill_hp_to_atk: float
    burst_normal_hp: float
    burst_low_hp: float


@dataclass(frozen=True)
class ScenarioConfig:
    """docs/akasha_hutao_spec.mdのH1〜H8を切り替える設定。"""

    character_level: int = 90
    enemy_level: int = 90
    low_hp_for_a4: bool = True
    low_hp_for_homa: bool = True
    low_hp_for_burst: bool = True
    enemy_base_pyro_res: float = 0.10
    vv_res_reduction: float = 0.40
    hutao_external_em: float = 420.0
    vaporize_base_multiplier: float = 1.5
    vaporize_em_coefficient: float = 2.78
    vaporize_em_denominator: float = 1400.0
    crimson_witch_vape_bonus: float = 0.15
    apply_crimson_witch_vape_bonus: bool = True
    kazuha_em_for_a4: float = 1420.0
    # raw stats.atkに未包含の戦闘中ATK%。baselineはMillennial Movement 20%。
    external_atk_pct: float = 0.20
    amber_c6_atk_pct: float = 0.0
    freedom_sworn_normal_charged_bonus: float = 0.16
    internal_rounding_mode: InternalRoundingMode = InternalRoundingMode.NONE
    normal_attack_talent_level: int = 10
    skill_talent_level: int = 10
    burst_talent_level: int = 10
    talent_multiplier_override: TalentMultipliers | None = None
    raw_max_hp_includes_homa_hp: bool = True
    apply_crimson_witch_skill_stack: bool = True
    apply_shimenawa_damage_bonus: bool = True
    burst_uptime_non_shimenawa: float = 2 / 3
    burst_uptime_shimenawa: float = 1 / 3

    def __post_init__(self) -> None:
        integer_fields = (self.character_level, self.enemy_level, self.normal_attack_talent_level,
                          self.skill_talent_level, self.burst_talent_level)
        if any(type(value) is not int or value <= 0 for value in integer_fields):
            raise HutaoModelError("levelとtalent levelは正の整数で指定してください")
        numeric_fields = (
            self.enemy_base_pyro_res, self.vv_res_reduction, self.hutao_external_em,
            self.vaporize_base_multiplier, self.vaporize_em_coefficient,
            self.vaporize_em_denominator, self.crimson_witch_vape_bonus,
            self.kazuha_em_for_a4, self.external_atk_pct, self.amber_c6_atk_pct,
            self.freedom_sworn_normal_charged_bonus, self.burst_uptime_non_shimenawa,
            self.burst_uptime_shimenawa,
        )
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in numeric_fields):
            raise HutaoModelError("ScenarioConfigの数値は有限値で指定してください")
        if self.hutao_external_em < 0 or self.kazuha_em_for_a4 < 0:
            raise HutaoModelError("EMは0以上で指定してください")
        if self.vaporize_base_multiplier < 0 or self.vaporize_em_coefficient < 0 or self.vaporize_em_denominator <= 0:
            raise HutaoModelError("Vaporize倍率とEM係数は0以上、EM分母は正で指定してください")
        if self.burst_uptime_non_shimenawa < 0 or self.burst_uptime_shimenawa < 0:
            raise HutaoModelError("burst uptimeは0以上で指定してください")
        try:
            InternalRoundingMode(self.internal_rounding_mode)
        except ValueError as error:
            raise HutaoModelError("internal_rounding_modeが未対応です") from error


@dataclass(frozen=True)
class CalculationBreakdown:
    value: float
    details: tuple[tuple[str, object], ...]

    def as_dict(self) -> dict[str, object]:
        return {key: value for key, value in self.details}


@dataclass(frozen=True)
class NormalizedPrecombatAtk:
    """Akasha Leaderboardのraw stats.atkと同じ段階のATK。"""

    value: float
    base_atk: float
    source: str


@dataclass(frozen=True)
class ExternalCombatAtkBonus:
    """normalized precombat ATKへまだ入っていない外部ATK加算。"""

    value: float
    millennial_movement_atk_pct: float
    amber_c6_atk_pct: float


@dataclass(frozen=True)
class HutaoSkillAtkBonus:
    """胡桃EによるMaxHP依存ATK加算。"""

    value: float
    uncapped_value: float
    cap: float


@dataclass(frozen=True)
class CommonPyroDamageBonus:
    """N1/CA/Qへ共通する炎元素Damage Bonusの入力境界。"""

    raw_pyro_bonus: float
    hutao_a4_bonus: float
    kazuha_a4_bonus: float
    crimson_witch_stack_bonus: float

    @property
    def total(self) -> float:
        return self.raw_pyro_bonus + self.hutao_a4_bonus + self.kazuha_a4_bonus + self.crimson_witch_stack_bonus


@dataclass(frozen=True)
class AttackTypeDamageBonus:
    """通常・重撃だけへ加えるDamage Bonus。Qへ流用しない。"""

    freedom_sworn_bonus: float = 0.0
    shimenawa_bonus: float = 0.0

    @property
    def total(self) -> float:
        return self.freedom_sworn_bonus + self.shimenawa_bonus


@dataclass(frozen=True)
class ArtifactReconstructedAtkInput:
    """rawを使わずnormalized precombat ATKを組み立てる診断入力。"""

    artifact_atk_pct: float
    artifact_flat_atk: float
    artifact_set_atk_pct: float
    pyro_resonance_atk_pct: float = 0.25


@dataclass(frozen=True)
class FinalCombatAtk:
    normalized_precombat: NormalizedPrecombatAtk
    external_combat: ExternalCombatAtkBonus
    hutao_skill: HutaoSkillAtkBonus

    @property
    def value(self) -> float:
        return self.normalized_precombat.value + self.external_combat.value + self.hutao_skill.value


@dataclass(frozen=True)
class ObservedComponents:
    n1_vape: float
    n1_non_vape: float
    ca_vape: float
    q_vape: float


@dataclass(frozen=True)
class HutaoAkashaInput:
    """観測値を含まない、Hu Tao Akasha評価エンジンの正規化入力。"""

    input_source: str
    max_hp: float
    sheet_atk: float
    base_atk: float
    crit_rate: float
    crit_dmg: float
    elemental_mastery: float
    pyro_dmg_bonus: float
    artifact_sets: tuple[tuple[str, int], ...]

    def set_count(self, set_name: str) -> int:
        return next((count for name, count in self.artifact_sets if name == set_name), 0)

    @property
    def has_crimson_witch_4pc(self) -> bool:
        return self.set_count("Crimson Witch of Flames") >= 4

    @property
    def has_shimenawa_4pc(self) -> bool:
        return self.set_count("Shimenawa's Reminiscence") >= 4


@dataclass(frozen=True)
class AkashaHutaoBuild(HutaoAkashaInput):
    """保存済みLeaderboardの正規化入力と観測値。"""

    leaderboard_id: str
    rank: int
    uid: str | None
    build_md5: str | None
    entry_id: str | None
    raw_path: str
    observed: ObservedComponents
    observed_result: float


class HypothesisStatus(StrEnum):
    CONFIRMED = "confirmed"
    STRONGLY_SUPPORTED = "strongly_supported"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class HypothesisState:
    hypothesis_id: str
    status: HypothesisStatus
    summary: str


@dataclass(frozen=True)
class AkashaScoreResult:
    """optimizerとUIへ公開するHu Tao Akasha推定結果。"""

    n1_non_vape_avg: float
    n1_vape_avg: float
    ca_vape_avg: float
    q_vape_avg: float
    aggregate_score: float
    debug_breakdown: dict[str, object]
    hypothesis_states: tuple[HypothesisState, ...]
    is_estimate: bool = True


@dataclass(frozen=True)
class PredictedComponents:
    n1_vape: CalculationBreakdown
    n1_non_vape: CalculationBreakdown
    ca_vape: CalculationBreakdown
    q_vape: CalculationBreakdown
    aggregate: CalculationBreakdown


@dataclass(frozen=True)
class BuildComparison:
    build: AkashaHutaoBuild
    predicted: PredictedComponents
