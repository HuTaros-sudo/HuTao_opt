"""H1のMax HP境界と胡桃E変換だけを比較する診断。"""

import csv
import json
import math
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import mean, pstdev, pvariance

from .hutao_damage import DISPLAYED_LEVEL_10_TALENTS, E_ATK_CAP_BASE_ATK_MULTIPLIER
from .hutao_engine import predict_components
from .hutao_models import AkashaHutaoBuild, ScenarioConfig, TalentMultipliers
from .hutao_raw import load_hutao_builds
from .hutao_validation import relative_error


# 表示丸め前の基礎値。Lv90/95/100は検証資料の同一表から取得し、Damage engineの固定仕様とは分離する。
HUTAO_BASE_HP_BY_LEVEL = {90: 15552.31, 95: 16104.39, 100: 16657.69}
HOMA_R1_HP_PCT = 0.20
E_SKILL_RATIOS = {9: 0.0596, 10: 0.0626, 11: 0.0656, 13: 0.0715}
SLOTS = ("flower", "plume", "sands", "goblet", "circlet")


@dataclass(frozen=True)
class ArtifactHpValue:
    hp_pct: float = 0.0
    flat_hp: float = 0.0


def _hp(*values: tuple[float, float]) -> tuple[ArtifactHpValue, ...]:
    return tuple(ArtifactHpValue(hp_pct, flat_hp) for hp_pct, flat_hp in values)


LOCAL_OBSERVATIONS_PATH = Path("data/akasha/local_artifact_observations.json")


