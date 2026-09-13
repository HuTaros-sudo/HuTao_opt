"""`python -m genshin_opt.akasha.h5_validate` 用のH5検証CLI。"""

import json

from .h5_validation import run_h5_validation


def main() -> None:
    print(json.dumps(run_h5_validation(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

