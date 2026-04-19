#!/usr/bin/env python3
"""Backward-compatible wrapper for the new dev reset script."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reset_dev_data import main


if __name__ == "__main__":
    print("Note: scripts/clean_test_data.py is deprecated; use scripts/reset_dev_data.py.", file=sys.stderr)
    raise SystemExit(main())