def _load_artifact_hp_observations(path: Path = LOCAL_OBSERVATIONS_PATH) -> dict[str, tuple[ArtifactHpValue, ...]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {uid: tuple(ArtifactHpValue(float(item["hp_pct"]), float(item["flat_hp"])) for item in values)
            for uid, values in payload.get("artifact_hp_by_uid", {}).items()}


# 公開playerのUIDと手作業観測値はGit管理外のローカルファイルから読む。
ARTIFACT_HP_BY_UID = _load_artifact_hp_observations()


def reconstruct_max_hp(base_hp: float, artifact_hp_pct: float, artifact_flat_hp: float,
                       homa_hp_pct: float) -> float:
    return base_hp * (1 + artifact_hp_pct + homa_hp_pct) + artifact_flat_hp


def _raw_metadata(build: AkashaHutaoBuild) -> dict[str, object]:
    payload = json.loads(Path(build.raw_path).read_text(encoding="utf-8"))
    row = next(row for row in payload["data"] if str(row.get("uid")) == build.uid and row.get("md5") == build.build_md5)
    skill = row["talentsLevelMap"]["elementalSkill"]
    return {
        "profile_level": int(row["propMap"]["level"]["val"]), "profile_constellation": int(row["constellation"]),
        "profile_skill_level": int(skill["level"]), "profile_skill_raw_level": int(skill["rawLevel"]),
        "profile_skill_boosted": bool(skill["boosted"]),
        "profile_weapon_refinement": int(row["weapon"]["weaponInfo"]["refinementLevel"]["value"]) + 1,
    }


def maxhp_reconstruction_rows(builds: tuple[AkashaHutaoBuild, ...]) -> list[dict[str, object]]:
    rows = []
    for build in builds:
        artifacts = ARTIFACT_HP_BY_UID[build.uid or ""]
        metadata = _raw_metadata(build)
        hp_pct = sum(item.hp_pct for item in artifacts)
        flat_hp = sum(item.flat_hp for item in artifacts)
        profile_level = int(metadata["profile_level"])
        candidates = {
            "a_lv90_artifacts_homa_r1": reconstruct_max_hp(HUTAO_BASE_HP_BY_LEVEL[90], hp_pct, flat_hp, HOMA_R1_HP_PCT),
            "b_lv90_artifacts_no_homa": reconstruct_max_hp(HUTAO_BASE_HP_BY_LEVEL[90], hp_pct, flat_hp, 0.0),
            "c_lv100_artifacts_homa_r1": reconstruct_max_hp(HUTAO_BASE_HP_BY_LEVEL[100], hp_pct, flat_hp, HOMA_R1_HP_PCT),
            "d_profile_level_artifacts_homa_r1": reconstruct_max_hp(HUTAO_BASE_HP_BY_LEVEL[profile_level], hp_pct, flat_hp, HOMA_R1_HP_PCT),
        }
        # HP%は0.1 percentage point表示、flat HPは整数表示として、各表示項を±半単位で保守的に伝播する。
        hp_pct_terms = sum(item.hp_pct != 0 for item in artifacts)
        flat_hp_terms = sum(item.flat_hp != 0 for item in artifacts)
        rounding_bound = HUTAO_BASE_HP_BY_LEVEL[90] * hp_pct_terms * 0.0005 + flat_hp_terms * 0.5
        row = {
            "leaderboard_id": build.leaderboard_id, "rank": build.rank, "uid": build.uid,
            "build_md5": build.build_md5, "raw_stats_max_hp": build.max_hp, **metadata,
            "artifact_hp_pct": hp_pct, "artifact_flat_hp": flat_hp,
            "artifact_hp_pct_display_terms": hp_pct_terms, "artifact_flat_hp_display_terms": flat_hp_terms,
            "lv90_display_rounding_error_bound": rounding_bound, "artifact_set_hp_pct": 0.0,
            "inferred_base_hp_assuming_homa_r1": (build.max_hp - flat_hp) / (1 + hp_pct + HOMA_R1_HP_PCT),
            "inferred_homa_hp_pct_assuming_lv90": (build.max_hp - flat_hp) / HUTAO_BASE_HP_BY_LEVEL[90] - 1 - hp_pct,
        }
        for slot, artifact in zip(SLOTS, artifacts, strict=True):
            row[f"{slot}_hp_pct"] = artifact.hp_pct
            row[f"{slot}_flat_hp"] = artifact.flat_hp
        for name, value in candidates.items():
            difference = value - build.max_hp
            row[name] = value
            row[f"{name}_absolute_difference"] = difference
            row[f"{name}_relative_difference"] = difference / build.max_hp
        rows.append(row)
    return rows


def _talents_with_skill_ratio(ratio: float) -> TalentMultipliers:
    baseline = DISPLAYED_LEVEL_10_TALENTS
    return TalentMultipliers(baseline.n1, baseline.charged, ratio, baseline.burst_normal_hp, baseline.burst_low_hp)


def _pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = mean(xs), mean(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    denominator = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return numerator / denominator if denominator else float("nan")


def _maxhp_candidates(row: dict[str, object]) -> dict[str, float]:
    return {name: float(row[name]) for name in (
        "raw_stats_max_hp", "a_lv90_artifacts_homa_r1", "b_lv90_artifacts_no_homa", "c_lv100_artifacts_homa_r1",
        "d_profile_level_artifacts_homa_r1")}


def e_bonus_comparison_rows(builds: tuple[AkashaHutaoBuild, ...], maxhp_rows: list[dict[str, object]],
                            base_config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    scenario = base_config or ScenarioConfig()
    maxhp_by_uid = {row["uid"]: row for row in maxhp_rows}
    rows = []
    for hp_model in _maxhp_candidates(maxhp_rows[0]):
        talent_models = [(f"fixed_{level}", level) for level in E_SKILL_RATIOS] + [("profile_actual_10_or_13", None)]
        for talent_model, fixed_level in talent_models:
            group = []
            for build in builds:
                maxhp_row = maxhp_by_uid[build.uid]
                talent_level = fixed_level or int(maxhp_row["profile_skill_level"])
                ratio = E_SKILL_RATIOS[talent_level]
                config = replace(scenario, skill_talent_level=talent_level,
                                 talent_multiplier_override=_talents_with_skill_ratio(ratio))
                hp = float(maxhp_row[hp_model])
                candidate_build = replace(build, max_hp=hp)
                predicted = predict_components(candidate_build, config).aggregate.value
                uncapped = hp * ratio
                cap = build.base_atk * E_ATK_CAP_BASE_ATK_MULTIPLIER
                group.append({
                    "leaderboard_id": build.leaderboard_id, "rank": build.rank, "uid": build.uid,
                    "build_md5": build.build_md5, "max_hp_model": hp_model, "skill_talent_model": talent_model,
                    "skill_talent_level": talent_level,
                    "skill_hp_to_atk_ratio": ratio, "max_hp": hp, "artifact_hp_pct": maxhp_row["artifact_hp_pct"],
                    "raw_stats_atk": build.sheet_atk, "uncapped_e_atk_bonus": uncapped, "e_atk_cap": cap,
                    "e_cap_reached": uncapped >= cap, "final_e_atk_bonus": min(uncapped, cap),
                    "observed_aggregate": build.observed_result, "predicted_aggregate": predicted,
                    "relative_error": relative_error(build.observed_result, predicted),
                    "observed_to_predicted_ratio": build.observed_result / predicted,
                    "profile_constellation": maxhp_row["profile_constellation"],
                    "profile_skill_level": maxhp_row["profile_skill_level"],
                    "profile_skill_raw_level": maxhp_row["profile_skill_raw_level"],
                })
            observed = [float(row["observed_aggregate"]) for row in group]
            predicted = [float(row["predicted_aggregate"]) for row in group]
            scale = sum(o * p for o, p in zip(observed, predicted, strict=True)) / sum(p * p for p in predicted)
            for row in group:
                row["diagnostic_least_squares_scale"] = scale
                scaled_error = (scale * float(row["predicted_aggregate"]) - float(row["observed_aggregate"])) / float(row["observed_aggregate"])
                row["scale_normalized_relative_error"] = scaled_error
            fields = ("max_hp", "final_e_atk_bonus", "raw_stats_atk", "artifact_hp_pct")
            errors = [float(row["relative_error"]) for row in group]
            scaled_errors = [float(row["scale_normalized_relative_error"]) for row in group]
            ratios = [float(row["observed_to_predicted_ratio"]) for row in group]
            for row in group:
                row["ratio_variance_across_builds"] = pvariance(ratios)
                row["ratio_std_across_builds"] = pstdev(ratios)
                row["relative_error_std_across_builds"] = pstdev(errors)
                row["scale_normalized_error_std_across_builds"] = pstdev(scaled_errors)
                for field in fields:
                    xs = [float(item[field]) for item in group]
                    row[f"residual_vs_{field}_pearson"] = _pearson(xs, errors)
                    row[f"scaled_residual_vs_{field}_pearson"] = _pearson(xs, scaled_errors)
            rows.extend(group)
    return rows


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def candidate_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault((str(row["max_hp_model"]), str(row["skill_talent_model"])), []).append(row)
    result = []
    for (hp_model, talent_model), group in groups.items():
        errors = [float(row["relative_error"]) for row in group]
        scaled = [float(row["scale_normalized_relative_error"]) for row in group]
        first = group[0]
        result.append({
            "max_hp_model": hp_model, "skill_talent_model": talent_model,
            "mean_relative_error": mean(errors), "relative_error_std": pstdev(errors),
            "ratio_std": first["ratio_std_across_builds"], "diagnostic_scale": first["diagnostic_least_squares_scale"],
            "scaled_error_std": pstdev(scaled), "residual_vs_max_hp": first["residual_vs_max_hp_pearson"],
            "residual_vs_e_bonus": first["residual_vs_final_e_atk_bonus_pearson"],
            "residual_vs_raw_atk": first["residual_vs_raw_stats_atk_pearson"],
            "residual_vs_hp_pct": first["residual_vs_artifact_hp_pct_pearson"],
            "scaled_residual_vs_max_hp": first["scaled_residual_vs_max_hp_pearson"],
        })
    return result


def run_h1_validation(raw_root: str | Path = "data/akasha/raw", output_root: str | Path = "data/akasha") -> dict[str, object]:
    builds = load_hutao_builds(raw_root)
    missing = [build.uid for build in builds if build.uid not in ARTIFACT_HP_BY_UID]
    if missing:
        raise ValueError(f"聖遺物HP内訳がないbuildです: {missing}")
    maxhp_rows = maxhp_reconstruction_rows(builds)
    e_rows = e_bonus_comparison_rows(builds, maxhp_rows)
    output = Path(output_root)
    _write_csv(maxhp_rows, output / "h1_maxhp_reconstruction.csv")
    _write_csv(e_rows, output / "h1_e_bonus_comparison.csv")
    return {
        "build_count": len(builds), "maxhp_rows": len(maxhp_rows), "e_comparison_rows": len(e_rows),
        "e_cap_counts": {str(level): sum(bool(row["e_cap_reached"]) for row in e_rows
                                           if row["max_hp_model"] == "a_lv90_artifacts_homa_r1" and row["skill_talent_model"] == f"fixed_{level}")
                         for level in E_SKILL_RATIOS},
        "candidate_summary": candidate_summary(e_rows),
    }
