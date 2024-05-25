import datetime
import html
import json
import os
from typing import Dict

import numpy as np
import pandas as pd
import pytz
from sqlalchemy import func, select
from tzlocal import get_localzone

from enova.algo.service import LLMConfig
from enova.api.enode_api import EnodeApi
from enova.api.escaler_api import EScalerApiWrapper
from enova.api.prom_api import PromApi
from enova.app.db_modles import DeploymentInstanceInfoTable, TestInfoTable
from enova.app.utils import compute_actual_duration
from enova.common.config import CONFIG
from enova.common.constant import (
    DeployStatus,
    Distribution,
    TestStatus,
    TrafficDistributionType,
)
from enova.common.error import (
    BackendConfigMissingError,
    DeploymentInstanceCreateFailedError,
    DeploymentInstanceExistError,
    DeploymentInstanceNotExistError,
    JmeterContainerLaunchError,
    TestNotExistError,
    TestStartError,
)
from enova.common.logger import LOGGER
from enova.common.utils import gen_ulid, get_machine_spec, short_uuid, tokenize_size
from enova.database.relation.transaction.session import get_async_session
from enova.enode.utils import hf_model_params_size
from enova.server.restful.service import BaseApiService


class TestActionHandler:
    @staticmethod
    def build_req_body(param_spec):
        body = {
            "prompt": "${question}",
            "max_tokens": param_spec["max_tokens"],
            "temperature": param_spec["temperature"],
            "top_p": param_spec["top_p"],
        }

        # others param format: k1:v1,k2:v2,...
        if param_spec["others"]:
            for pair in param_spec["others"].split(","):
                k, v = pair.split(":")
                body[k] = v

        body_json_str = json.dumps(body)
        return html.escape(body_json_str)

    def start(self, host, port, test_info):
        from enova.entry.command.injector import TrafficInjector

        test_spec = test_info["test_spec"]
        if test_spec["distribution"] == TrafficDistributionType.GAUSSIAN.value:
            timer = {"type": Distribution.NORMAL.value, "mean": test_spec["tps_mean"], "std": test_spec["tps_std"]}
        elif test_spec["distribution"] == TrafficDistributionType.POISSON.value:
            timer = {"type": Distribution.POISSON.value, "lambda": test_spec["tps_mean"]}
        else:
            distribution = test_spec["distribution"]
            LOGGER.exception(f"distribution {distribution} not allow.")
            raise NotImplementedError()

        param_spec = test_info["param_spec"]

        try:
            TrafficInjector().run(
                host=host,
                port=port,
                path="/generate",
                method="post",
                duration=compute_actual_duration(test_spec["duration"], test_spec["duration_unit"]),
                timer=timer,
                data=test_spec["data_set"],
                body=self.build_req_body(param_spec),
                headers="Content-Type:application/json",
                output=test_info["test_id"],
                container_name="enova-traffic-injector-" + test_info["test_id"],
            )
            return True
        except JmeterContainerLaunchError:
            return False

    @staticmethod
    def build_test_result(file_path):
        # total = 0
        # success = 0
        # elapsed = []
        pdf = pd.read_csv(file_path)
        return {"total": len(pdf), "success": sum(pdf.success), "elasped_avg": pdf.elapsed.mean()}

    @staticmethod
    async def build_model_metric(test_info: TestInfoTable):
        local_tz = get_localzone()
        start_time = datetime.datetime.fromisoformat(test_info.create_time).replace(tzinfo=local_tz)
        utc_start_time = start_time.astimezone(pytz.utc)
        end_time = utc_start_time + datetime.timedelta(
            seconds=max(
                60, compute_actual_duration(test_info.test_spec["duration"], test_info.test_spec["duration_unit"])
            )
        )

        start = int(start_time.timestamp())
        end = int(end_time.timestamp())
        # TODO: modify prom sql
        generation_tps_query = "avg by(exported_job) (avg_generation_throughput_tokens_per_second)"
        prompt_tps_query = "avg by(exported_job) (avg_prompt_throughput_tokens_per_second)"

        generation_tps_query_ret = await PromApi.query_range(
            {
                "query": generation_tps_query,
                "start": start,
                "end": end,
                "step": CONFIG.enova_app["prom_time_step"],
            }
        )
        prompt_tps_query_ret = await PromApi.query_range(
            {
                "query": prompt_tps_query,
                "start": start,
                "end": end,
                "step": CONFIG.enova_app["prom_time_step"],
            }
        )

        return {
            "generation_tps": 0
            if not generation_tps_query_ret
            else int(TestActionHandler.compute_metric_avg(generation_tps_query_ret)),
            "prompt_tps": 0
            if not prompt_tps_query_ret
            else int(TestActionHandler.compute_metric_avg(prompt_tps_query_ret)),
        }

    @staticmethod
    def compute_metric_avg(prom_ret: Dict):
        if prom_ret.get("status") != "success":
            LOGGER.info(f"prom_ret response not success, prom_ret: {prom_ret}")
            return 0
        if not prom_ret["data"]["result"]:
            LOGGER.info(f"prom_ret response get no data, prom_ret: {prom_ret}")
        # flatten all result
        # remove all zero disturbed data
        values = []
        for r in prom_ret["data"]["result"]:
            if not all(float(v[1]) == 0 for v in r["values"]):
                for v in r["values"]:
                    values.append(float(v[1]))
        return np.average(values) if values else 0

    @staticmethod
    async def update_test_info_when_finish(test_info: TestInfoTable):
        test_id = test_info.test_id
        cache_dir = os.path.join(CONFIG.traffic_injector["cache_dir"], test_id)
        report_dir = os.path.join(cache_dir, "report")
        os.makedirs(report_dir, exist_ok=True)

        test_status = TestStatus.SUCCESS.value
        if not os.listdir(report_dir):
            test_status = TestStatus.FAILED.value

        test_result = TestActionHandler.build_test_result(os.path.join(report_dir, "report.log"))
        model_metric = await TestActionHandler.build_model_metric(test_info)
        test_info.test_status = test_status
        test_info.result = test_result
        test_info.prompt_tps = model_metric["prompt_tps"]
        test_info.generation_tps = model_metric["generation_tps"]
        return test_info

    @staticmethod
    async def update_metrics(test_info: TestInfoTable):
        model_metric = await TestActionHandler.build_model_metric(test_info)
        test_info.prompt_tps = model_metric["prompt_tps"]
        test_info.generation_tps = model_metric["generation_tps"]
        return test_info


