
# 确保 POD_NAME 环境变量已设置
if [ -z "${POD_NAME}" ]; then
  echo "错误：POD_NAME 环境变量未设置。"
  exit 1
fi

# 使用Bash参数扩展功能，从POD_NAME的末尾解析出序号
# ${POD_NAME##*-} 的意思是：从POD_NAME变量中，移除从开头到最后一个'-'的所有内容
INDEX=${POD_NAME##*-}

echo "当前Pod名称: ${POD_NAME}"
echo "解析出的序号: ${INDEX}"

export RAY_NODE_IP_ADDRESS=${POD_NAME}.vllm-multi-node-svc-headless
export RAY_OVERRIDE_NODE_IP_ADDRESS=${POD_NAME}.vllm-multi-node-svc-headless

if [ -z ${SYSTEM_CONFIG} ]; then
    export SYSTEM_CONFIG='{}'
fi

if [[ "${INDEX}" == "0" ]]; then
    # 这是第一个Pod (主节点)
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

    sleep 10
    export export RAY_ADDRESS=${RAY_NODE_IP_ADDRESS}:6379
    # enova serving run $@

else
    # 这是其他Pod (副本节点)
    echo "检测到序号为 ${INDEX} (非0)，将执行副本节点（Replica）的任务..."

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
fi
sleep infinity

