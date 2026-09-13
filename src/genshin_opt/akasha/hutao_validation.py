"""Akasha観測componentと胡桃物理モデルの比較・CSV出力。"""

import csv
import json
from dataclasses import asdict
from pathlib import Path

from .hutao_engine import debug_build, predict_components
from .hutao_models import AkashaHutaoBuild, BuildComparison, ScenarioConfig


CSV_FIELDS = (
    "leaderboard_id", "rank", "uid", "build_md5", "entry_id", "artifact_sets",
    "observed_n1_vape", "predicted_n1_vape", "n1_vape_relative_error",
    "observed_n1_non_vape", "predicted_n1_non_vape", "n1_non_vape_relative_error",
    "observed_ca_vape", "predicted_ca_vape", "ca_vape_relative_error",
    "observed_q_vape", "predicted_q_vape", "q_vape_relative_error",
    "observed_result", "predicted_result", "result_relative_error", "raw_path",
)


def relative_error(observed: float, predicted: float) -> float:
    if observed == 0:
        return 0.0 if predicted == 0 else float("inf")
    return (predicted - observed) / observed


def compare_build(build: AkashaHutaoBuild, config: ScenarioConfig | None = None) -> BuildComparison:
    return BuildComparison(build, predict_components(build, config))


def compare_builds(builds: tuple[AkashaHutaoBuild, ...],
                   config: ScenarioConfig | None = None) -> tuple[BuildComparison, ...]:
    return tuple(compare_build(build, config) for build in builds)


def comparison_row(comparison: BuildComparison) -> dict[str, object]:
    build = comparison.build
    observed = build.observed
    predicted = comparison.predicted
    return {
        "leaderboard_id": build.leaderboard_id, "rank": build.rank, "uid": build.uid or "",
        "build_md5": build.build_md5 or "", "entry_id": build.entry_id or "",
        "artifact_sets": json.dumps(dict(build.artifact_sets), ensure_ascii=False, sort_keys=True),
        "observed_n1_vape": observed.n1_vape, "predicted_n1_vape": predicted.n1_vape.value,
        "n1_vape_relative_error": relative_error(observed.n1_vape, predicted.n1_vape.value),
        "observed_n1_non_vape": observed.n1_non_vape,
        "predicted_n1_non_vape": predicted.n1_non_vape.value,
        "n1_non_vape_relative_error": relative_error(observed.n1_non_vape, predicted.n1_non_vape.value),
        "observed_ca_vape": observed.ca_vape, "predicted_ca_vape": predicted.ca_vape.value,
        "ca_vape_relative_error": relative_error(observed.ca_vape, predicted.ca_vape.value),
        "observed_q_vape": observed.q_vape, "predicted_q_vape": predicted.q_vape.value,
        "q_vape_relative_error": relative_error(observed.q_vape, predicted.q_vape.value),
        "observed_result": build.observed_result, "predicted_result": predicted.aggregate.value,
        "result_relative_error": relative_error(build.observed_result, predicted.aggregate.value),
        "raw_path": build.raw_path,
    }


def save_comparison_csv(comparisons: tuple[BuildComparison, ...], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(comparison_row(comparison) for comparison in comparisons)
    temporary.replace(output)
    return output


def largest_component_error(comparisons: tuple[BuildComparison, ...]) -> tuple[str, float]:
    maxima = {"n1_vape": 0.0, "n1_non_vape": 0.0, "ca_vape": 0.0, "q_vape": 0.0}
    for comparison in comparisons:
        row = comparison_row(comparison)
        for component in maxima:
            maxima[component] = max(maxima[component], abs(float(row[f"{component}_relative_error"])))
    return max(maxima.items(), key=lambda item: item[1])


def debug_comparison(comparison: BuildComparison, config: ScenarioConfig | None = None) -> dict[str, object]:
    result = debug_build(comparison.build, config)
    result["observed"] = asdict(comparison.build.observed)
    result["predicted"] = {
        "n1_vape": comparison.predicted.n1_vape.value,
        "n1_non_vape": comparison.predicted.n1_non_vape.value,
        "ca_vape": comparison.predicted.ca_vape.value,
        "q_vape": comparison.predicted.q_vape.value,
        "aggregate": comparison.predicted.aggregate.value,
    }
    return result
