from genshin_opt.akasha.build_residual_validation import (candidate_comparison_rows, correlation_rows,
                                                          residual_rows)
from genshin_opt.akasha.hutao_raw import load_hutao_builds


BUILDS = load_hutao_builds("data/akasha/raw")


def test_scale_removed_residual_dataset_contains_20_builds_and_hp_contributions():
    rows = residual_rows(BUILDS)
    assert len(rows) == 20
    assert all("max_hp_div_raw_atk" in row and "e_bonus_div_final_atk" in row for row in rows)
    assert all(row["diagnostic_common_scale"] > 1 for row in rows)


def test_correlations_include_pearson_spearman_and_crimson_witch_only_scope():
    rows = residual_rows(BUILDS)
    all_correlations = correlation_rows(rows, "all_20")
    witch_correlations = correlation_rows(rows, "crimson_witch_19")
    assert len(all_correlations) == len(witch_correlations) == 14
    assert {row["build_count"] for row in all_correlations} == {20}
    assert {row["build_count"] for row in witch_correlations} == {19}
    assert all("pearson" in row and "spearman" in row for row in all_correlations)


def test_discrete_e_and_base_atk_candidates_have_requested_ranking_metrics():
    rows = candidate_comparison_rows(BUILDS)
    assert {row["candidate"] for row in rows if row["candidate_kind"] == "e_talent_level"} == {
        "e_lv9", "e_lv10", "e_lv11", "e_lv13",
    }
    assert {row["candidate"] for row in rows if row["candidate_kind"] == "base_atk"} == {
        "raw_internal_714.5089773", "displayed_714",
    }
    assert all("scale_removed_residual_std" in row and "under_0.1_percent_accuracy" in row for row in rows)
