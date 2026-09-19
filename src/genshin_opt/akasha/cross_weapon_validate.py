"""cross-weapon診断CSVを生成するCLI。"""

import json

from .cross_weapon_validation import run_cross_weapon_validation


def main() -> None:
    result = run_cross_weapon_validation()
    printable = {"category_summaries": result["category_summaries"],
                 "model_comparison": result["model_comparison"]}
    print(json.dumps(printable, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