class PilotActionHandler:
    def __init__(self) -> None:
        self.escaler_api = EScalerApiWrapper()

    def form_envs(self):
        # TODO: get CUDA_VISIBLE_DEVICES in os.envs or contaienr's os.envs
        enode_envs = []

        hf_proxy = CONFIG.enova_app.get("hf_proxy")
        # TODO: It shouldn't be set hf_proxy to env proxy in container, it will mess named nework' dns in docker-compose
        if hf_proxy:
            enode_envs += [
                {
                    "name": "http_proxy",
                    "value": hf_proxy,
                },
                {
                    "name": "https_proxy",
                    "value": hf_proxy,
                },
                {
                    "name": "no_proxy",
                    "value": "otel-collector,enova-escaler,enova-prometheus,enova-enode,grafana,dcgm-exporter,tempo,enova-app,enova-escaler,enova-algo,localhost,127.0.0.1",
                },
            ]
        return enode_envs

    def form_volumes(self):
        volume_lst = [
            {
                "hostPath": "/root/.cache",
                "mountPath": "/root/.cache",
            },
        ]

        host_model_dir = CONFIG.enova_app.get("host_model_dir")
        if host_model_dir:
            volume_lst += [
                {
                    "hostPath": host_model_dir,
                    "mountPath": CONFIG.enova_app.get("model_dir"),
                }
            ]

        return volume_lst

    async def deploy_enode(self, instance_info):
        user_args = CONFIG.get_user_args()

        model_config = instance_info["model_cfg"]
        llm_config = {
            "framework": model_config["model_type"],
            "param": model_config["param"],
        }

        gpu_spec = instance_info["instance_spec"].get("gpu")
        gpu_config = {
            "name": gpu_spec["product"],
            "spec": tokenize_size(gpu_spec["video_memory"])[0],
            "num": gpu_spec["card_amount"],
        }

        serving_args = CONFIG.serving
        for k in serving_args.keys():
            serving_k = f"serving_{k}"
            if serving_k in user_args.keys():
                serving_args[k] = user_args[serving_k]

        backend = serving_args["backend"]  # TODO: extern more backends
        backendConfig = getattr(CONFIG, backend)
        if not backendConfig:
            raise BackendConfigMissingError()

        for k in backendConfig.keys():
            if k in user_args.keys():
                backendConfig[k] = user_args[k]

        llmo_args = CONFIG.llmo
        for k in llmo_args.keys():
            if k in user_args.keys():
                llmo_args[k] = user_args[k]

        enode_info = {
            "backend": backend,
            "backendConfig": backendConfig,
            "envs": self.form_envs(),
            "exporter_endpoint": llmo_args["eai_exporter_endpoint"],
            "exporter_service_name": llmo_args["eai_exporter_service_name"],
            "host": serving_args["host"],
            "model": model_config["model_name"],
            "modelConfig": {
                "gpu": gpu_config,
                "llm": llm_config,
                "version": short_uuid(4),
            },
            "name": instance_info["enode_id"],
            "port": serving_args["port"],
            "replica": serving_args["replica"],
            "volumes": self.form_volumes(),
        }
        instance_info_extra = instance_info.get("extra", {})
        instance_info_extra["create_deploy_payload"] = enode_info
        try:
            ret = await self.escaler_api.create_deploy(enode_info)
            instance_info_extra["create_deploy_return"] = ret

        except Exception as e:
            LOGGER.error(f"call enode api 'deploy_enode' failed: Error {e}")
            return None

        instance_info["extra"] = instance_info_extra
        return instance_info

    async def check_enode(self, instance_info):
        pass  # TODO

    async def sync_enode_status(self, instance_info: Dict):
        instance_info_extra = instance_info.extra or {}
        try:
            # TODO:
            get_deploy_ret = await self.escaler_api.get_deploy(
                {
                    "task_name": instance_info.enode_id,
                }
            )
            instance_info_extra["get_deploy_ret"] = get_deploy_ret
            LOGGER.info(f"sync_enode_status get_deploy_ret: {get_deploy_ret}")
            engine_args = await EnodeApi.engine_args(params={})
            LOGGER.info(f"engine_args: {engine_args}")

            if get_deploy_ret.get("ret", {}).get("result", {}).get("status"):
                get_deploy_status = get_deploy_ret["ret"]["result"]["status"]
                instance_info.deploy_status = get_deploy_status  # TODO: convert to DeployStatus's value
                task_spec = get_deploy_ret["ret"]["result"]["task_spec"]

                startup_args = {
                    "exported_job": task_spec.get("exporter_service_name"),
                    "dtype": engine_args.get("dtype"),
                    "load_format": engine_args.get("load_format"),
                    "max_num_batched_tokens": task_spec.get("max_num_batched_tokens"),
                    "max_num_seqs": engine_args.get("max_num_seqs"),
                    "max_paddings": engine_args.get("max_paddings"),
                    "max_seq_len": engine_args.get("max_seq_len") or engine_args.get("max_model_len"),
                    "model": engine_args.get("model"),
                    "tokenizer": engine_args.get("tokenizer"),
                    "pipeline_parallel_size": engine_args.get("pipeline_parallel_size"),
                    "tensor_parallel_size": engine_args.get("tensor_parallel_size"),
                    "quantization": engine_args.get("quantization"),
                    "engine_args": engine_args,
                }
                instance_info.startup_args = startup_args

            else:
                instance_info.deploy_status = DeployStatus.UNKNOWN.value
            instance_info.extra = instance_info_extra
        except Exception as e:
            LOGGER.exception(f"call enode api 'sync_enode_status' failed: Error {e}")

        return instance_info

    async def shutdown_enode(self, instance_info: Dict):
        instance_info_extra = instance_info.extra or {}
        LOGGER.info(f"start shutdown enode: {instance_info}")
        try:
            delete_deploay_ret = await self.escaler_api.delete_deploy(
                {
                    "task_name": instance_info.enode_id,
                }
            )
            instance_info_extra["delete_deploay_ret"] = delete_deploay_ret
            instance_info.is_deleted = 1
            instance_info.deploy_status = DeployStatus.FINISHED.value
            instance_info.extra = instance_info_extra
        except Exception as e:
            LOGGER.exception(f"call enode api failed: Error {e}")
            return None

        return instance_info


