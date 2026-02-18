#!/usr/bin/env python3
"""兼容旧调用方式：python cli.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from money_get.main import cli


if __name__ == "__main__":
    cli()
