"""保存済みAkasha buildに対する相対順位再現性能を診断する。"""

import csv
import math
from pathlib import Path
from statistics import mean

from .hutao_models import AkashaHutaoBuild, ScenarioConfig
from .hutao_raw import load_hutao_builds
from .hutao_score import score_hutao_akasha


NEARBY_THRESHOLDS = (0.001, 0.0025, 0.005, 0.01)


def _pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = mean(xs), mean(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    denominator = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return numerator / denominator if denominator else float("nan")


def _descending_ranks(values: list[float]) -> list[float]:
    """同値へ平均順位を割り当てる。"""
    ordered = sorted(range(len(values)), key=lambda index: values[index], reverse=True)
    ranks = [0.0] * len(values)
    position = 0
    while position < len(ordered):
        end = position + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[position]]:
            end += 1
        average_rank = ((position + 1) + end) / 2
        for index in ordered[position:end]:
            ranks[index] = average_rank
        position = end
    return ranks


def _kendall_tau_b(xs: list[float], ys: list[float]) -> float:
    concordant = discordant = x_ties = y_ties = 0
    for left in range(len(xs)):
        for right in range(left + 1, len(xs)):
            x_sign = (xs[left] > xs[right]) - (xs[left] < xs[right])
            y_sign = (ys[left] > ys[right]) - (ys[left] < ys[right])
            if x_sign == 0 and y_sign == 0:
                continue
            if x_sign == 0:
                x_ties += 1
            elif y_sign == 0:
                y_ties += 1
            elif x_sign == y_sign:
                concordant += 1
            else:
                discordant += 1
    denominator = math.sqrt((concordant + discordant + x_ties) * (concordant + discordant + y_ties))
    return (concordant - discordant) / denominator if denominator else float("nan")


def ranking_rows(builds: tuple[AkashaHutaoBuild, ...], config: ScenarioConfig | None = None) -> list[dict[str, object]]:
    scenario = config or ScenarioConfig()
    observed = [build.observed_result for build in builds]
    predicted = [score_hutao_akasha(build, scenario).aggregate_score for build in builds]
    observed_ranks = _descending_ranks(observed)
    predicted_ranks = _descending_ranks(predicted)
    scale = sum(obs * pred for obs, pred in zip(observed, predicted, strict=True)) / sum(pred**2 for pred in predicted)
    rows = []
    for build, obs, pred, observed_rank, predicted_rank in zip(
            builds, observed, predicted, observed_ranks, predicted_ranks, strict=True):
        rows.append({
            "leaderboard_id": build.leaderboard_id, "api_rank": build.rank, "uid": build.uid,
            "build_md5": build.build_md5, "observed_result": obs, "predicted_result": pred,
            "relative_error": pred / obs - 1, "observed_rank": observed_rank,
            "predicted_rank": predicted_rank, "rank_difference": predicted_rank - observed_rank,
            "exact_rank_position": predicted_rank == observed_rank, "diagnostic_common_scale": scale,
            "scaled_predicted_result": scale * pred, "scaled_relative_error": scale * pred / obs - 1,
        })
    return rows


def pairwise_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    pairs = []
    for left in range(len(rows)):
        for right in range(left + 1, len(rows)):
            a, b = rows[left], rows[right]
            observed_difference = float(a["observed_result"]) - float(b["observed_result"])
            predicted_difference = float(a["predicted_result"]) - float(b["predicted_result"])
            observed_sign = (observed_difference > 0) - (observed_difference < 0)
            predicted_sign = (predicted_difference > 0) - (predicted_difference < 0)
            relative_gap = abs(observed_difference) / max(abs(float(a["observed_result"])), abs(float(b["observed_result"])))
            row = {
                "uid_a": a["uid"], "build_md5_a": a["build_md5"], "uid_b": b["uid"],
                "build_md5_b": b["build_md5"], "observed_result_a": a["observed_result"],
                "observed_result_b": b["observed_result"], "predicted_result_a": a["predicted_result"],
                "predicted_result_b": b["predicted_result"], "observed_difference": observed_difference,
                "observed_relative_gap": relative_gap, "predicted_difference": predicted_difference,
                "ordering_correct": observed_sign != 0 and observed_sign == predicted_sign,
                "observed_tie": observed_sign == 0, "predicted_tie": predicted_sign == 0,
            }
            for threshold in NEARBY_THRESHOLDS:
                row[f"within_{threshold * 100:g}_percent"] = relative_gap < threshold
            pairs.append(row)
    return pairs


def ranking_summary(rows: list[dict[str, object]], pairs: list[dict[str, object]]) -> dict[str, object]:
    observed = [float(row["observed_result"]) for row in rows]
    predicted = [float(row["predicted_result"]) for row in rows]
    observed_ranks = [float(row["observed_rank"]) for row in rows]
    predicted_ranks = [float(row["predicted_rank"]) for row in rows]
    eligible = [row for row in pairs if not row["observed_tie"]]
    nearby = {}
    for threshold in NEARBY_THRESHOLDS:
        selected = [row for row in eligible if float(row["observed_relative_gap"]) < threshold]
        nearby[f"under_{threshold * 100:g}_percent"] = {
            "pair_count": len(selected),
            "accuracy": sum(bool(row["ordering_correct"]) for row in selected) / len(selected) if selected else None,
        }
    scale = float(rows[0]["diagnostic_common_scale"])
    scaled_ranks = _descending_ranks([scale * value for value in predicted])
    return {
        "build_count": len(rows), "pearson": _pearson(observed, predicted),
        "spearman": _pearson(observed_ranks, predicted_ranks), "kendall_tau_b": _kendall_tau_b(observed, predicted),
        "exact_rank_positions": sum(bool(row["exact_rank_position"]) for row in rows),
        "all_pair_count": len(eligible),
        "pairwise_ordering_accuracy": sum(bool(row["ordering_correct"]) for row in eligible) / len(eligible),
        "nearby": nearby, "diagnostic_common_scale": scale,
        "scale_preserves_all_predicted_ranks": scaled_ranks == predicted_ranks,
        "mean_relative_error": mean(float(row["relative_error"]) for row in rows),
        "scaled_mean_relative_error": mean(float(row["scaled_relative_error"]) for row in rows),
    }


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def run_ranking_validation(raw_root: str | Path = "data/akasha/raw",
                           output_root: str | Path = "data/akasha") -> dict[str, object]:
    builds = load_hutao_builds(raw_root)
    rows = ranking_rows(builds)
    pairs = pairwise_rows(rows)
    output = Path(output_root)
    _write_csv(rows, output / "ranking_fidelity.csv")
    _write_csv(pairs, output / "pairwise_ordering.csv")
    return ranking_summary(rows, pairs)