class AppService(BaseApiService):
    """"""

    START_TIME_FIELD = "update_time"
    END_TIME_FIELD = "update_time"

    def __init__(self) -> None:
        self.pilot_handler = PilotActionHandler()
        self.test_handler = TestActionHandler()

    async def create_instance(self, params):
        await self.check_enode_existed()

        # TODO: use no_proxy, no need to pass proxies in hf's api
        hf_proxy = CONFIG.enova_app.get("hf_proxy")
        if hf_proxy:
            user_hf_proxies = {
                "http": hf_proxy,
                "https": hf_proxy,
            }
        else:
            user_hf_proxies = None

        model = params["model"]
        # host_model_dir existed, this mean enova-app run in container
        # TODO: maybe mess by host env vars, when run in host
        host_model_dir = CONFIG.enova_app.get("host_model_dir")
        if host_model_dir:
            model = CONFIG.enova_app.get("model_dir")

        model_params = hf_model_params_size(model, hf_proxies=user_hf_proxies)
        model_params["model_name"] = model
        model_params["param"] = int(round(model_params.get("params_size", 0) / 10**9, ndigits=0))

        llm_config = LLMConfig()
        model_params["llm_config"] = llm_config.LLM_CONFIG.get(model_params["model_name"], {}).get(
            model_params["param"], {}
        )
        model_params["default_config"] = llm_config.DEFAULT_CONFIG.get(model_params["param"], {})
        # model_params = {}
        host_spec = get_machine_spec()

        instance_info = {
            "instance_name": params["instance_name"],
            "instance_spec": host_spec,
            "startup_args": {},  # #TODO: polit startup args all in CONFIG
            "model_cfg": model_params,
            "creator": params["creator"],
        }
        instance_info["creator"] = (
            instance_info.get("creator")
            or params.get("instance_spec", {}).get("hostname")
            or params.get("instance_spec", {}).get("host_ip")
            or "unknown"
        )
        instance_info["updater"] = instance_info["creator"]
        instance_info["enode_id"] = gen_ulid()

        async with get_async_session() as async_session:
            instance_info = await self.pilot_handler.deploy_enode(instance_info)

            if not instance_info:
                raise DeploymentInstanceCreateFailedError()

            instance_info_orm = DeploymentInstanceInfoTable(**instance_info)
            async_session.add(instance_info_orm)

            await async_session.flush()

            instance_info = instance_info_orm.dict
        return instance_info

    async def check_enode_existed(self):
        async with get_async_session() as async_session:
            smt = select(DeploymentInstanceInfoTable).filter(
                DeploymentInstanceInfoTable.deploy_status.in_(
                    [
                        DeployStatus.RUNNING.value,
                        DeployStatus.PENDING.value,
                        DeployStatus.FAILED.value,
                        DeployStatus.UNKNOWN.value,
                    ]
                ),
                DeploymentInstanceInfoTable.is_deleted == 0,
            )
            c = await async_session.scalar(select(func.count()).select_from(smt))
            if c > 0:
                raise DeploymentInstanceExistError("cannot redeploy model")

    async def list_instance(self, params: Dict):
        """"""
        # no_pager
        # TODO: build filter by params
        # filter_conditions = []  #
        query = (
            select(DeploymentInstanceInfoTable)
            .filter(
                DeploymentInstanceInfoTable.is_deleted == 0,
            )
            .order_by(DeploymentInstanceInfoTable.create_time.desc())
        )
        data = []
        async with get_async_session() as async_session:
            query_result = await async_session.execute(query)
            for instance_info in query_result:
                instance_info = instance_info[0]
                instance_info = await self.pilot_handler.sync_enode_status(instance_info)
                await async_session.merge(instance_info)
                await async_session.flush()

                data.append(instance_info.dict)
        return {"data": data}

    async def delete_instance(self, instance_id):
        """"""
        query = select(DeploymentInstanceInfoTable).filter(
            DeploymentInstanceInfoTable.instance_id == instance_id,
            DeploymentInstanceInfoTable.is_deleted == 0,
        )
        async with get_async_session() as async_session:
            query_result = await async_session.execute(query)
            instance_info = query_result.first()

            if not instance_info:
                raise DeploymentInstanceNotExistError()

            instance_info = instance_info[0]
            instance_info = await self.pilot_handler.shutdown_enode(instance_info)
            if instance_info is None:
                return "failed"

            await async_session.merge(instance_info)
            await async_session.flush()

        return "success"

    async def delete_instance_by_name(self, instance_name):
        """"""
        query = select(DeploymentInstanceInfoTable).filter(
            DeploymentInstanceInfoTable.instance_name == instance_name,
            DeploymentInstanceInfoTable.is_deleted == 0,
        )
        async with get_async_session() as async_session:
            query_result = await async_session.execute(query)
            for instance_info in query_result:
                instance_info = instance_info[0]
                instance_info = await self.pilot_handler.shutdown_enode(instance_info)
                if instance_info is None:
                    continue

                # SQLite DateTime type only accepts Python datetime and date objects as input
                await async_session.merge(instance_info)
                await async_session.flush()

        return "success"

    async def get_instance(self, instance_id):
        """"""
        query = select(DeploymentInstanceInfoTable).filter(
            DeploymentInstanceInfoTable.instance_id == instance_id,
            DeploymentInstanceInfoTable.is_deleted == 0,
        )
        async with get_async_session() as async_session:
            query_result = await async_session.execute(query)
            instance_info = query_result.first()

            if not instance_info:
                raise DeploymentInstanceNotExistError()

            instance_info = instance_info[0]
            instance_info = await self.pilot_handler.sync_enode_status(instance_info)

            await async_session.merge(instance_info)
            await async_session.flush()

            instance_info_dct = instance_info.dict
        return instance_info_dct

    async def list_test(self, params: Dict):
        from enova.entry.command.injector import TrafficInjector

        ret = await self.common_list(
            params, TestInfoTable, fuzzy_field_list=["data_set", "test_status", "creator", "updater"]
        )
        async with get_async_session() as async_session:
            for datum in ret["data"]:
                # Sync Docker-compose
                if datum["test_status"] == TestStatus.RUNNING.value:
                    test_id = datum["test_id"]
                    tj = TrafficInjector()
                    test_status = tj.status(test_id)
                    test_info = TestInfoTable(**datum)
                    if test_status == "exited" or test_status is None:
                        # collect the job
                        tj.stop()
                        test_info = await self.test_handler.update_test_info_when_finish(test_info)
                        await async_session.merge(test_info)
                        await async_session.flush()

                elif datum["test_status"] == TestStatus.SUCCESS.value:
                    test_info = TestInfoTable(**datum)
                    test_info = await self.test_handler.update_test_info_when_finish(test_info)
                    await async_session.merge(test_info)
                    await async_session.flush()

        return ret

    async def create_test(self, params: Dict):
        test_id = gen_ulid()
        test_info = {
            "test_id": test_id,
            "instance_id": params["instance_id"],
            "test_spec": params["test_spec"],
            "param_spec": params["param_spec"],
            "test_status": TestStatus.INIT.value,
            "data_set": params["test_spec"]["data_set"],
            "result": {},
            "creator": params.get("creator") or "unknown",
        }

        instance_info = await self.get_instance(params["instance_id"])
        if instance_info["deploy_status"] != DeployStatus.RUNNING.value:
            raise TestStartError(f"instance: {params['instance_id']} is not running")
        async with get_async_session() as async_session:
            smt = select(TestInfoTable).filter(
                TestInfoTable.test_status.in_(
                    [TestStatus.INIT.value, TestStatus.RUNNING.value, TestStatus.UNKNOWN.value]
                )
            )
            c = await async_session.scalar(select(func.count()).select_from(smt))
            if c > 0:
                raise TestStartError("test is running, please wait for finished")

            # TODO: just one local enode service
            success = self.test_handler.start(
                CONFIG.traffic_injector["default_enode_host"],
                instance_info["extra"]["create_deploy_payload"]["port"],
                test_info,
            )
            if not success:
                raise TestStartError(f"instance_id: {params['instance_id']} start failed")

            test_info["test_status"] = TestStatus.RUNNING.value
            async_session.add(TestInfoTable(**test_info))
            await async_session.flush()
        return test_info

    async def delete_test(self, test_id):
        """"""
        from enova.entry.command.injector import TrafficInjector

        query = select(TestInfoTable).filter(TestInfoTable.test_id == test_id)
        async with get_async_session() as async_session:
            query_result = await async_session.execute(query)
            test_info = query_result.first()

            if not test_info:
                raise TestNotExistError()
            tj = TrafficInjector()
            tj.stop()
            await async_session.delete(test_info)
        return True

    async def get_test(self, test_id):
        """"""
        from enova.entry.command.injector import TrafficInjector

        query = select(TestInfoTable).filter(TestInfoTable.test_id == test_id)
        async with get_async_session() as async_session:
            query_result = await async_session.execute(query)
            test_info = query_result.first()

            if not test_info:
                raise TestNotExistError()
            test_info = test_info[0]
            if test_info.test_status == TestStatus.RUNNING.value:
                # Sync Docker-compose
                tj = TrafficInjector()
                test_status = tj.status(test_id)
                if test_status == "exited" or test_status is None:
                    # collect the job
                    tj.stop()
                    # update result
                    await self.test_handler.update_test_info_when_finish(test_info)

                    await async_session.merge(test_info)
                    await async_session.flush()
                elif test_status == TestStatus.SUCCESS.value:
                    # Prom metric may have some delayed
                    if not test_info.prompt_tps or not test_info.generation_tps:
                        await self.test_handler.update_metrics(test_info)
                        await async_session.merge(test_info)
                        await async_session.flush()
            test_info_dict = test_info.dict
        return test_info_dict
