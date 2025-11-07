while true
do
    if [ $USE_HOSTIP == "true" ]; then
        echo "use hostip"
        ray start --node-ip-address=$NODE_IP --num-cpus=$CPU_NUM --num-gpus=$GPU_NUM \
            --address=$HEADER_HOST:$HEADER_PORT --object-manager-port=$OBJECT_MANAGER_PORT \
            --node-manager-port=$NODE_MANAGER_PORT \
            --worker-port-list=$WORKER_PORT_LIST --temp-dir=$TEMP_DIR --block
    else
        echo "use podip"
        ray start --num-cpus=$CPU_NUM --num-gpus=$GPU_NUM --address=$HEADER_HOST:$HEADER_PORT --object-manager-port=8076 --node-manager-port=8077 --temp-dir=$TEMP_DIR --block
    fi
    echo "ray worker stop unpectedly, restart it"
done
sleep infinity

