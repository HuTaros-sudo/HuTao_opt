"""`python -m genshin_opt.akasha.h4_validate`用CLI。"""

import json

from .h4_validation import run_h4_validation


def main() -> None:
    print(json.dumps(run_h4_validation(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
