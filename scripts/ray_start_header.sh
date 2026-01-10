if [ -z ${SYSTEM_CONFIG} ]; then
    export SYSTEM_CONFIG='{}'
fi

if [ $USE_HOSTIP == "true" ]; then
    echo "use hostip"
    ray start --node-ip-address=$NODE_IP --num-cpus=$CPU_NUM --num-gpus=$GPU_NUM
        --address=$HEADER_HOST:$HEADER_PORT --object-manager-port=$OBJECT_MANAGER_PORT \
        --node-manager-port=$NODE_MANAGER_PORT \
        --worker-port-list=$WORKER_PORT_LIST --include-dashboard=1 --dashboard-port=$DASHBOARD_PORT --dashboard-host=0.0.0.0 \
        --temp-dir=$TEMP_DIR --system-config="$SYSTEM_CONFIG"
else
    echo "use podip"
    ray start --head --num-cpus=$CPU_NUM --num-gpus=$GPU_NUM --port=$HEADER_PORT --object-manager-port=8076 --node-manager-port=8077 \
        --include-dashboard=True --dashboard-port=$DASHBOARD_PORT --dashboard-host=0.0.0.0 --temp-dir=$TEMP_DIR --system-config="$SYSTEM_CONFIG"
fi

python header_run.py > header_run.log 2>&1 &
tail -f header_run.log
sleep infinity
