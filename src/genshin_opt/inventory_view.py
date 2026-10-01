"""Inventoryの重複除外と、GUI向け聖遺物表示文字列。"""

from .models import Artifact, Inventory, Stat
from .validation import PERCENT_TYPES


STAT_JAPANESE_LABELS = {
    Stat.HP_FLAT: "HP実数", Stat.ATK_FLAT: "攻撃力実数", Stat.DEF_FLAT: "防御力実数",
    Stat.HP_PERCENT: "HP", Stat.ATK_PERCENT: "攻撃力", Stat.DEF_PERCENT: "防御力",
    Stat.ELEMENTAL_MASTERY: "元素熟知", Stat.ENERGY_RECHARGE: "元素チャージ効率",
    Stat.CRIT_RATE: "会心率", Stat.CRIT_DMG: "会心ダメージ",
    Stat.PYRO_DMG: "炎元素ダメージ", Stat.HYDRO_DMG: "水元素ダメージ",
    Stat.CRYO_DMG: "氷元素ダメージ", Stat.ELECTRO_DMG: "雷元素ダメージ",
    Stat.ANEMO_DMG: "風元素ダメージ", Stat.GEO_DMG: "岩元素ダメージ",
    Stat.DENDRO_DMG: "草元素ダメージ", Stat.PHYSICAL_DMG: "物理ダメージ",
    Stat.HEALING_BONUS: "与える治療効果",
}


def format_game_stat(stat: Stat, value: float) -> str:
    """内部値をゲーム画面に近い整数・小数1桁表示へ変換する。"""
    label = STAT_JAPANESE_LABELS[stat]
    if stat in PERCENT_TYPES:
        return f"{label}{value * 100:.1f}%"
    return f"{label}{value:.0f}"


def artifact_option_label(artifact: Artifact) -> str:
    main = format_game_stat(artifact.main_stat.stat, artifact.main_stat.value)
    substats = "、".join(format_game_stat(substat.stat, substat.value) for substat in artifact.substats)
    return f"{artifact.id}｜{artifact.set_name}｜メイン: {main}｜{substats}"


def artifact_content_signature(artifact: Artifact) -> tuple[object, ...]:
    """IDと入力順を除き、部位・セット・現在値・再構築用初期値を比較する。"""
    substats = tuple(sorted(
        ((substat.stat.value, substat.value, substat.initial_value) for substat in artifact.substats),
        key=lambda item: item[0],
    ))
    return (artifact.slot.value, artifact.set_name, artifact.main_stat.stat.value, artifact.main_stat.value,
            substats, artifact.initial_substat_count)


def deduplicate_inventory(inventory: Inventory) -> Inventory:
    """完全に同じ内容の聖遺物は最初の1件だけを残す。入力JSONは変更しない。"""
    seen = set()
    artifacts = []
    for artifact in inventory.artifacts:
        signature = artifact_content_signature(artifact)
        if signature in seen:
            continue
        seen.add(signature)
        artifacts.append(artifact)
    return Inventory(inventory.schema_version, tuple(artifacts))
