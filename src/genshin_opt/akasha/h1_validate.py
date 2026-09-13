"""`python -m genshin_opt.akasha.h1_validate` 用CLI。"""

import json

from .h1_validation import run_h1_validation


def main() -> None:
    print(json.dumps(run_h1_validation(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
