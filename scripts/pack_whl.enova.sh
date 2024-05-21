#!/bin/bash

set -x
echo "Runing packing wheel using ${PWD}"

SCRIPT=$(realpath "$0")
BASEDIR=$(dirname "$SCRIPT")
BASEDIR=$(dirname "$BASEDIR")


# pack
cd $BASEDIR
python -m build --no-isolation

