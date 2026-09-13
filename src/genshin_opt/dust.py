"""聖啓の塵の再構築分布と評価指標。UIやoptimizerには依存しない。"""

import math
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import IntEnum, StrEnum
from math import comb

from .models import Artifact, Stat, Substat
from .validation import validate_for_reshape


class DustError(ValueError):
    """再構築条件または確率モデルのエラー。"""


class GuaranteeTier(IntEnum):
    NORMAL = 2
    ADVANCED = 3
    ABSOLUTE = 4


class AllocationModel(StrEnum):
    """実ゲームで公式確認されていない強化先確率モデルの識別子。"""

    GO_CAPPED_BINOMIAL = "go_capped_binomial"


@dataclass(frozen=True)
class WeightedRoll:
    value: float
    probability: float


@dataclass(frozen=True)
class StatRollDistribution:
    stat: Stat
    rolls: tuple[WeightedRoll, ...]


@dataclass(frozen=True)
class ReshapeConditions:
    selected_stats: tuple[Stat, Stat]
    guarantee_tier: GuaranteeTier
    roll_distributions: tuple[StatRollDistribution, ...]
    allocation_model: AllocationModel = AllocationModel.GO_CAPPED_BINOMIAL
    roll_model_id: str = "caller_supplied"


@dataclass(frozen=True)
class ReshapeOutcome:
    artifact: Artifact
    enhancement_counts: tuple[tuple[Stat, int], ...]
    probability: float

    def count_for(self, stat: Stat) -> int:
        return dict(self.enhancement_counts)[stat]


@dataclass(frozen=True)
class ReshapeDistribution:
    original: Artifact
    conditions: ReshapeConditions
    enhancement_rolls: int
    outcomes: tuple[ReshapeOutcome, ...]


@dataclass(frozen=True)
class UpdateMetrics:
    original_score: float
    update_probability: float
    expected_candidate_score: float
    expected_kept_score: float
    expected_improvement: float
    mean_improvement_when_updated: float | None


ArtifactEvaluator = Callable[[Artifact], float]


def enhancement_roll_count(artifact: Artifact) -> int:
    """初期3/4種類とレベルから、4種類へ配分済みの強化回数を返す。"""
    validate_for_reshape(artifact)
    assert artifact.initial_substat_count is not None
    return artifact.level // 4 - (4 - artifact.initial_substat_count)


def _validate_conditions(artifact: Artifact, conditions: ReshapeConditions, roll_count: int) -> dict[Stat, tuple[WeightedRoll, ...]]:
    artifact_stats = tuple(substat.stat for substat in artifact.substats)
    selected = conditions.selected_stats
    if len(set(selected)) != 2 or any(stat not in artifact_stats for stat in selected):
        raise DustError("優先ステータスは対象聖遺物の異なる2種類を指定してください")
    if not isinstance(conditions.guarantee_tier, GuaranteeTier):
        raise DustError("保証段階が不正です")
    if conditions.guarantee_tier > roll_count:
        raise DustError("保証回数が再配分可能な強化回数を超えています")
    if conditions.allocation_model != AllocationModel.GO_CAPPED_BINOMIAL:
        raise DustError("未対応の強化先確率モデルです")
    if not isinstance(conditions.roll_model_id, str) or not conditions.roll_model_id.strip():
        raise DustError("ロール値モデルIDは空でない文字列にしてください")

    distributions: dict[Stat, tuple[WeightedRoll, ...]] = {}
    for distribution in conditions.roll_distributions:
        if distribution.stat in distributions:
            raise DustError(f"ロール分布が重複しています: {distribution.stat.value}")
        if distribution.stat not in artifact_stats:
            raise DustError(f"対象外ステータスのロール分布です: {distribution.stat.value}")
        if not distribution.rolls:
            raise DustError(f"ロール分布が空です: {distribution.stat.value}")
        probability_sum = 0.0
        for roll in distribution.rolls:
            if type(roll.value) not in (int, float) or not math.isfinite(roll.value) or roll.value <= 0:
                raise DustError("ロール値は有限の正の数にしてください")
            if type(roll.probability) not in (int, float) or not math.isfinite(roll.probability) or roll.probability <= 0:
                raise DustError("ロール確率は有限の正の数にしてください")
            probability_sum += roll.probability
        if not math.isclose(probability_sum, 1.0, abs_tol=1e-12):
            raise DustError(f"ロール確率の合計は1にしてください: {distribution.stat.value}")
        distributions[distribution.stat] = distribution.rolls
    if set(distributions) != set(artifact_stats):
        missing = sorted(stat.value for stat in set(artifact_stats) - set(distributions))
        raise DustError(f"ロール分布がないステータスがあります: {', '.join(missing)}")
    return distributions


def _group_distribution(stats: tuple[Stat, Stat], count: int,
                        rolls: dict[Stat, tuple[WeightedRoll, ...]]) -> dict[tuple[int, int, float, float], float]:
    states = {(0, 0, 0.0, 0.0): 1.0}
    for _ in range(count):
        next_states: dict[tuple[int, int, float, float], float] = {}
        for state, state_probability in states.items():
            for stat_index, stat in enumerate(stats):
                for roll in rolls[stat]:
                    counts = (state[0] + (stat_index == 0), state[1] + (stat_index == 1))
                    deltas = (state[2] + (roll.value if stat_index == 0 else 0),
                              state[3] + (roll.value if stat_index == 1 else 0))
                    key = (counts[0], counts[1], round(deltas[0], 12), round(deltas[1], 12))
                    next_states[key] = next_states.get(key, 0.0) + state_probability * 0.5 * roll.probability
        states = next_states
    return states


