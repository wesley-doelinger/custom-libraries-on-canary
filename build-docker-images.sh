#!/bin/bash

docker build -t amz-builder -f Dockerfile.amz-builder .

docker build -t amz-runner -f Dockerfile.amz-runner .