#!/usr/bin/env python3

# Here we inform python to search for dependencies
# on this project
from pathlib import Path
import sys
import os

root = Path(__file__).parents[1].absolute()
deps = Path(root.joinpath('deps')).absolute()
libs = Path(root.joinpath('lib')).absolute()

sys.path.append(str(root))  # Project root dir
sys.path.append(str(deps))  # Python dependencies
sys.path.append(str(libs))  # Binary dependencies

# Here we ask python to load all binary libraries
# before starting to import modules, so when the
# modules get loaded they will be already available.
# This is the same effect that exporting LD_LIBRARY_PATH
# before calling this script, but since we cannot do this
# on Canary environment, we have to do it manually.
from ctypes import cdll

dynamic_libs = [
    'libc.so.6',
    'libcom_err.so.2',
    'libcrypt.so.1',
    'libcrypto.so.10',
    'libdl.so.2',
    'libgssapi_krb5.so.2',
    'libk5crypto.so.3',
    'libkeyutils.so.1',
    'libkrb5.so.3',
    'libkrb5support.so.0',
    'liblber-2.4.so.2',
    'libldap_r-2.4.so.2',
    'libnspr4.so',
    'libnss3.so',
    'libnssutil3.so',
    'libpcre.so.1',
    'libplc4.so',
    'libplds4.so',
    'libpq.so.5',
    'libpthread.so.0',
    'libresolv.so.2',
    'librt.so.1',
    'libsasl2.so.3',
    'libselinux.so.1',
    'libsmime3.so',
    'libssl.so.10',
    'libssl3.so',
    'libz.so.1',
]

for lib in dynamic_libs:
    full_path = '{lib_dir}/{lib_name}'.format(
        lib_dir=libs,
        lib_name=lib
    )

    cdll.LoadLibrary(full_path)

# Now let's start our real work!!!

# from aws_synthetics.common import synthetics_logger as logger
import psycopg2


def main(credentials):
    print(
        'Connecting to postgres server at: "{}:{}"...'.format(
            credentials['db_host'],
            credentials['db_port'],
        )
    )

    cursor = psycopg2.connect(
        host=credentials['db_host'],
        port=credentials['db_port'],
        database=credentials['db_name'],
        user=credentials['db_user'],
        password=credentials['db_pass'],
    ).cursor()

    res = cursor.execute('SELECT version()')
    print('I got db info: {}'.format(cursor.fetchone()))

    cursor.close()


def get_credentials():
    return {
        'db_host': str(os.environ['DB_HOST']),
        'db_port': int(os.environ['DB_PORT']),
        'db_user': str(os.environ['DB_USER']),
        'db_pass': str(os.environ['DB_PASS']),
        'db_name': str(os.environ['DB_NAME']),
    }


def handler(event, context):
    print('Starting Postgres Canary')

    credentials = get_credentials()

    return main(credentials)

handler(1,2)