"""H5（外部ATK%）を、raw増分モデルと聖遺物再構築モデルで検証する。"""

import csv
import json
import math
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import mean, median

from .hutao_damage import E_ATK_CAP_BASE_ATK_MULTIPLIER, HOMA_BASE_ATK_FROM_HP, HOMA_LOW_HP_EXTRA_ATK_FROM_HP
from .hutao_engine import predict_components, predict_components_from_artifacts
from .hutao_models import AkashaHutaoBuild, ArtifactReconstructedAtkInput, ScenarioConfig
from .hutao_raw import load_hutao_builds
from .hutao_validation import relative_error


CHARACTER_BASE_ATK_DISPLAY = 106.0
WEAPON_BASE_ATK_DISPLAY = 608.0
PYRO_RESONANCE_ATK_PCT = 0.25
MILLENNIAL_MOVEMENT_ATK_PCT = 0.20
AMBER_C6_ATK_PCT = 0.15
SHIMENAWA_2PC_ATK_PCT = 0.18


@dataclass(frozen=True)
class ArtifactAtkBreakdown:
    artifact_atk_pct: float
    artifact_flat_atk: float
    source: str = "Akasha profile build card (2026-09-13、表示値は丸め済み)"


LOCAL_OBSERVATIONS_PATH = Path("data/akasha/local_artifact_observations.json")


def _load_artifact_atk_observations(path: Path = LOCAL_OBSERVATIONS_PATH) -> dict[str, ArtifactAtkBreakdown]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {uid: ArtifactAtkBreakdown(float(item["artifact_atk_pct"]), float(item["artifact_flat_atk"]),
                                      str(item.get("source", "local observation")))
            for uid, item in payload.get("artifact_atk_by_uid", {}).items()}


# 公開playerのUIDと手作業観測値はGit管理外のローカルファイルから読む。
ARTIFACT_ATK_BY_UID = _load_artifact_atk_observations()


MODEL_CONFIGS = {
    "A": (0.45, 0.00, "Pyro Resonance 25% + Millennial Movement 20%"),
    "B": (0.20, 0.00, "Millennial Movement 20% only"),
    "C": (0.25, 0.00, "Pyro Resonance 25% only"),
    "D": (0.00, 0.00, "external ATK 0%"),
    "E": (0.20, 0.15, "Millennial Movement 20% + Amber C6 15%"),
}


def artifact_set_atk_pct(build: AkashaHutaoBuild) -> float:
    return SHIMENAWA_2PC_ATK_PCT if build.set_count("Shimenawa's Reminiscence") >= 2 else 0.0


def reconstruct_atk_stages(build: AkashaHutaoBuild) -> dict[str, float]:
    artifact = ARTIFACT_ATK_BY_UID[build.uid or ""]
    set_atk_pct = artifact_set_atk_pct(build)
    homa_base = build.max_hp * HOMA_BASE_ATK_FROM_HP
    homa_low = build.max_hp * HOMA_LOW_HP_EXTRA_ATK_FROM_HP
    profile_normalized = build.base_atk * (1 + artifact.artifact_atk_pct + set_atk_pct) + artifact.artifact_flat_atk + homa_base
    raw_candidate = profile_normalized + homa_low + build.base_atk * PYRO_RESONANCE_ATK_PCT
    e_atk = min(build.max_hp * 0.0626, build.base_atk * E_ATK_CAP_BASE_ATK_MULTIPLIER)
    return {
        "character_base_atk_display": CHARACTER_BASE_ATK_DISPLAY,
        "weapon_base_atk_display": WEAPON_BASE_ATK_DISPLAY,
        "combined_base_atk_internal": build.base_atk,
        "artifact_atk_pct": artifact.artifact_atk_pct,
        "artifact_flat_atk": artifact.artifact_flat_atk,
        "artifact_set_atk_pct": set_atk_pct,
        "profile_atk_normalized_candidate": profile_normalized,
        "pyro_resonance_atk": build.base_atk * PYRO_RESONANCE_ATK_PCT,
        "millennial_movement_atk": build.base_atk * MILLENNIAL_MOVEMENT_ATK_PCT,
        "amber_c6_atk": build.base_atk * AMBER_C6_ATK_PCT,
        "homa_base_hp_atk": homa_base,
        "homa_low_hp_atk": homa_low,
        "homa_total_hp_atk": homa_base + homa_low,
        "hutao_e_atk": e_atk,
        "raw_atk_reconstructed": raw_candidate,
        "raw_atk_reconstruction_error": raw_candidate - build.sheet_atk,
    }


def _values(build: AkashaHutaoBuild, config: ScenarioConfig, independent: bool) -> dict[str, float]:
    artifact = ARTIFACT_ATK_BY_UID[build.uid or ""]
    artifact_input = ArtifactReconstructedAtkInput(
        artifact.artifact_atk_pct, artifact.artifact_flat_atk, artifact_set_atk_pct(build))
    predicted = (predict_components_from_artifacts(build, artifact_input, config)
                 if independent else predict_components(build, config))
    values = {
        "n1_non_vape": predicted.n1_non_vape.value, "n1_vape": predicted.n1_vape.value,
        "ca_vape": predicted.ca_vape.value, "q_vape": predicted.q_vape.value,
        "aggregate": predicted.aggregate.value,
    }
    current_atk = predicted.n1_non_vape.as_dict()["total_atk"]
    if not independent:
        # H5成果物は境界修正前の比較を保存する。旧経路で二重計上していたHoma低HP 1.0%を明示的に再現する。
        legacy_atk = current_atk + build.max_hp * HOMA_LOW_HP_EXTRA_ATK_FROM_HP
        return {name: value * legacy_atk / current_atk for name, value in values.items()}
    return values


