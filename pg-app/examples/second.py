#!/usr/bin/env python3

from pathlib import Path
import sys

root = Path(__file__).parents[1].absolute()
deps = Path(root.joinpath('deps')).absolute()

sys.path.append(str(deps))

import psycopg2

print('psycopg2 imported successfully')
