import json
import sys
import click
import os

from enova.common.cli_helper import ArgumentHelper, DockerComposeHeler, EnumType, parse_extra_args
from enova.common.config import CONFIG
from enova.common.constant import DeployMode
from enova.common.logger import LOGGER


class EnovaApp:
    def __init__(self, deploy_mode: DeployMode = DeployMode.LOCAL.value) -> None:
        self._svc_name = "enova-app"
        self._docker_compose = DockerComposeHeler()
        self._deploy_mode = deploy_mode

    def _run_local(self, host, port):
        import uvicorn

        from enova.app.server import get_app_api_server

        api_server = get_app_api_server()
        uvicorn.run(api_server.app, host=host, port=port)

    def _run_compose(self, host, port, restart=False):
        """
        - first stop svc
        - update svc options
        - start up svc
        """
        if restart:
            self._docker_compose.stop_service(self._svc_name)

        svc_cmd = ["enova", "app", "run", "--host", host, "--port", port]
        environment_lst = self._docker_compose.get_service_option(self._svc_name, "environment") or []
        volumes_lst = self._docker_compose.get_service_option(self._svc_name, "volumes") or []

        def check_local_model_dir(dir_path):
            if os.path.isabs(dir_path):
                if not os.path.exists(dir_path):
                    raise FileNotFoundError(f"Directory not found: {dir_path}")
                if not os.path.isdir(dir_path):
                    raise FileNotFoundError(f"{dir_path} is a Directory")
                return True
            else:
                maybe_rel = os.path.abspath(dir_path)
                if os.path.exists(maybe_rel) and os.path.isdir(maybe_rel):
                    return True

            return False

        if isinstance(environment_lst, list):
            user_args = CONFIG.get_user_args()
            if "hf_proxy" in user_args.keys() and user_args["hf_proxy"]:
                hf_proxy = user_args["hf_proxy"]
                environment_lst.append(f"EMERGINGAI_ENOVA_APP_HF_PROXY={hf_proxy}")

            if "model" in user_args.keys() and user_args["model"]:
                model_dir = user_args["model"]
                if check_local_model_dir(model_dir):
                    model_dir = os.path.abspath(model_dir)
                    environment_lst.append(f"EMERGINGAI_ENOVA_APP_HOST_MODEL_DIR={model_dir}")
                    volumes_lst.append(f"{model_dir}:{CONFIG.enova_app['model_dir']}")
                    LOGGER.info(f"use local model: {model_dir}")
                    LOGGER.debug(f"maping local model in compose: {CONFIG.enova_app['model_dir']}")
                else:
                    LOGGER.info(f"use remote model: {model_dir}")

            environment_lst.append("EMERGINGAI_ENOVA_APP_USER_ARGS=" + json.dumps(user_args))

        # traffic inject setup
        os.makedirs(CONFIG.traffic_injector["cache_dir"], exist_ok=True)
        os.makedirs(CONFIG.traffic_injector["dataset_host_dir"], exist_ok=True)
        volumes_lst.extend(
            [
                f"{CONFIG.traffic_injector['cache_dir']}:{CONFIG.traffic_injector['cache_dir']}",
                f"{CONFIG.traffic_injector['dataset_dir']}:{CONFIG.enova_app['dataset_dir_container']}",
            ]
        )

        options = {
            "command": " ".join([str(cmd) for cmd in svc_cmd]),
            "environment": environment_lst,
            "volumes": volumes_lst,
        }

        self._docker_compose.update_service_options(self._svc_name, options)
        self._docker_compose.startup_service(self._svc_name, is_daemon=True)

    def run(self, host, port, restart=False, **kwargs):
        args_helper = ArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        if self._deploy_mode in [DeployMode.LOCAL.value]:
            self._run_local(host=host, port=port)

        elif self._deploy_mode in [DeployMode.COMPOSE.value]:
            self._run_compose(host=host, port=port, restart=restart)

        else:
            raise NotImplementedError()

    def _stop_compose(self):
        self._docker_compose.stop_service(self._svc_name)

    def stop(self):
        if self._deploy_mode in [DeployMode.LOCAL.value]:
            return NotImplemented
        elif self._deploy_mode in [DeployMode.COMPOSE.value]:
            self._stop_compose()


pass_enova_app = click.make_pass_decorator(EnovaApp)


@click.group(name="app")
@click.option("-d", "--deploy-mode", type=EnumType(DeployMode), default=DeployMode.LOCAL.value)
@click.pass_context
def app_cli(ctx, deploy_mode: DeployMode):
    """
    Start ENOVA application server.
    """
    ctx.obj = EnovaApp(deploy_mode=deploy_mode.value)


@app_cli.command(name="run", context_settings=CONFIG.cli["subcmd_context_settings"])
@click.option("--host", type=str, default=CONFIG.enova_app["host"])
@click.option("--port", type=int, default=CONFIG.enova_app["port"])
@pass_enova_app
@click.pass_context
def app_run(ctx, enov_app: EnovaApp, host, port):
    enov_app.run(host=host, port=port, **parse_extra_args(ctx))


@app_cli.command(name="stop")
@pass_enova_app
@click.pass_context
def app_stop(ctx, enov_app: EnovaApp):
    enov_app.stop()
