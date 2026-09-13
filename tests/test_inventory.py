import copy
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from genshin_opt.models import Slot, Stat
from genshin_opt.storage import inventory_from_dict, load_inventory
from genshin_opt.validation import ValidationError, validate_artifact, validate_for_reshape, validate_inventory


SAMPLE_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_inventory.json"


@pytest.fixture
def payload():
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def test_sample_loads_all_slots_and_optional_initial_values():
    inventory = load_inventory(SAMPLE_PATH)
    validate_inventory(inventory)
    assert inventory.schema_version == 1
    assert {artifact.slot for artifact in inventory.artifacts} == set(Slot)
    assert len(inventory.artifacts) == 5
    flower, plume, sands, *_ = inventory.artifacts
    assert flower.main_stat.stat is Stat.HP_FLAT
    assert flower.main_stat.value == 4780
    assert all(sub.initial_value is None for sub in flower.substats)
    assert plume.substats[0].initial_value == 0.035
    assert sands.main_stat.value == 0.466
    assert sands.substats[0].initial_value == 0.035
    assert sands.substats[1].initial_value is None
    assert sands.substats[2].initial_value is None


def test_initial_values_are_not_required_for_normal_validation():
    plume = load_inventory(SAMPLE_PATH).artifacts[1]
    without_initial = replace(plume, substats=tuple(replace(sub, initial_value=None) for sub in plume.substats), initial_substat_count=None)
    validate_artifact(without_initial)
    assert [(sub.stat, sub.value) for sub in plume.substats] == [(sub.stat, sub.value) for sub in without_initial.substats]
    assert without_initial.main_stat == plume.main_stat
    with pytest.raises(ValidationError, match="initial_substat_count"):
        validate_for_reshape(without_initial)


@pytest.mark.parametrize("count", [3, 4])
def test_reshape_accepts_complete_initial_data(count):
    artifact = load_inventory(SAMPLE_PATH).artifacts[1]
    validate_for_reshape(replace(artifact, initial_substat_count=count))


@pytest.mark.parametrize("index", range(4))
def test_reshape_requires_each_initial_value(index):
    artifact = load_inventory(SAMPLE_PATH).artifacts[1]
    substats = list(artifact.substats)
    substats[index] = replace(substats[index], initial_value=None)
    artifact = replace(artifact, substats=tuple(substats))
    validate_artifact(artifact)
    with pytest.raises(ValidationError, match=rf"substats\[{index}\].initial_value"):
        validate_for_reshape(artifact)


def test_reshape_requires_max_level():
    artifact = replace(load_inventory(SAMPLE_PATH).artifacts[1], level=19)
    validate_artifact(artifact)
    with pytest.raises(ValidationError, match="Lv.20"):
        validate_for_reshape(artifact)


@pytest.mark.parametrize("field,value", [
    ("id", ""), ("id", "   "), ("id", " flower "), ("set_name", None),
    ("slot", "feather"), ("rarity", 4), ("rarity", True), ("level", -1),
    ("level", 21), ("level", True), ("level", 20.0), ("level", "20"),
    ("initial_substat_count", 2), ("initial_substat_count", 4.0), ("initial_substat_count", True),
])
def test_invalid_artifact_fields(payload, field, value):
    payload["artifacts"][0][field] = value
    with pytest.raises(ValidationError, match=rf"artifacts\[0\].{field}"):
        inventory_from_dict(payload)


@pytest.mark.parametrize("value", [0, -1, True, "0.1", None, float("nan"), float("inf"), float("-inf"), 1e100])
def test_invalid_stat_values(payload, value):
    payload["artifacts"][0]["substats"][0]["value"] = value
    with pytest.raises(ValidationError, match=r"substats\[0\].value"):
        inventory_from_dict(payload)


@pytest.mark.parametrize("value", [0, -0.1, True, "0.035", float("nan"), float("inf"), 0.2])
def test_invalid_initial_values(payload, value):
    payload["artifacts"][1]["substats"][0]["initial_value"] = value
    with pytest.raises(ValidationError, match="initial_value"):
        inventory_from_dict(payload)


