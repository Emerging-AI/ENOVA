import abc
import dataclasses
import uvicorn
from enova.common.logger import LOGGER
from enova.enode.enode import Enode


@dataclasses.dataclass
class BaseBackend(metaclass=abc.ABCMeta):
    enode: Enode

    @abc.abstractmethod
    def _create_app(self):
        """"""

    def _create_apiserver(self):
        self._create_app()
        self._init_middlewares()
        self._init_routers()

    def _init_middlewares(self):
        """"""

    def _init_exception_handler(self):
        """"""

    def _init_routers(self):
        """ """

    def local_run(self, host, port):
        """"""
        self._create_apiserver()
        self.print_run_info(host, port)
        uvicorn.run(self.app, host=host, port=port)

    def print_run_info(self, host, port):
        # Send the welcome message, especially to make sure that users will know
        # whicl URL to visit in order to not get a "not found" error.
        LOGGER.info(f"host: {host}, port: {port}")
