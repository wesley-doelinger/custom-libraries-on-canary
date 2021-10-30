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

dynamic_libs = [
    'ld-linux-x86-64.so.2',
    'libpcre.so.1',
    'libselinux.so.1',
    'libcrypt.so.1',
    'libkeyutils.so.1',
    'libkrb5support.so.0',
    'libresolv.so.2',
    'librt.so.1',
    'libdl.so.2',
    'libk5crypto.so.3',
    'liblber-2.4.so.2',
    'libnspr4.so',
    'libnss3.so',
    'libnssutil3.so',
    'libplc4.so',
    'libplds4.so',
    'libsasl2.so.3',
    'libsmime3.so',
    'libssl3.so',
    'libz.so.1',
    'libcom_err.so.2',
    'libcrypto.so.10',
    'libgssapi_krb5.so.2',
    'libkrb5.so.3',
    'libldap_r-2.4.so.2',
    'libssl.so.10',
    'libc.so.6',
    'libpq.so.5',
    'libpthread.so.0',
]

for lib in dynamic_libs:
    full_path = '{lib_dir}/{lib_name}'.format(
        lib_dir=libs,
        lib_name=lib
    )

    cdll.LoadLibrary(full_path)


# Our actual code
from aws_synthetics.common import synthetics_logger as logger
import psycopg2


def handler(event, context):
    logger.info('Starting Postgres Canary')

    return 0
