"""`python -m genshin_opt.akasha.h6_validate` 用CLI。"""

import json

from .h6_validation import run_h6_validation


def main() -> None:
    print(json.dumps(run_h6_validation(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
