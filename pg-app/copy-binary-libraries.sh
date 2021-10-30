#!/bin/bash

## Finding all dynamic libraries on our local deps/ dir
PYTHON_DYN_LIBS=$(find deps -iname "*.so*")

## Getting filenames
FILENAMES=$(lddtree $PYTHON_DYN_LIBS | grep '  ' | sort | awk '{ print $3 }' | awk '!x[$0]++')

mkdir -p libs/

echo -e "\nCopying files to libs/...\n"

for FILE in $FILENAMES;
do
  cp -v $FILE libs/
done;

echo -e "\nGenerating ordered python list...\n"

for FILE in $FILENAMES;
do
  NAME=$(echo $FILE | cut -f3 -d '/')
  echo "'$NAME',"
done;