def _observed(build: AkashaHutaoBuild) -> dict[str, float]:
    return {
        "n1_non_vape": build.observed.n1_non_vape, "n1_vape": build.observed.n1_vape,
        "ca_vape": build.observed.ca_vape, "q_vape": build.observed.q_vape,
        "aggregate": build.observed_result,
    }


def model_comparison_rows(builds: tuple[AkashaHutaoBuild, ...], base_config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    base = base_config or ScenarioConfig()
    rows = []
    for basis, independent in (("raw_increment", False), ("artifact_reconstructed", True)):
        for model, (external, amber, description) in MODEL_CONFIGS.items():
            config = replace(base, external_atk_pct=external, amber_c6_atk_pct=amber)
            errors = {name: [] for name in ("n1_non_vape", "n1_vape", "ca_vape", "q_vape", "aggregate")}
            for build in builds:
                predicted, observed = _values(build, config, independent), _observed(build)
                for component in errors:
                    errors[component].append(relative_error(observed[component], predicted[component]))
            for component, component_errors in errors.items():
                rows.append({
                    "basis": basis, "model": model, "description": description,
                    "external_atk_pct": external, "amber_c6_atk_pct": amber, "component": component,
                    "build_count": len(component_errors), "mean_relative_error": mean(component_errors),
                    "median_relative_error": median(component_errors),
                    "max_absolute_relative_error": max(abs(error) for error in component_errors),
                })
    return rows


def _pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = mean(xs), mean(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    denominator = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return numerator / denominator if denominator else float("nan")


def residual_rows(builds: tuple[AkashaHutaoBuild, ...], base_config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    config = replace(base_config or ScenarioConfig(), external_atk_pct=0.20, amber_c6_atk_pct=0.0)
    rows = []
    for build in builds:
        predicted, observed, stages = _values(build, config, False), _observed(build), reconstruct_atk_stages(build)
        row = {
            "leaderboard_id": build.leaderboard_id, "rank": build.rank, "uid": build.uid,
            "build_md5": build.build_md5, "hp": build.max_hp, "raw_stats_atk": build.sheet_atk,
            "artifact_atk_pct": stages["artifact_atk_pct"], "artifact_flat_atk": stages["artifact_flat_atk"],
            "artifact_set_atk_pct": stages["artifact_set_atk_pct"], "crit_rate": build.crit_rate,
            "crit_dmg": build.crit_dmg, "elemental_mastery": build.elemental_mastery,
            "pyro_dmg_bonus": build.pyro_dmg_bonus,
            "artifact_sets": json.dumps(dict(build.artifact_sets), ensure_ascii=False, sort_keys=True),
            **stages,
        }
        for component in predicted:
            row[f"observed_{component}"] = observed[component]
            row[f"predicted_{component}"] = predicted[component]
            row[f"{component}_relative_error"] = relative_error(observed[component], predicted[component])
            row[f"{component}_ratio"] = predicted[component] / observed[component]
        ratios = [row[f"{name}_ratio"] for name in ("n1_non_vape", "n1_vape", "ca_vape", "q_vape")]
        row["component_ratio_range"] = max(ratios) - min(ratios)
        rows.append(row)
    return rows


def residual_correlations(rows: list[dict[str, object]], error_field: str = "aggregate_relative_error") -> dict[str, float]:
    inputs = ("hp", "raw_stats_atk", "artifact_atk_pct", "artifact_flat_atk", "crit_rate", "crit_dmg",
              "elemental_mastery", "pyro_dmg_bonus")
    ys = [float(row[error_field]) for row in rows]
    return {name: _pearson([float(row[name]) for row in rows], ys) for name in inputs}


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_h5_validation(raw_root: str | Path = "data/akasha/raw", output_root: str | Path = "data/akasha") -> dict[str, object]:
    builds = load_hutao_builds(raw_root)
    missing = [build.uid for build in builds if build.uid not in ARTIFACT_ATK_BY_UID]
    if missing:
        raise ValueError(f"聖遺物ATK内訳がないbuildです: {missing}")
    output = Path(output_root)
    comparisons, residuals = model_comparison_rows(builds), residual_rows(builds)
    _write_csv(comparisons, output / "h5_model_comparison.csv")
    _write_csv(residuals, output / "h5_residuals.csv")
    return {
        "build_count": len(builds), "comparison_rows": len(comparisons),
        "raw_reconstruction_max_abs_error": max(abs(float(row["raw_atk_reconstruction_error"])) for row in residuals),
        "component_ratio_range_max": max(float(row["component_ratio_range"]) for row in residuals),
        "correlations": residual_correlations(residuals),
    }
