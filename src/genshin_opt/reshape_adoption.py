"""元Artifactと再構築後Artifactを別inventoryで再最適化して比較する。"""

from dataclasses import dataclass
from enum import StrEnum

from .models import Artifact, Inventory
from .optimizer import BuildConstraint, BuildEvaluator, OptimizationResult, optimize
from .validation import validate_artifact, validate_inventory


DEFAULT_ADOPTION_UNCERTAINTY_THRESHOLD = 0.005


class AdoptionVerdict(StrEnum):
    RECONSTRUCTED_BETTER = "reconstructed_better"
    ORIGINAL_BETTER = "original_better"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class ArtifactCaseResult:
    inventory: Inventory
    best: OptimizationResult
    target_used: bool


@dataclass(frozen=True)
class ArtifactAdoptionComparison:
    original: ArtifactCaseResult
    reconstructed: ArtifactCaseResult
    damage_difference: float
    improvement_percent: float
    verdict: AdoptionVerdict
    uncertainty_threshold: float


def inventory_with_artifact_case(inventory: Inventory, target_id: str, artifact: Artifact) -> Inventory:
    """選択された1件を置換し、同一IDを重複追加しないcase inventoryを作る。"""
    validate_artifact(artifact, "replacement")
    matches = [index for index, item in enumerate(inventory.artifacts) if item.id == target_id]
    if len(matches) != 1:
        raise ValueError(f"置換対象の聖遺物IDが1件ではありません: {target_id}")
    if artifact.id != target_id:
        raise ValueError("置換ArtifactのIDは選択された対象IDと一致させてください")
    artifacts = tuple(artifact if index == matches[0] else item for index, item in enumerate(inventory.artifacts))
    case_inventory = Inventory(inventory.schema_version, artifacts)
    validate_inventory(case_inventory)
    return case_inventory


def compare_artifact_adoption(inventory: Inventory, target_id: str, original: Artifact,
                                reconstructed: Artifact, evaluate: BuildEvaluator,
                                constraint: BuildConstraint | None = None,
                                uncertainty_threshold: float = DEFAULT_ADOPTION_UNCERTAINTY_THRESHOLD) -> ArtifactAdoptionComparison:
    """元へ戻す世界と再構築後を採用する世界を、同じ評価関数で独立に最適化する。"""
    if type(uncertainty_threshold) not in (int, float) or uncertainty_threshold < 0:
        raise ValueError("不確実判定の閾値は0以上にしてください")
    if original.slot != reconstructed.slot or original.set_name != reconstructed.set_name:
        raise ValueError("再構築前後のslotとset_nameは一致させてください")
    if original.main_stat != reconstructed.main_stat:
        raise ValueError("再構築前後のmain statは一致させてください")
    original_inventory = inventory_with_artifact_case(inventory, target_id, original)
    reconstructed_inventory = inventory_with_artifact_case(inventory, target_id, reconstructed)
    original_best = optimize(original_inventory, evaluate, constraint)
    reconstructed_best = optimize(reconstructed_inventory, evaluate, constraint)
    difference = reconstructed_best.score - original_best.score
    improvement = difference / original_best.score if original_best.score else 0.0
    if improvement > uncertainty_threshold:
        verdict = AdoptionVerdict.RECONSTRUCTED_BETTER
    elif improvement < -uncertainty_threshold:
        verdict = AdoptionVerdict.ORIGINAL_BETTER
    else:
        verdict = AdoptionVerdict.UNCERTAIN
    original_case = ArtifactCaseResult(original_inventory, original_best,
                                       any(item.id == target_id for item in original_best.artifacts))
    reconstructed_case = ArtifactCaseResult(reconstructed_inventory, reconstructed_best,
                                            any(item.id == target_id for item in reconstructed_best.artifacts))
    return ArtifactAdoptionComparison(original_case, reconstructed_case, difference, improvement * 100,
                                      verdict, uncertainty_threshold)
