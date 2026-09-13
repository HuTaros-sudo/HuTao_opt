"""通常の入力検証と、将来の再構築用データの必須チェック。"""

import math

from .models import Artifact, Inventory, Slot, Stat, StatValue, Substat


class ValidationError(ValueError):
    """入力項目の場所と原因を含むエラー。"""


SUBSTAT_TYPES = frozenset({Stat.HP_FLAT, Stat.ATK_FLAT, Stat.DEF_FLAT, Stat.HP_PERCENT,
                          Stat.ATK_PERCENT, Stat.DEF_PERCENT, Stat.ELEMENTAL_MASTERY,
                          Stat.ENERGY_RECHARGE, Stat.CRIT_RATE, Stat.CRIT_DMG})
PERCENT_TYPES = frozenset(Stat) - {Stat.HP_FLAT, Stat.ATK_FLAT, Stat.DEF_FLAT, Stat.ELEMENTAL_MASTERY}
COMMON_MAIN = {Stat.HP_PERCENT, Stat.ATK_PERCENT, Stat.DEF_PERCENT, Stat.ELEMENTAL_MASTERY}
MAIN_TYPES = {
    Slot.FLOWER: {Stat.HP_FLAT},
    Slot.PLUME: {Stat.ATK_FLAT},
    Slot.SANDS: COMMON_MAIN | {Stat.ENERGY_RECHARGE},
    Slot.GOBLET: COMMON_MAIN | {Stat.PYRO_DMG, Stat.HYDRO_DMG, Stat.CRYO_DMG, Stat.ELECTRO_DMG,
                               Stat.ANEMO_DMG, Stat.GEO_DMG, Stat.DENDRO_DMG, Stat.PHYSICAL_DMG},
    Slot.CIRCLET: COMMON_MAIN | {Stat.CRIT_RATE, Stat.CRIT_DMG, Stat.HEALING_BONUS},
}


def require(condition: bool, path: str, message: str) -> None:
    if not condition:
        raise ValidationError(f"{path}: {message}")


def validate_number(value: float, stat: Stat, path: str) -> None:
    require(type(value) in (int, float), path, "数値を入力してください（文字列・真偽値は不可）")
    require(value > 0 and value < math.inf, path, "有限の正の数を入力してください")
    if stat in PERCENT_TYPES:
        require(value <= 1, path, "割合は小数で入力してください（46.6% → 0.466）")


def validate_artifact(artifact: Artifact, path: str = "artifact") -> None:
    """初期値なし・一部のみ入力された聖遺物も通常用途では許可する。"""
    require(isinstance(artifact, Artifact), path, "Artifactが必要です")
    for field in ("id", "set_name"):
        value = getattr(artifact, field)
        require(isinstance(value, str) and bool(value.strip()), f"{path}.{field}", "空でない文字列が必要です")
        require(value == value.strip(), f"{path}.{field}", "前後の空白を除いてください")
    require(isinstance(artifact.slot, Slot), f"{path}.slot", "有効なSlotが必要です")
    require(type(artifact.rarity) is int and artifact.rarity == 5, f"{path}.rarity", "現在は★5のみ対応しています")
    require(type(artifact.level) is int and 0 <= artifact.level <= 20, f"{path}.level", "0〜20の整数が必要です")
    count = artifact.initial_substat_count
    require(count is None or (type(count) is int and count in (3, 4)), f"{path}.initial_substat_count", "3、4、またはnullが必要です")
    require(isinstance(artifact.main_stat, StatValue), f"{path}.main_stat", "StatValueが必要です")
    main = artifact.main_stat
    require(isinstance(main.stat, Stat) and main.stat in MAIN_TYPES[artifact.slot], f"{path}.main_stat.stat", "部位に対応しないメインステータスです")
    validate_number(main.value, main.stat, f"{path}.main_stat.value")
    require(isinstance(artifact.substats, tuple), f"{path}.substats", "Substatのtupleが必要です")
    allowed_counts = (3, 4) if artifact.level < 4 else (4,)
    require(len(artifact.substats) in allowed_counts, f"{path}.substats", "Lv.0〜3は3〜4種類、Lv.4以上は4種類が必要です")
    if count is not None and artifact.level < 4:
        require(count == len(artifact.substats), f"{path}.initial_substat_count", "現在のサブステータス数と一致しません")
    seen = set()
    for index, sub in enumerate(artifact.substats):
        subpath = f"{path}.substats[{index}]"
        require(isinstance(sub, Substat), subpath, "Substatが必要です")
        require(isinstance(sub.stat, Stat) and sub.stat in SUBSTAT_TYPES, f"{subpath}.stat", "サブステータスに使用できない種類です")
        require(sub.stat not in seen, f"{subpath}.stat", "サブステータスが重複しています")
        require(sub.stat != main.stat, f"{subpath}.stat", "メインと同じ種類は使用できません")
        seen.add(sub.stat)
        validate_number(sub.value, sub.stat, f"{subpath}.value")
        if sub.initial_value is not None:
            validate_number(sub.initial_value, sub.stat, f"{subpath}.initial_value")
            require(sub.initial_value <= sub.value, f"{subpath}.initial_value", "現在値以下にしてください")
            if artifact.level < 4:
                require(sub.initial_value == sub.value, f"{subpath}.initial_value", "Lv.0〜3では現在値と同じ値にしてください")


def validate_inventory(inventory: Inventory) -> None:
    require(isinstance(inventory, Inventory), "inventory", "Inventoryが必要です")
    require(type(inventory.schema_version) is int and inventory.schema_version == 1, "schema_version", "対応するバージョンは1です")
    require(isinstance(inventory.artifacts, tuple), "artifacts", "Artifactのtupleが必要です")
    seen = set()
    for index, artifact in enumerate(inventory.artifacts):
        path = f"artifacts[{index}]"
        validate_artifact(artifact, path)
        require(artifact.id not in seen, f"{path}.id", f"IDが重複しています: {artifact.id}")
        seen.add(artifact.id)


def validate_for_reshape(artifact: Artifact) -> None:
    """再構築用の初期データがそろっているか検証する。確率計算はしない。"""
    validate_artifact(artifact)
    require(artifact.level == 20, "artifact.level", "再構築用にはLv.20が必要です")
    require(artifact.initial_substat_count is not None, "artifact.initial_substat_count", "再構築用には初期の種類数が必要です")
    for index, sub in enumerate(artifact.substats):
        require(sub.initial_value is not None, f"artifact.substats[{index}].initial_value", "再構築用には全4種類の初期値が必要です")
