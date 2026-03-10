#!/usr/bin/env python
import os
import sys

# Ensure the antigravity package is heavily prioritized in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from cli.runner import main_runner

if __name__ == "__main__":
    main_runner()
