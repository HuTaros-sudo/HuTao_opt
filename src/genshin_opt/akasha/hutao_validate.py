"""保存済みrawに対して胡桃単発Damage初期仮説を検証するCLI。"""

import argparse
import json

from .hutao_models import ScenarioConfig
from .hutao_raw import load_hutao_builds
from .hutao_validation import (compare_builds, comparison_row, debug_comparison,
                               largest_component_error, save_comparison_csv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Akasha胡桃の4 componentを初期仮説と比較します")
    parser.add_argument("--raw-root", default="data/akasha/raw", help="保存済みrawのルートまたはpage JSON")
    parser.add_argument("--leaderboard-id", default="1000004605", help="対象calculation ID")
    parser.add_argument("--output", default="data/akasha/hutao_component_comparison.csv", help="比較CSV")
    parser.add_argument("--debug-rank", type=int, default=1, help="中間値を表示するrank。0で非表示")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = ScenarioConfig()
    builds = load_hutao_builds(args.raw_root, args.leaderboard_id)
    comparisons = compare_builds(builds, config)
    output = save_comparison_csv(comparisons, args.output)
    component, error = largest_component_error(comparisons)
    print(f"builds={len(comparisons)} output={output}")
    print(f"largest_component_error={component} max_abs_relative_error={error:.6%}")
    for comparison in comparisons:
        row = comparison_row(comparison)
        print(f"rank={row['rank']} result_error={float(row['result_relative_error']):.6%}")
    if args.debug_rank:
        match = next((item for item in comparisons if item.build.rank == args.debug_rank), None)
        if match is not None:
            print(json.dumps(debug_comparison(match, config), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

