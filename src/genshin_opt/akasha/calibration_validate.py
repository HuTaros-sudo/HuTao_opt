"""Homa R1 empirical calibrationのLeave-One-Out検証CLI。"""

import json

from .calibration import run_homa_calibration_validation


def main() -> None:
    result = run_homa_calibration_validation()
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