def _selected_total_distribution(roll_count: int, guarantee: int) -> dict[int, float]:
    distribution: dict[int, float] = {}
    for selected_count in range(roll_count + 1):
        adjusted_count = max(selected_count, guarantee)
        probability = comb(roll_count, selected_count) / 2**roll_count
        distribution[adjusted_count] = distribution.get(adjusted_count, 0.0) + probability
    return distribution


def reshape_distribution(artifact: Artifact, conditions: ReshapeConditions) -> ReshapeDistribution:
    """初期値を固定し、指定モデルで1回再構築した結果分布を全列挙する。"""
    roll_count = enhancement_roll_count(artifact)
    rolls = _validate_conditions(artifact, conditions, roll_count)
    selected = conditions.selected_stats
    other = tuple(stat for stat in (sub.stat for sub in artifact.substats) if stat not in selected)
    if len(other) != 2:
        raise DustError("対象聖遺物には4種類のサブステータスが必要です")

    artifact_stats = tuple(sub.stat for sub in artifact.substats)
    initial_values = {sub.stat: sub.initial_value for sub in artifact.substats}
    combined: dict[tuple[tuple[int, ...], tuple[float, ...]], float] = {}
    for selected_count, count_probability in _selected_total_distribution(roll_count, int(conditions.guarantee_tier)).items():
        selected_states = _group_distribution(selected, selected_count, rolls)
        other_states = _group_distribution(other, roll_count - selected_count, rolls)
        for selected_state, selected_probability in selected_states.items():
            for other_state, other_probability in other_states.items():
                counts_by_stat = {selected[0]: selected_state[0], selected[1]: selected_state[1],
                                  other[0]: other_state[0], other[1]: other_state[1]}
                deltas_by_stat = {selected[0]: selected_state[2], selected[1]: selected_state[3],
                                  other[0]: other_state[2], other[1]: other_state[3]}
                counts = tuple(counts_by_stat[stat] for stat in artifact_stats)
                deltas = tuple(deltas_by_stat[stat] for stat in artifact_stats)
                key = (counts, deltas)
                probability = count_probability * selected_probability * other_probability
                combined[key] = combined.get(key, 0.0) + probability

    outcomes = []
    for (counts, deltas), probability in combined.items():
        substats = tuple(Substat(stat, round(float(initial_values[stat]) + delta, 12), float(initial_values[stat]))
                         for stat, delta in zip(artifact_stats, deltas))
        reshaped = replace(artifact, substats=substats)
        enhancement_counts = tuple(zip(artifact_stats, counts))
        outcomes.append(ReshapeOutcome(reshaped, enhancement_counts, probability))
    outcomes.sort(key=lambda outcome: tuple((stat.value, count) for stat, count in outcome.enhancement_counts))
    probability_sum = sum(outcome.probability for outcome in outcomes)
    if not math.isclose(probability_sum, 1.0, abs_tol=1e-10):
        raise DustError(f"結果確率の合計が1になりません: {probability_sum}")
    return ReshapeDistribution(artifact, conditions, roll_count, tuple(outcomes))


def calculate_update_metrics(distribution: ReshapeDistribution, evaluate: ArtifactEvaluator) -> UpdateMetrics:
    """元を保持できる前提で、更新確率と候補・保持後の期待値を計算する。"""
    if not distribution.outcomes:
        raise DustError("再構築結果分布が空です")
    if any(type(outcome.probability) not in (int, float) or not math.isfinite(outcome.probability)
           or outcome.probability <= 0 for outcome in distribution.outcomes):
        raise DustError("結果確率は有限の正の数にしてください")
    probability_sum = sum(outcome.probability for outcome in distribution.outcomes)
    if not math.isclose(probability_sum, 1.0, abs_tol=1e-10):
        raise DustError("結果確率の合計は1にしてください")
    original_score = evaluate(distribution.original)
    if type(original_score) not in (int, float) or not math.isfinite(original_score):
        raise DustError("評価関数は有限の数値を返す必要があります")

    update_probability = 0.0
    expected_candidate_score = 0.0
    expected_kept_score = 0.0
    expected_improvement = 0.0
    for outcome in distribution.outcomes:
        score = evaluate(outcome.artifact)
        if type(score) not in (int, float) or not math.isfinite(score):
            raise DustError("評価関数は有限の数値を返す必要があります")
        improvement = score - original_score
        expected_candidate_score += outcome.probability * score
        expected_kept_score += outcome.probability * max(original_score, score)
        expected_improvement += outcome.probability * max(0.0, improvement)
        if improvement > 0:
            update_probability += outcome.probability
    mean_updated = expected_improvement / update_probability if update_probability > 0 else None
    return UpdateMetrics(float(original_score), update_probability, expected_candidate_score,
                         expected_kept_score, expected_improvement, mean_updated)
