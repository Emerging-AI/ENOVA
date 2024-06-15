import copy
import multiprocessing
import os
import json
from json import JSONDecodeError
import rapidjson


def _get_pkg_version(filename="VERSION", back_step=4):
    version_file_path = None
    current_dir = os.path.dirname(__file__)
    for _ in range(back_step):
        maybe_file_path = os.path.join(current_dir, filename)
        if os.path.exists(maybe_file_path) and os.path.isfile(maybe_file_path):
            version_file_path = maybe_file_path
            break
        current_dir = os.path.dirname(current_dir)

    try:
        if version_file_path:
            with open(version_file_path, "r") as version_file:
                _ver = version_file.read().strip()
            return _ver
    except Exception:
        pass
    return "0.0.x"


def proc_val(value):
    if not isinstance(value, str):
        return value

    # pylint: disable=no-else-return
    if value.lower() == "true":
        return True
    elif value.lower() == "false":
        return False

    try:
        return json.loads(value)
    except JSONDecodeError:
        pass

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        pass

    return value


class Config:
    """Global Config"""

    root_dir = os.getcwd()

    # defualt value of whole service
    default_map = {
        "pkg": {"version": "0.0.3"},
        "app_name": "",
        "api": {
            "docs_url": "/api/docs",
            "redoc_url": "/api/redoc",
            "openapi_url": "/api/openapi.json",
            "harbor_username": "admin",
            "harbor_passwd": "",
            "api_version": "v1",
            "auth_api_version": "v1",
            "default_min_page": 1,
            "default_max_page": 1000,
            "default_max_size": 200,
            "default_min_size": 1,
            "termination_grace_period_seconds": 30,
            "databases": {"default": {"database": "enova_database", "data_dir": "/tmp"}},
        },
        "logger": {
            "name": "server",
            "path": "./var/log/emergingai",
            "level": "debug",
            "datefmt": "%Y-%m-%d %a %H:%M:%S",
            "fmt": "[%(asctime)s.%(msecs)d][%(levelname)s][%(processName)s][%(process)d][%(threadName)s][%(name)s][%(pathname)s:%(lineno)s - %(funcName)s()] %(message)s",  # noqa
            "file_handler_filename_format": "{path}/{name}.log",
            "file_handler_when": "H",
            "file_handler_interval": 1,
            "file_handler_backupCount": 336,
            "file_handler_suffix": "%Y-%m-%d_%H.log",
            "file_handler_extMatch_pattern": "^\\d{4}-\\d{2}-\\d{2}_\\d{2}.log$",
        },
        "scheduler": {},
        "apps": {},
        "TEMP_DIR": "/tmp",
        "object_spilling_paths": ["/tmp/ray/spills"],
        "serving": {
            "backend": "vllm",
            "host": "0.0.0.0",
            "port": 9199,
            "replica": 1,
        },
        "webui": {
            "host": "0.0.0.0",
            "port": 8501,
            "script": "webui/chat.py",
            "daemon": True,
        },
        "llmo": {
            # "eai_exporter_endpoint": "0.0.0.0:32893",
            "eai_exporter_endpoint": "otel-collector:4317",
            "eai_exporter_service_name": "llmo-svc",
        },
        "vllm": {
            "gpu_memory_utilization": 0.5,
            "tensor_parallel_size": 1,
            "vllm_mode": "normal",
            "trust_remote_code": True,
        },
        "deploy": {
            "docker_compose_exce": "template/deployment/docker-compose/bin/docker-compose-linux-x86_64",
        },
        "enova_algo": {
            "middleware_names": [
                "enova.server.middleware.trace.TraceMiddleware",
                "enova.server.middleware.response.ResponseMiddleware",
            ],
            "resource_names": ["enova.algo.resource"],
            "host": "0.0.0.0",
            "port": 8181,
            "url_prefix": "/api/enovaalgo",
            "api_version": "v1",
        },
        "enova_app": {
            "middleware_names": [
                "enova.server.middleware.trace.TraceMiddleware",
                "enova.server.middleware.response.ResponseMiddleware",
            ],
            "resource_names": ["enova.app.resource"],
            "host": "0.0.0.0",
            "port": 8182,
            "url_prefix": "",
            "api_version": "v1",
            "escaler_api_host": "http://enova-escaler:8183",
            "app_api_host": "http://127.0.0.1:8182",
            "prom_api_host": "http://enova-prometheus:9090",
            "prom_time_step": "1m",
            "enode_api_host": "http://enova-enode:9199",
            "model_dir": "/workspace/model",
            "dataset_dir_container": "/opt/enova/enova/template/deployment/docker-compose/traffic-injector/data",
        },
        "enova_enode": {},
        "cli": {
            "default_app_healthz_check_count": 10,
            "context_settings": {"help_option_names": ["-h", "--help"]},
            "subcmd_context_settings": {
                "help_option_names": ["-h", "--help"],
                "ignore_unknown_options": True,
                "allow_extra_args": True,
            },
        },
        "traffic_injector": {
            "conf": "template/deployment/docker-compose/traffic-injector",
            "cache_dir": "/tmp/traffic_injector",
            "dataset_dir": "traffic_injector_dataset",
            "dataset_host_dir": "/home/traffic_injector_dataset",
            "default_enode_host": "enova-enode",
        },
    }

    _instance = None

    def __init__(self):
        self.inner_logger = multiprocessing.get_logger()
        self.args_map = {}
        self.config_map = copy.deepcopy(self.default_map)
        self.load_enviroments()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance

    def set_default(self, d):
        d = {key: value for key, value in d.items()}
        self.default_map.update(d)

    def update(self, d, map_name="derived"):
        """ """
        d = {key: value for key, value in d.items()}
        config_map = getattr(self, "%s_map" % map_name)
        config_map.update(d)

    def _update_if_exist(self, src_dct, dst_dct):
        new_dct = copy.deepcopy(dst_dct)
        for k, v in src_dct.items():
            if k in new_dct:
                if isinstance(v, dict) and isinstance(new_dct[k], dict):
                    new_dct.update({k: self._update_if_exist(v, new_dct[k])})
                elif not isinstance(new_dct[k], dict):
                    new_dct.update({k: v})
                else:
                    raise ValueError("new config missmatch default")
            else:
                new_dct.update({k: v})
        return new_dct

    def load_enviroments(self):
        for k, v in os.environ.items():
            if k.startswith("EMERGINGAI"):
                k = k.replace("EMERGINGAI_", "").lower()
                v = proc_val(v)

                has_updated = False
                for special_key_prefix in ["api", "enova_app", "enova_algo", "traffic_injector", "cli", "enova_enode"]:
                    if k.startswith(f"{special_key_prefix}_"):
                        k = k.replace(f"{special_key_prefix}_", "", 1)
                        if isinstance(v, dict) and isinstance(self.config_map[special_key_prefix].get(k), dict):
                            v = self._update_if_exist(v, self.config_map[special_key_prefix].get("", {}))
                        self.config_map[special_key_prefix].update({k: v})
                        has_updated = True
                        break
                if not has_updated:
                    self.config_map.update({k: v})
                    if isinstance(v, dict):
                        v = self._update_if_exist(v, self.config_map.get(k, {}))
                    self.config_map.update({k: v})
            elif k in ["HOSTNAME"]:
                self.config_map[k.lower()] = v

    def __getattr__(self, key):
        """ """
        return self._inner_getattr(key)

    def _inner_getattr(self, key):
        if key in self.args_map:
            return self.args_map[key]
        elif key in self.config_map:
            return self.config_map[key]
        elif key in os.environ:
            return proc_val(os.environ[key])
        elif key in self.default_map:
            return self.default_map[key]
        return None

    def load_config(self, file_name):
        """
        load config from json file, gernerally setup the default value of components,
        also modify by the env vars
        """
        # default config
        if os.path.exists(file_name):
            with open(file_name, "r") as file_obj:
                for k, v in rapidjson.load(file_obj).items():
                    if isinstance(v, dict):
                        v = self._update_if_exist(v, self.config_map.get(k, {}))
                    self.config_map.update({k: v})
        else:
            self.inner_logger.error(f"Cannot find config file: {file_name}.")

        # env config
        self.load_enviroments()

    def load_args(self, args):
        """
        modify the config by the user arguments
        """
        # CLI options/arguments have higher priority, they override the above configurations.
        self.args_map.update({k: v for k, v in vars(args).items() if v is not None})

    def update_config(self, args):
        for k, v in args.items():
            if isinstance(v, dict) and isinstance(self.config_map.get(k), dict):
                v = self._update_if_exist(v, self.config_map.get(k))
            self.config_map.update({k: v})

    @property
    def api_docs_url(self):
        return CONFIG.api["url_prefix"] + "/docs"

    @property
    def api_redoc_url(self):
        return CONFIG.api["url_prefix"] + "/redoc"

    @property
    def api_openapi_url(self):
        return CONFIG.api["url_prefix"] + "/openapi.json"

    @property
    def command_args(self):
        command_args_lst = []
        for k, v in CONFIG.config_map.items():
            if k.endswith("args"):
                v["command_func"] = k
                command_args_lst.append(v)

        return command_args_lst

    def print_config(self, logger=None):
        if logger is not None:
            logger.info(f"config_map: {json.dumps(self.config_map, indent=4)}")
        else:
            from enova.common.logger import LOGGER

            LOGGER.info(f"config_map: {json.dumps(self.config_map, indent=4)}")

    def get_user_args(self):
        if not CONFIG.command_args:
            return {}
        return min(CONFIG.command_args, key=lambda item: item.get("call_order", float("inf")))


CONFIG = Config()
# default conf/settings.json
DEFAULT_CONFIG_SETTINGS = "conf/settings.json"
if os.path.exists(DEFAULT_CONFIG_SETTINGS):
    CONFIG.load_config(DEFAULT_CONFIG_SETTINGS)
