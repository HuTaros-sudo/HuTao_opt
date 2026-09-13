from pathlib import Path


RAW_DEPENDENT_TESTS = frozenset({
    "test_akasha_atk_boundary.py", "test_akasha_build_residual_validation.py",
    "test_akasha_crit_validation.py", "test_akasha_h1_validation.py", "test_akasha_h3_validation.py",
    "test_akasha_h4_validation.py", "test_akasha_h5_validation.py", "test_akasha_h6_validation.py",
    "test_akasha_hutao_score.py", "test_akasha_hutao_validation.py", "test_akasha_ranking_validation.py",
})
HAS_LOCAL_AKASHA_RAW = any(Path("data/akasha/raw").rglob("page_*.json"))


def pytest_ignore_collect(collection_path: Path, config: object) -> bool:
    """公開cloneでは、Git管理外のAkasha観測rawを必要とする診断テストを収集しない。"""
    return not HAS_LOCAL_AKASHA_RAW and collection_path.name in RAW_DEPENDENT_TESTS
