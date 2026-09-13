"""評価式を知らずに5部位の全組み合わせを調べる小規模optimizer。"""

import math
from collections.abc import Callable
from dataclasses import dataclass
from itertools import product

from .models import Artifact, Inventory, Slot
from .validation import validate_inventory

Build = tuple[Artifact, ...]
BuildEvaluator = Callable[[Build], float]
BuildConstraint = Callable[[Build], bool]


class OptimizationError(ValueError):
    """最適化を実行できない入力または評価値を表す。"""


@dataclass(frozen=True)
class OptimizationResult:
    artifacts: Build
    score: float
    combinations_evaluated: int

    def artifact_for(self, slot: Slot) -> Artifact:
        """結果から指定部位を取得する。"""
        return self.artifacts[list(Slot).index(slot)]


def at_least_set_pieces(set_name: str, minimum: int = 4) -> BuildConstraint:
    """指定セットがminimum部位以上ある組み合わせだけを許可する制約を返す。"""
    if not isinstance(set_name, str) or not set_name.strip() or set_name != set_name.strip():
        raise OptimizationError("セット名は前後に空白のない文字列にしてください")
    if type(minimum) is not int or not 0 <= minimum <= len(Slot):
        raise OptimizationError("必要セット数は0〜5の整数にしてください")
    return lambda build: sum(artifact.set_name == set_name for artifact in build) >= minimum


def optimize(inventory: Inventory, evaluate: BuildEvaluator,
             constraint: BuildConstraint | None = None) -> OptimizationResult:
    """各部位から1個ずつ選ぶ全組み合わせを評価し、最大値を返す。"""
    validate_inventory(inventory)
    candidates = {slot: tuple(a for a in inventory.artifacts if a.slot == slot) for slot in Slot}
    missing_slots = [slot.value for slot, artifacts in candidates.items() if not artifacts]
    if missing_slots:
        raise OptimizationError(f"候補がない部位があります: {', '.join(missing_slots)}")

    best_build: Build | None = None
    best_score = -math.inf
    combinations_evaluated = 0
    for build in product(*(candidates[slot] for slot in Slot)):
        if constraint is not None and not constraint(build):
            continue
        score = evaluate(build)
        if type(score) not in (int, float) or not math.isfinite(score):
            raise OptimizationError("評価関数は有限の数値を返す必要があります")
        combinations_evaluated += 1
        if best_build is None or score > best_score:
            best_build = build
            best_score = float(score)

    if best_build is None:
        raise OptimizationError("制約を満たす組み合わせがありません")
    return OptimizationResult(best_build, best_score, combinations_evaluated)
