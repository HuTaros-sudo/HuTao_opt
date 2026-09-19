from dataclasses import replace

import pytest

from genshin_opt.akasha.cross_weapon_validation import (CATEGORIES, category_summaries,
                                                         cross_weapon_missing_rows,
                                                         missing_atk_model_comparison,
                                                         parse_jina_api_payload,
                                                         scenario_difference_flags)
from genshin_opt.akasha.hutao_models import AkashaHutaoBuild, ObservedComponents
from genshin_opt.akasha.hutao_raw import load_hutao_builds
from genshin_opt.akasha.hutao_score import score_hutao_akasha


def synthetic_build(leaderboard_id: str, rank: int, base_atk: float, missing_atk: float) -> AkashaHutaoBuild:
    build = AkashaHutaoBuild(
        input_source="synthetic", max_hp=32000.0, sheet_atk=1200.0, base_atk=base_atk,
        crit_rate=0.8, crit_dmg=2.0, elemental_mastery=200.0, pyro_dmg_bonus=0.616,
        artifact_sets=(("Crimson Witch of Flames", 4),), leaderboard_id=leaderboard_id, rank=rank,
        uid=f"uid-{leaderboard_id}-{rank}", build_md5=f"md5-{leaderboard_id}-{rank}",
        entry_id=f"entry-{leaderboard_id}-{rank}", raw_path="synthetic",
        observed=ObservedComponents(1, 1, 1, 1), observed_result=1,
    )
    score = score_hutao_akasha(build)
    multiplier = score.debug_breakdown["components"]["n1_non_vape"]
    fixed = (multiplier["talent_multiplier"] * multiplier["damage_bonus_multiplier"]
             * multiplier["crit_multiplier"] * multiplier["def_multiplier"]
             * multiplier["res_multiplier"] * multiplier["reaction_multiplier"])
    observed = replace(build.observed, n1_non_vape=(score.debug_breakdown["final_atk"] + missing_atk) * fixed)
    return replace(build, observed=observed)


def test_jina_payload_parser_removes_proxy_header(tmp_path) -> None:
    path = tmp_path / "payload.txt"
    path.write_text('Title:\n\nMarkdown Content:\n{"data": [{"value": 1}]}', encoding="utf-8")
    assert parse_jina_api_payload(path) == {"data": [{"value": 1}]}


def test_scenario_audit_has_no_false_weapon_only_difference() -> None:
    flags = scenario_difference_flags(CATEGORIES[2])
    assert not any(flags.values())
    assert CATEGORIES[2].identification_eligible
    assert not CATEGORIES[1].identification_eligible


def test_model_comparison_excludes_ineligible_weapon() -> None:
    builds = {
        "1000004605": tuple(synthetic_build("1000004605", rank, 714.5, 300.0) for rank in (1, 2)),
        "1000004606": tuple(synthetic_build("1000004606", rank, 648.2, 900.0) for rank in (1, 2)),
        "1000004607": tuple(synthetic_build("1000004607", rank, 616.0, 280.0) for rank in (1, 2)),
    }
    rows = cross_weapon_missing_rows(builds)
    summaries = category_summaries(rows)
    scarlet = next(row for row in summaries if row["leaderboard_id"] == "1000004606")
    assert not scarlet["identification_eligible"]
    models = missing_atk_model_comparison(rows)
    category_model = next(row for row in models if row["model"] == "D_weapon_category")
    assert category_model["residual_std"] == pytest.approx(0)


def test_score_hutao_akasha_homa_baseline_is_bit_identical() -> None:
    result = score_hutao_akasha(load_hutao_builds("data/akasha/raw", "1000004605")[0])
    actual = tuple(value.hex() for value in (result.n1_non_vape_avg, result.n1_vape_avg,
                                              result.ca_vape_avg, result.q_vape_avg,
                                              result.aggregate_score))
    assert actual == (
        "0x1.26b0389b5c47cp+14", "0x1.a8f0c17e4e4c6p+15", "0x1.3448ff839809ep+17",
        "0x1.7135f0da10e1ep+18", "0x1.1d635d97b334fp+21",
    )
