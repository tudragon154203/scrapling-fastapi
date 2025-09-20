#!/usr/bin/env python3
"""Print the canonical opencode model identifier."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from model_utils import canonicalize_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", help="Model identifier to normalize.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(canonicalize_model(args.model))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

