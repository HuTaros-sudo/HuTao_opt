from genshin_opt.inventory_view import artifact_option_label, deduplicate_inventory, format_game_stat
from genshin_opt.models import Artifact, Inventory, Slot, Stat, StatValue, Substat


def artifact(artifact_id: str, substats: tuple[Substat, ...] | None = None) -> Artifact:
    return Artifact(
        artifact_id, Slot.FLOWER, "燃え盛る炎の魔女", 5, 20, StatValue(Stat.HP_FLAT, 4780),
        substats or (Substat(Stat.CRIT_DMG, 0.0777, 0.0777), Substat(Stat.HP_FLAT, 298.75, 298.75),
                     Substat(Stat.CRIT_RATE, 0.0389, 0.0389), Substat(Stat.ELEMENTAL_MASTERY, 23.31, 23.31)),
        initial_substat_count=4,
    )


def test_game_stat_format_matches_japanese_artifact_display() -> None:
    assert format_game_stat(Stat.CRIT_DMG, 0.0777) == "会心ダメージ7.8%"
    assert format_game_stat(Stat.HP_FLAT, 298.75) == "HP実数299"
    assert format_game_stat(Stat.ENERGY_RECHARGE, 0.0648) == "元素チャージ効率6.5%"


def test_artifact_option_contains_id_set_main_and_all_substats() -> None:
    label = artifact_option_label(artifact("火魔女花5"))
    assert label.startswith("火魔女花5｜燃え盛る炎の魔女｜メイン: HP実数4780｜")
    assert "会心ダメージ7.8%" in label
    assert "HP実数299" in label
    assert "会心率3.9%" in label
    assert "元素熟知23" in label


def test_deduplicate_inventory_ignores_id_and_substat_order() -> None:
    first = artifact("first")
    duplicate = artifact("duplicate", tuple(reversed(first.substats)))
    unique = Artifact("unique", Slot.FLOWER, "燃え盛る炎の魔女", 5, 20,
                      StatValue(Stat.HP_FLAT, 4780),
                      (Substat(Stat.CRIT_DMG, 0.0777, 0.0777), Substat(Stat.HP_FLAT, 268.88, 268.88),
                       Substat(Stat.CRIT_RATE, 0.0389, 0.0389), Substat(Stat.ELEMENTAL_MASTERY, 23.31, 23.31)), 4)
    result = deduplicate_inventory(Inventory(1, (first, duplicate, unique)))
    assert tuple(item.id for item in result.artifacts) == ("first", "unique")


def test_deduplicate_preserves_different_reshape_initial_values() -> None:
    first = artifact("first")
    changed = list(first.substats)
    changed[0] = Substat(Stat.CRIT_DMG, 0.0777, 0.0544)
    result = deduplicate_inventory(Inventory(1, (first, artifact("changed", tuple(changed)))))
    assert len(result.artifacts) == 2
