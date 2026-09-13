"""聖遺物の現在値を集計する。初期値は再構築専用なので使用しない。"""

from collections.abc import Iterable

from .models import Artifact, Stat
from .validation import PERCENT_TYPES


def aggregate_current_stats(artifacts: Iterable[Artifact]) -> dict[Stat, float]:
    """メインとサブの現在値を、JSONと同じ内部単位で合計する。"""
    totals: dict[Stat, float] = {}
    for artifact in artifacts:
        totals[artifact.main_stat.stat] = totals.get(artifact.main_stat.stat, 0.0) + artifact.main_stat.value
        for substat in artifact.substats:
            totals[substat.stat] = totals.get(substat.stat, 0.0) + substat.value
    return totals


def to_display_stats(stats: dict[Stat, float]) -> dict[Stat, float]:
    """割合を百分率へ変換し、画面表示相当の数値にする。"""
    return {stat: value * 100 if stat in PERCENT_TYPES else value for stat, value in stats.items()}
