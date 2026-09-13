"""H6のraw炎Bonus、Kazuha A4、Freedom-Sworn、しめ縄を順番に診断する。"""

import csv
import json
import math
from dataclasses import replace
from pathlib import Path
from statistics import mean, median, pstdev

from .hutao_damage import CRIMSON_WITCH_2PC_PYRO_BONUS
from .hutao_engine import damage_bonus_inputs, predict_components
from .hutao_models import AkashaHutaoBuild, ScenarioConfig
from .hutao_raw import load_hutao_builds
from .hutao_validation import relative_error


PYRO_GOBLET_BONUS = 0.466
HUTAO_A4_PYRO_BONUS = 0.33
CRIMSON_WITCH_ONE_SKILL_STACK = 0.075
KAZUHA_A4_PER_EM = 0.0004
FREEDOM_SWORN_R1_NORMAL_CHARGED_BONUS = 0.16
SHIMENAWA_4PC_NORMAL_CHARGED_BONUS = 0.50
COMPONENTS = ("n1_non_vape", "n1_vape", "ca_vape", "q_vape", "aggregate")
KAZUHA_CANDIDATES = {"kazuha_raw_included_0": 0.0, "kazuha_1000_em_40": 1000.0,
                     "kazuha_1420_em_56_8": 1420.0}
FREEDOM_CANDIDATES = {"freedom_16": FREEDOM_SWORN_R1_NORMAL_CHARGED_BONUS, "freedom_0": 0.0}


def _raw_row(build: AkashaHutaoBuild) -> dict[str, object]:
    payload = json.loads(Path(build.raw_path).read_text(encoding="utf-8"))
    return next(row for row in payload["data"] if str(row.get("uid")) == build.uid and row.get("md5") == build.build_md5)


def artifact_pyro_bonus(build: AkashaHutaoBuild) -> tuple[float, float, float]:
    row = _raw_row(build)
    goblet_key = row.get("artifactObjects", {}).get("EQUIP_RING", {}).get("mainStatKey")
    goblet = PYRO_GOBLET_BONUS if goblet_key == "Pyro DMG Bonus" else 0.0
    crimson_static = CRIMSON_WITCH_2PC_PYRO_BONUS if build.set_count("Crimson Witch of Flames") >= 2 else 0.0
    other_artifact_pyro = 0.0
    return goblet, crimson_static, other_artifact_pyro


def raw_pyro_bonus_rows(builds: tuple[AkashaHutaoBuild, ...]) -> list[dict[str, object]]:
    rows = []
    for build in builds:
        goblet, crimson_static, other = artifact_pyro_bonus(build)
        artifact_only = goblet + crimson_static + other
        a4 = artifact_only + HUTAO_A4_PYRO_BONUS
        stack = CRIMSON_WITCH_ONE_SKILL_STACK if build.has_crimson_witch_4pc else 0.0
        candidates = {
            "a_artifact_only": artifact_only, "b_artifact_plus_hutao_a4": a4,
            "c_b_plus_crimson_stack": a4 + stack,
            "d_c_plus_kazuha_1420": a4 + stack + 1420 * KAZUHA_A4_PER_EM,
        }
        row = {
            "leaderboard_id": build.leaderboard_id, "rank": build.rank, "uid": build.uid,
            "build_md5": build.build_md5, "raw_stats_pyro_damage_bonus": build.pyro_dmg_bonus,
            "pyro_goblet_bonus": goblet, "crimson_witch_2pc_bonus": crimson_static,
            "other_artifact_pyro_bonus": other, "hutao_a4_bonus": HUTAO_A4_PYRO_BONUS,
            "crimson_witch_one_stack_bonus": stack, "kazuha_1420_em_bonus": 1420 * KAZUHA_A4_PER_EM,
            "has_crimson_witch_4pc": build.has_crimson_witch_4pc,
            "has_shimenawa_4pc": build.has_shimenawa_4pc,
        }
        for name, value in candidates.items():
            difference = value - build.pyro_dmg_bonus
            row[name] = value
            row[f"{name}_difference"] = difference
            row[f"{name}_absolute_difference"] = abs(difference)
        rows.append(row)
    for candidate in ("a_artifact_only", "b_artifact_plus_hutao_a4", "c_b_plus_crimson_stack",
                      "d_c_plus_kazuha_1420"):
        differences = [float(row[f"{candidate}_absolute_difference"]) for row in rows]
        for row in rows:
            row[f"{candidate}_mean_absolute_difference"] = mean(differences)
            row[f"{candidate}_maximum_absolute_difference"] = max(differences)
    return rows


