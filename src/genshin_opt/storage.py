"""手入力JSONを型付きデータへ変換する。UIや計算処理には依存しない。"""

import json
from pathlib import Path

from .models import Artifact, Inventory, Slot, Stat, StatValue, Substat
from .validation import ValidationError, require, validate_inventory


def check_fields(data: object, required: set[str], optional: set[str], path: str) -> dict:
    require(isinstance(data, dict), path, "JSONオブジェクトが必要です")
    missing = required - data.keys()
    unknown = data.keys() - required - optional
    require(not missing, path, f"必須項目がありません: {', '.join(sorted(missing))}")
    require(not unknown, path, f"未知の項目があります: {', '.join(sorted(map(str, unknown)))}")
    return data


def parse_enum(enum_type: type[Slot] | type[Stat], value: object, path: str):
    try:
        return enum_type(value)
    except (ValueError, TypeError) as error:
        raise ValidationError(f"{path}: 未対応の種類です: {value!r}") from error


def inventory_from_dict(data: object) -> Inventory:
    root = check_fields(data, {"schema_version", "artifacts"}, set(), "inventory")
    require(type(root["schema_version"]) is int and root["schema_version"] == 1, "schema_version", "対応するバージョンは1です")
    require(isinstance(root["artifacts"], list), "artifacts", "配列が必要です")
    artifacts = []
    for index, raw in enumerate(root["artifacts"]):
        path = f"artifacts[{index}]"
        raw = check_fields(raw, {"id", "slot", "set_name", "rarity", "level", "main_stat", "substats"}, {"initial_substat_count"}, path)
        main = check_fields(raw["main_stat"], {"stat", "value"}, set(), f"{path}.main_stat")
        main_stat = StatValue(parse_enum(Stat, main["stat"], f"{path}.main_stat.stat"), main["value"])
        require(isinstance(raw["substats"], list), f"{path}.substats", "配列が必要です")
        substats = []
        for subindex, sub in enumerate(raw["substats"]):
            subpath = f"{path}.substats[{subindex}]"
            sub = check_fields(sub, {"stat", "value"}, {"initial_value"}, subpath)
            substats.append(Substat(parse_enum(Stat, sub["stat"], f"{subpath}.stat"), sub["value"], sub.get("initial_value")))
        artifacts.append(Artifact(id=raw["id"], slot=parse_enum(Slot, raw["slot"], f"{path}.slot"),
                                  set_name=raw["set_name"], rarity=raw["rarity"], level=raw["level"],
                                  main_stat=main_stat, substats=tuple(substats), initial_substat_count=raw.get("initial_substat_count")))
    inventory = Inventory(root["schema_version"], tuple(artifacts))
    validate_inventory(inventory)
    return inventory


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, "JSON", f"キーが重複しています: {key}")
        result[key] = value
    return result


def reject_constant(value: str):
    raise ValidationError(f"JSON: 非標準の数値は使用できません: {value}")


def load_inventory(path: str | Path) -> Inventory:
    """UTF-8（BOM付きも可）を読む。ファイルI/Oのエラーはそのまま返す。"""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
        return loads_inventory(text)
    except UnicodeDecodeError as error:
        raise ValidationError(f"{path}: UTF-8で保存してください") from error


def loads_inventory(text: str) -> Inventory:
    """UIなどで手入力されたJSON文字列を所持品へ変換する。"""
    require(isinstance(text, str), "JSON", "文字列が必要です")
    try:
        data = json.loads(text, object_pairs_hook=reject_duplicate_keys, parse_constant=reject_constant)
    except json.JSONDecodeError as error:
        raise ValidationError(f"JSON:{error.lineno}:{error.colno}: JSONの書式が不正です: {error.msg}") from error
    return inventory_from_dict(data)
