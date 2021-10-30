#!/usr/bin/env python3


# Getting absolute paths to our project
from pathlib import Path
import sys

root = Path(__file__).parents[1].absolute()
deps = Path(root.joinpath('deps')).absolute()
libs = Path(root.joinpath('libs')).absolute()

# Adding 'deps' to path where python look for modules
sys.path.append(str(deps))


# Importing binary libraries manually
from ctypes import cdll

cdll.LoadLibrary(f'{libs}/libpq.so.5')


# Our actual code
import psycopg2

print('psycopg2 imported successfully')