@pytest.mark.parametrize("stat", ["crit_rate", "hp_flat", "pyro_dmg", "typo"])
def test_invalid_substat_type_or_duplication(payload, stat):
    payload["artifacts"][0]["substats"][1]["stat"] = stat
    with pytest.raises(ValidationError, match=r"substats\[1\].stat"):
        inventory_from_dict(payload)


def test_main_stat_must_match_slot(payload):
    payload["artifacts"][0]["main_stat"]["stat"] = "atk_flat"
    with pytest.raises(ValidationError, match="main_stat.stat"):
        inventory_from_dict(payload)


def test_duplicate_artifact_ids_rejected(payload):
    payload["artifacts"].append(copy.deepcopy(payload["artifacts"][0]))
    with pytest.raises(ValidationError, match=r"artifacts\[5\].id"):
        inventory_from_dict(payload)


def test_empty_and_incomplete_inventories_allowed(payload):
    assert inventory_from_dict({"schema_version": 1, "artifacts": []}).artifacts == ()
    payload["artifacts"] = payload["artifacts"][:1]
    assert len(inventory_from_dict(payload).artifacts) == 1


@pytest.mark.parametrize("level", [0, 3, 4, 20])
def test_substat_count_level_boundary(payload, level):
    raw = payload["artifacts"][0]
    raw["level"] = level
    raw["substats"] = raw["substats"][:3]
    if level < 4:
        inventory_from_dict(payload)
    else:
        with pytest.raises(ValidationError, match="substats"):
            inventory_from_dict(payload)


def test_initial_count_and_values_before_first_upgrade(payload):
    raw = payload["artifacts"][1]
    raw["level"] = 0
    for sub in raw["substats"]:
        sub["value"] = sub["initial_value"]
    inventory_from_dict(payload)
    raw["initial_substat_count"] = 3
    with pytest.raises(ValidationError, match="initial_substat_count"):
        inventory_from_dict(payload)
    raw["initial_substat_count"] = 4
    raw["substats"][0]["value"] = 0.07
    with pytest.raises(ValidationError, match="initial_value"):
        inventory_from_dict(payload)


@pytest.mark.parametrize("data", [[], None, {}, {"schema_version": True, "artifacts": []},
                                   {"schema_version": 2, "artifacts": []}, {"schema_version": 1, "artifacts": {}}])
def test_invalid_root(data):
    with pytest.raises(ValidationError):
        inventory_from_dict(data)


@pytest.mark.parametrize("target", ["root", "artifact", "main", "sub"])
def test_unknown_keys_are_not_silently_ignored(payload, target):
    raw = payload["artifacts"][0]
    objects = {"root": payload, "artifact": raw, "main": raw["main_stat"], "sub": raw["substats"][0]}
    objects[target]["typo"] = 1
    with pytest.raises(ValidationError, match="未知の項目"):
        inventory_from_dict(payload)


def test_missing_required_field_has_location(payload):
    del payload["artifacts"][0]["substats"][0]["value"]
    with pytest.raises(ValidationError, match=r"artifacts\[0\].substats\[0\].*value"):
        inventory_from_dict(payload)


@pytest.mark.parametrize("text", ['{"schema_version":1,}', '{"schema_version":1,"schema_version":1,"artifacts":[]}',
                                  '{"schema_version":1,"artifacts":NaN}', '{"schema_version":1,"artifacts":Infinity}'])
def test_invalid_json(tmp_path, text):
    path = tmp_path / "invalid.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValidationError, match="JSON"):
        load_inventory(path)


def test_utf8_bom_and_japanese_path(tmp_path, payload):
    path = tmp_path / "所持聖遺物.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8-sig")
    assert load_inventory(path).artifacts[0].set_name == "人工セットA"


def test_missing_file_and_invalid_encoding(tmp_path):
    path = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        load_inventory(path)
    path.write_bytes(b"\xff")
    with pytest.raises(ValidationError, match="UTF-8"):
        load_inventory(path)


def test_models_are_immutable_and_validation_applies_to_python_objects():
    artifact = load_inventory(SAMPLE_PATH).artifacts[0]
    with pytest.raises(FrozenInstanceError):
        artifact.level = 0
    with pytest.raises(ValidationError, match="level"):
        validate_artifact(replace(artifact, level=True))
    with pytest.raises(ValidationError, match="substats"):
        validate_artifact(replace(artifact, substats=[]))
