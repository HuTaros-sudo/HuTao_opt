"""`python -m genshin_opt.akasha.h3_validate` 用CLI。"""

import json

from .h3_validation import run_h3_validation


def main() -> None:
    print(json.dumps(run_h3_validation(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
