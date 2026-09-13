"""Streamlitの聖啓の塵入力で使う、編集可能な初期値。"""

from .models import Stat


DUST_ROLL_TIERS = ("低", "中", "高", "最高")
DEFAULT_DUST_ROLL_PROBABILITIES_PERCENT = (25.0, 25.0, 25.0, 25.0)
DEFAULT_DUST_UPDATE_PROBABILITY_PERCENT = 25.0
DEFAULT_DUST_ROLL_VALUES_DISPLAY = {
    Stat.ATK_FLAT: (13.62, 15.56, 17.51, 19.45),
    Stat.ATK_PERCENT: (4.08, 4.66, 5.25, 5.83),
    Stat.DEF_FLAT: (16.20, 18.52, 20.83, 23.15),
    Stat.DEF_PERCENT: (5.10, 5.83, 6.56, 7.29),
    Stat.HP_FLAT: (209.13, 239.00, 268.88, 298.75),
    Stat.HP_PERCENT: (4.08, 4.66, 5.25, 5.83),
    Stat.ELEMENTAL_MASTERY: (16.32, 18.65, 20.98, 23.31),
    Stat.ENERGY_RECHARGE: (4.53, 5.18, 5.83, 6.48),
    Stat.CRIT_RATE: (2.72, 3.11, 3.50, 3.89),
    Stat.CRIT_DMG: (5.44, 6.22, 6.99, 7.77),
}


PERCENT_ROLL_STATS = {
    Stat.ATK_PERCENT, Stat.DEF_PERCENT, Stat.HP_PERCENT, Stat.ENERGY_RECHARGE, Stat.CRIT_RATE, Stat.CRIT_DMG,
}


def roll_value_to_internal(stat: Stat, displayed_value: float) -> float:
    """GUIの百分率表示を、モデルが使う0〜1表現へ変換する。"""
    return displayed_value / 100 if stat in PERCENT_ROLL_STATS else displayed_value
