#!/usr/bin/env python3

from pathlib import Path
import sys
import os

root = Path(__file__).parents[1].absolute()
deps = Path(root.joinpath('deps')).absolute()
libs = Path(root.joinpath('libs')).absolute()

sys.path.append(str(deps))

os.environ['LD_LIBRARY_PATH'] = str(libs)

import psycopg2

print('psycopg2 imported successfully')