def _observed(build: AkashaHutaoBuild) -> dict[str, float]:
    return {
        "n1_non_vape": build.observed.n1_non_vape, "n1_vape": build.observed.n1_vape,
        "ca_vape": build.observed.ca_vape, "q_vape": build.observed.q_vape,
        "aggregate": build.observed_result,
    }


def _predicted(build: AkashaHutaoBuild, config: ScenarioConfig) -> dict[str, float]:
    predicted = predict_components(build, config)
    return {
        "n1_non_vape": predicted.n1_non_vape.value, "n1_vape": predicted.n1_vape.value,
        "ca_vape": predicted.ca_vape.value, "q_vape": predicted.q_vape.value,
        "aggregate": predicted.aggregate.value,
    }


def _pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = mean(xs), mean(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    denominator = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return numerator / denominator if denominator else float("nan")


def _candidate_build_rows(builds: tuple[AkashaHutaoBuild, ...], configs: dict[str, ScenarioConfig],
                          stage: str) -> list[dict[str, object]]:
    rows = []
    for candidate_id, config in configs.items():
        group = []
        for build in builds:
            observed, predicted = _observed(build), _predicted(build, config)
            common, attack_type = damage_bonus_inputs(build, config)
            row = {
                "stage": stage, "candidate_id": candidate_id, "leaderboard_id": build.leaderboard_id,
                "rank": build.rank, "uid": build.uid, "build_md5": build.build_md5,
                "kazuha_em_for_a4": config.kazuha_em_for_a4,
                "kazuha_a4_bonus": common.kazuha_a4_bonus,
                "freedom_sworn_bonus": attack_type.freedom_sworn_bonus,
                "shimenawa_bonus": attack_type.shimenawa_bonus,
                "raw_pyro_bonus": common.raw_pyro_bonus, "hutao_a4_bonus": common.hutao_a4_bonus,
                "crimson_witch_stack_bonus": common.crimson_witch_stack_bonus,
                "common_pyro_bonus": common.total, "n1_ca_attack_type_bonus": attack_type.total,
                "has_shimenawa_4pc": build.has_shimenawa_4pc, "max_hp": build.max_hp,
            }
            for component in COMPONENTS:
                row[f"observed_{component}"] = observed[component]
                row[f"predicted_{component}"] = predicted[component]
                row[f"{component}_relative_error"] = relative_error(observed[component], predicted[component])
                row[f"{component}_predicted_to_observed_ratio"] = predicted[component] / observed[component]
            component_ratios = [float(row[f"{name}_predicted_to_observed_ratio"]) for name in COMPONENTS[:-1]]
            n1_ratio = mean([float(row["n1_non_vape_predicted_to_observed_ratio"]),
                             float(row["n1_vape_predicted_to_observed_ratio"])])
            ca_ratio = float(row["ca_vape_predicted_to_observed_ratio"])
            q_ratio = float(row["q_vape_predicted_to_observed_ratio"])
            row["n1_vs_q_ratio_gap"] = n1_ratio - q_ratio
            row["ca_vs_q_ratio_gap"] = ca_ratio - q_ratio
            row["n1_ca_vs_q_ratio_gap"] = mean([n1_ratio, ca_ratio]) - q_ratio
            row["within_build_component_spread"] = max(component_ratios) - min(component_ratios)
            row["within_build_component_relative_spread"] = max(component_ratios) / min(component_ratios) - 1
            group.append(row)
        for component in COMPONENTS:
            errors = [float(row[f"{component}_relative_error"]) for row in group]
            ratios = [float(row[f"{component}_predicted_to_observed_ratio"]) for row in group]
            for row in group:
                row[f"mean_{component}_relative_error"] = mean(errors)
                row[f"median_{component}_relative_error"] = median(errors)
                row[f"{component}_residual_std"] = pstdev(errors)
                row[f"maximum_absolute_{component}_relative_error"] = max(map(abs, errors))
                row[f"{component}_ratio_std"] = pstdev(ratios)
        aggregate_errors = [float(row["aggregate_relative_error"]) for row in group]
        for row in group:
            row["aggregate_residual_vs_max_hp_pearson"] = _pearson(
                [float(item["max_hp"]) for item in group], aggregate_errors)
            row["mean_n1_relative_error"] = mean([float(row["mean_n1_non_vape_relative_error"]),
                                                   float(row["mean_n1_vape_relative_error"])])
            row["mean_n1_vs_q_ratio_gap"] = mean(float(item["n1_vs_q_ratio_gap"]) for item in group)
            row["mean_ca_vs_q_ratio_gap"] = mean(float(item["ca_vs_q_ratio_gap"]) for item in group)
            row["mean_n1_ca_vs_q_ratio_gap"] = mean(float(item["n1_ca_vs_q_ratio_gap"]) for item in group)
            row["mean_within_build_component_spread"] = mean(
                float(item["within_build_component_spread"]) for item in group)
            row["mean_within_build_component_relative_spread"] = mean(
                float(item["within_build_component_relative_spread"]) for item in group)
        rows.extend(group)
    return rows


def kazuha_candidate_rows(builds: tuple[AkashaHutaoBuild, ...], base_config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    baseline = base_config or ScenarioConfig()
    configs = {name: replace(baseline, kazuha_em_for_a4=em) for name, em in KAZUHA_CANDIDATES.items()}
    return _candidate_build_rows(builds, configs, "kazuha")


def freedom_candidate_rows(builds: tuple[AkashaHutaoBuild, ...], kazuha_em: float = 1420.0,
                           base_config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    baseline = replace(base_config or ScenarioConfig(), kazuha_em_for_a4=kazuha_em)
    configs = {name: replace(baseline, freedom_sworn_normal_charged_bonus=bonus)
               for name, bonus in FREEDOM_CANDIDATES.items()}
    rows = _candidate_build_rows(builds, configs, "freedom_sworn")
    shimenawa = tuple(build for build in builds if build.has_shimenawa_4pc)
    if shimenawa:
        shimenawa_configs = {
            "shimenawa_50": replace(baseline, freedom_sworn_normal_charged_bonus=FREEDOM_SWORN_R1_NORMAL_CHARGED_BONUS,
                                     apply_shimenawa_damage_bonus=True),
            "shimenawa_0": replace(baseline, freedom_sworn_normal_charged_bonus=FREEDOM_SWORN_R1_NORMAL_CHARGED_BONUS,
                                    apply_shimenawa_damage_bonus=False),
        }
        rows.extend(_candidate_build_rows(shimenawa, shimenawa_configs, "shimenawa_single_build"))
    return rows


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def _summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    summaries = []
    for stage, candidate_id in dict.fromkeys((str(row["stage"]), str(row["candidate_id"])) for row in rows):
        group = [row for row in rows if row["stage"] == stage and row["candidate_id"] == candidate_id]
        first = group[0]
        summaries.append({
            "stage": stage, "candidate_id": candidate_id, "build_count": len(group),
            "kazuha_a4_bonus": first["kazuha_a4_bonus"], "freedom_sworn_bonus": first["freedom_sworn_bonus"],
            "shimenawa_bonus": first["shimenawa_bonus"],
            "mean_n1_non_vape_error": first["mean_n1_non_vape_relative_error"],
            "mean_n1_vape_error": first["mean_n1_vape_relative_error"],
            "mean_ca_error": first["mean_ca_vape_relative_error"], "mean_q_error": first["mean_q_vape_relative_error"],
            "mean_aggregate_error": first["mean_aggregate_relative_error"],
            "aggregate_residual_std": first["aggregate_residual_std"],
            "n1_ca_vs_q_ratio_gap": first["mean_n1_ca_vs_q_ratio_gap"],
            "component_spread": first["mean_within_build_component_spread"],
            "component_relative_spread": first["mean_within_build_component_relative_spread"],
            "max_hp_correlation": first["aggregate_residual_vs_max_hp_pearson"],
        })
    return summaries


def run_h6_validation(raw_root: str | Path = "data/akasha/raw",
                      output_root: str | Path = "data/akasha") -> dict[str, object]:
    builds = load_hutao_builds(raw_root)
    raw_rows = raw_pyro_bonus_rows(builds)
    kazuha_rows = kazuha_candidate_rows(builds)
    freedom_rows = freedom_candidate_rows(builds)
    output = Path(output_root)
    _write_csv(raw_rows, output / "h6_raw_pyro_bonus.csv")
    _write_csv(kazuha_rows, output / "h6_kazuha_candidates.csv")
    _write_csv(freedom_rows, output / "h6_freedom_sworn_candidates.csv")
    raw_summary = {}
    for candidate in ("a_artifact_only", "b_artifact_plus_hutao_a4", "c_b_plus_crimson_stack",
                      "d_c_plus_kazuha_1420"):
        raw_summary[candidate] = {
            "mean_absolute_difference": raw_rows[0][f"{candidate}_mean_absolute_difference"],
            "maximum_absolute_difference": raw_rows[0][f"{candidate}_maximum_absolute_difference"],
        }
    return {"build_count": len(builds), "raw_summary": raw_summary,
            "kazuha_summary": _summary(kazuha_rows), "freedom_and_shimenawa_summary": _summary(freedom_rows)}
