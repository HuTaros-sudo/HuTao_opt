"""`python -m genshin_opt.akasha.build_residual_validate`用CLI。"""

import json

from .build_residual_validation import run_build_residual_validation


if __name__ == "__main__":
    print(json.dumps(run_build_residual_validation(), ensure_ascii=False, indent=2))
