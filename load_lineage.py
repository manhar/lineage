#!/usr/bin/env python3
"""Convenience root wrapper for scripts/load_lineage.py"""
import sys
import runpy
from pathlib import Path

script_path = Path(__file__).parent / "scripts" / "load_lineage.py"
runpy.run_path(str(script_path), run_name="__main__")
