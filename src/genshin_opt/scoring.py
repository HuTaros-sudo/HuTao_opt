"""実ゲームの火力式とは独立した、optimizer検証用の人工評価関数。"""

from collections.abc import Mapping, Sequence

from .models import Artifact, Stat
from .stats import aggregate_current_stats, to_display_stats


def toy_score(stats: Mapping[Stat, float]) -> float:
    """表示上の会心率・会心ダメージ・HP%・元素熟知を人工的に評価する。"""
    cr = stats.get(Stat.CRIT_RATE, 0.0)
    cd = stats.get(Stat.CRIT_DMG, 0.0)
    hp = stats.get(Stat.HP_PERCENT, 0.0)
    em = stats.get(Stat.ELEMENTAL_MASTERY, 0.0)

    base = 2 * cr + cd + 0.3 * hp + 0.05 * em
    balance_penalty = abs(cd - 2 * cr) * 0.5
    return base - balance_penalty


def toy_build_score(artifacts: Sequence[Artifact]) -> float:
    """5部位の現在値を表示単位に直してtoy_scoreへ渡す。"""
    stats = to_display_stats(aggregate_current_stats(artifacts))
    return toy_score(stats)
