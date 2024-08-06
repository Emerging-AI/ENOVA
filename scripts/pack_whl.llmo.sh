#!/bin/bash

set -x
echo "Runing packing wheel of llmo using ${PWD}"

SCRIPT=$(realpath "$0")
BASEDIR=$(dirname "$SCRIPT")
BASEDIR=$(dirname "$BASEDIR")

# pack
cd $BASEDIR/llmo/enova-instrumentation-llmo
poetry build
