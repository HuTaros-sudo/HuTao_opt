"""`python -m genshin_opt.akasha.ranking_validate`用の診断CLI。"""

import json

from .ranking_validation import run_ranking_validation


if __name__ == "__main__":
    print(json.dumps(run_ranking_validation(), ensure_ascii=False, indent=2))
