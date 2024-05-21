from enova.common.config import CONFIG
from enova.server.server import ApiServer
from enova.common.constant import ApiServerType


def get_algo_api_server(api_server_type=ApiServerType.ENOVA_ALGO.value):
    api_config = getattr(CONFIG, api_server_type)
    CONFIG.api.update(api_config)

    api_server = ApiServer(api_config)

    return api_server
