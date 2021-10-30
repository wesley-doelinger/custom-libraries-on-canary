#!/usr/bin/env python3

# Here we inform python to search for dependencies
# on this project
from pathlib import Path
import sys
import os

root = Path(__file__).parents[1].absolute()
deps = Path(root.joinpath('deps')).absolute()

sys.path.append(str(deps))  # Python dependencies

# Now let's start our real work!!!

from aws_synthetics.common import synthetics_logger as logger
import requests


def main(breed):
    logger.info('Getting a dog...')

    try:
        uri = f'https://dog.ceo/api/breed/{breed}/images/random'
        res = requests.get(uri)

        if res.status_code == 200:
            logger.info(res.json()['message'])
        else:
            raise Exception(res)

    except Exception as e:
        logger.error(e)

    return 0


def handler(event, context):
    logger.info('Starting Dogs Canary')

    breed = os.environ['BREED']

    return main(breed)
