"""`python -m genshin_opt.akasha.atk_boundary_validate` 用CLI。"""

import json

from .atk_boundary_validation import run_atk_boundary_validation


def main() -> None:
    print(json.dumps(run_atk_boundary_validation(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

