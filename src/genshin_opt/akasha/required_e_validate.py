"""required final ATK / E contribution診断CLI。"""

import json

from .required_e_validation import run_required_e_validation


def main() -> None:
    result = run_required_e_validation()
    summary = {key: value for key, value in result.items() if key != "required_rows"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
