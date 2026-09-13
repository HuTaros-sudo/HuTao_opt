"""`python -m genshin_opt.akasha.cli`用の観測データ取得CLI。"""

import argparse

from .api import AkashaAPIConfig, AkashaLeaderboardClient, LeaderboardRequest
from .collect import collect_leaderboard


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Akasha leaderboardの観測値をraw JSONとCSVへ保存します")
    parser.add_argument("leaderboard_id", help="Akasha calculation/leaderboard ID")
    parser.add_argument("--max-pages", type=int, default=1, help="取得ページ数。1〜100、既定値1")
    parser.add_argument("--page-size", type=int, default=20, help="1ページの件数。1〜100、既定値20")
    parser.add_argument("--page-delay", type=float, default=1.0, help="ページ間の待機秒。既定値1.0")
    parser.add_argument("--max-retries", type=int, default=2, help="一時エラー時の再試行回数。0〜5")
    parser.add_argument("--retry-delay", type=float, default=2.0, help="再試行前の待機秒。既定値2.0")
    parser.add_argument("--timeout", type=float, default=20.0, help="1リクエストのtimeout秒")
    parser.add_argument("--variant", default="", help="Akashaのvariant。必要な場合だけ指定")
    parser.add_argument("--base-url", default="https://akasha.cv/api", help="API base URL")
    parser.add_argument("--endpoint", default="leaderboards", help="leaderboard endpoint")
    parser.add_argument("--raw-dir", default="data/akasha/raw", help="raw保存ルート")
    parser.add_argument("--csv", default="data/akasha/leaderboard.csv", help="整形済みCSV")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = AkashaAPIConfig(base_url=args.base_url, leaderboard_endpoint=args.endpoint,
                             timeout_seconds=args.timeout, page_delay_seconds=args.page_delay,
                             max_retries=args.max_retries, retry_delay_seconds=args.retry_delay)
    request = LeaderboardRequest(args.leaderboard_id, args.max_pages, args.page_size, args.variant)
    result = collect_leaderboard(AkashaLeaderboardClient(config), request, args.raw_dir, args.csv)
    print(f"leaderboard_id={result.leaderboard_id}")
    print(f"pages={result.pages_fetched} observations={result.observations_saved}")
    print(f"raw={result.raw_directory}")
    print(f"csv={result.csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
