"""再構築後の所持品を再最適化し、採用するか元を保持するか判断する。"""

import math
from dataclasses import dataclass
from enum import StrEnum

from .dust import ReshapeConditions, ReshapeDistribution, ReshapeOutcome, reshape_distribution
from .models import Artifact, Inventory
from .optimizer import BuildConstraint, BuildEvaluator, OptimizationResult, optimize


class ReshapeDecision(StrEnum):
    KEEP_ORIGINAL = "keep_original"
    APPLY_RESHAPE = "apply_reshape"


@dataclass(frozen=True)
class OptimizedOutcome:
    reshape_outcome: ReshapeOutcome
    reshaped_inventory_best: OptimizationResult
    decision: ReshapeDecision
    chosen_best: OptimizationResult


@dataclass(frozen=True)
class OptimizedReshapeAnalysis:
    original_best: OptimizationResult
    distribution: ReshapeDistribution
    outcomes: tuple[OptimizedOutcome, ...]
    optimal_set_update_probability: float
    expected_reshaped_inventory_score: float
    expected_chosen_score: float
    expected_improvement: float


def replace_inventory_artifact(inventory: Inventory, artifact_id: str, replacement: Artifact) -> Inventory:
    """同じID・部位・セットの再構築結果で所持品内の1件を置き換える。"""
    matches = tuple(artifact for artifact in inventory.artifacts if artifact.id == artifact_id)
    if len(matches) != 1:
        raise ValueError(f"置換対象の聖遺物IDが1件ではありません: {artifact_id}")
    original = matches[0]
    if replacement.id != original.id or replacement.slot != original.slot or replacement.set_name != original.set_name:
        raise ValueError("再構築結果のID・部位・セットは元の聖遺物と一致させてください")
    artifacts = tuple(replacement if artifact.id == artifact_id else artifact for artifact in inventory.artifacts)
    return Inventory(inventory.schema_version, artifacts)


def analyze_distribution(inventory: Inventory, distribution: ReshapeDistribution, evaluate: BuildEvaluator,
                         constraint: BuildConstraint | None = None) -> OptimizedReshapeAnalysis:
    """各結果で所持品を再最適化し、元の所持品と評価値を比較する。"""
    matching_originals = tuple(artifact for artifact in inventory.artifacts if artifact.id == distribution.original.id)
    if len(matching_originals) != 1 or matching_originals[0] != distribution.original:
        raise ValueError("再構築分布の元聖遺物が所持品と一致しません")
    if not distribution.outcomes:
        raise ValueError("再構築結果分布が空です")
    if any(type(outcome.probability) not in (int, float) or not math.isfinite(outcome.probability)
           or outcome.probability <= 0 for outcome in distribution.outcomes):
        raise ValueError("再構築結果の確率は有限の正の数にしてください")
    probability_sum = sum(outcome.probability for outcome in distribution.outcomes)
    if not math.isclose(probability_sum, 1.0, abs_tol=1e-10):
        raise ValueError("再構築結果の確率合計は1にしてください")
    original_best = optimize(inventory, evaluate, constraint)
    outcomes = []
    update_probability = 0.0
    expected_reshaped = 0.0
    expected_chosen = 0.0
    expected_improvement = 0.0
    for outcome in distribution.outcomes:
        reshaped_inventory = replace_inventory_artifact(inventory, distribution.original.id, outcome.artifact)
        reshaped_best = optimize(reshaped_inventory, evaluate, constraint)
        improved = reshaped_best.score > original_best.score
        decision = ReshapeDecision.APPLY_RESHAPE if improved else ReshapeDecision.KEEP_ORIGINAL
        chosen_best = reshaped_best if improved else original_best
        outcomes.append(OptimizedOutcome(outcome, reshaped_best, decision, chosen_best))
        expected_reshaped += outcome.probability * reshaped_best.score
        expected_chosen += outcome.probability * chosen_best.score
        expected_improvement += outcome.probability * max(0.0, reshaped_best.score - original_best.score)
        if improved:
            update_probability += outcome.probability
    return OptimizedReshapeAnalysis(original_best, distribution, tuple(outcomes), update_probability,
                                    expected_reshaped, expected_chosen, expected_improvement)


def analyze_reshape(inventory: Inventory, target: Artifact, conditions: ReshapeConditions,
                    evaluate: BuildEvaluator, constraint: BuildConstraint | None = None) -> OptimizedReshapeAnalysis:
    """1件の再構築分布を作り、各結果で最適セットを更新できるか判断する。"""
    distribution = reshape_distribution(target, conditions)
    return analyze_distribution(inventory, distribution, evaluate, constraint)
