"""既知ATK buff / raw境界監査のCLI。"""

import json

from .atk_buff_validation import run_atk_buff_validation


def main() -> None:
    print(json.dumps(run_atk_buff_validation(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
