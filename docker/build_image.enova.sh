#!/bin/bash

set -x
IMAGE_VERSION=v`cat VERSION`

echo "Runing build image enova:${IMAGE_VERSION} using ${PWD}"

SCRIPT=$(realpath "$0")
BASEDIR=$(dirname "$SCRIPT")
BASEDIR=$(dirname "$BASEDIR")
echo "BASEDIR: " ${BASEDIR}

# build src/front
cd $BASEDIR/src/front
rm $BASEDIR/enova/web_statics -rf
npm install
npm run build
# yarn
# yarn build

echo $BASEDIR/src/front/dist $BASEDIR/enova/web_statics
mv $BASEDIR/src/front/dist $BASEDIR/enova/web_statics

export HARBOR_PATH=dev-harbor.emergingai.inner.com/emergingai
export MIRROR_PATH=emergingai

# build enova
cd $BASEDIR
docker build -f $BASEDIR/docker/Dockerfile.enova -t $HARBOR_PATH/enova:$IMAGE_VERSION --build-arg HARBOR_PATH="$HARBOR_PATH" --build-arg CACHEBUST=$(date +%s) $BASEDIR

docker tag $HARBOR_PATH/enova:$IMAGE_VERSION  $MIRROR_PATH/enova:$IMAGE_VERSION