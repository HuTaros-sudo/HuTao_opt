"""`python -m genshin_opt.akasha.crit_validate`用CLI。"""

import json

from .crit_validation import run_crit_validation


def main() -> None:
    print(json.dumps(run_crit_validation(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
