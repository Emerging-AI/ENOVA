import abc
import asyncio
import dataclasses
import random
import re
from typing import Callable, Dict, ClassVar, Generic, TypeVar
from xmlrpc.client import Boolean
import httpx
from enova.common.config import CONFIG
from enova.common.constant import JSON_RESPONSE_HEADER, HttpMethod
from enova.common.local import get_local_param, set_local_param
from enova.common.error import EmergingaiAPIResponseError, APIParamsError
from enova.common.logger import LOGGER
from enova.common.g_vars import get_traceid

T = TypeVar("T")
POOL_SIZE = CONFIG.POOL_SIZE or 1


class BaseClientPool(Generic[T]):
    def get_client(self) -> T:
        index = random.randint(0, POOL_SIZE - 1)
        return self.pools[index]


class ASyncClientPool(BaseClientPool[httpx.AsyncClient]):
    def __init__(self) -> None:
        self._pools = None

    @property
    def pools(self):
        # singleton of async client pool
        self._pools = get_local_param("async_client_pool")
        if self._pools is None:
            LOGGER.info("create ASyncClientPool pools")
            pools = [httpx.AsyncClient(timeout=None, verify=False) for _ in range(POOL_SIZE)]
            set_local_param("async_client_pool", pools)
            self._pools = pools
        return self._pools


class ClientPool(BaseClientPool[httpx.Client]):
    def __init__(self) -> None:
        self.pools = [httpx.Client() for _ in range(POOL_SIZE)]


async_client_pool = ASyncClientPool()
client_pool = ClientPool()


@dataclasses.dataclass
class ASyncAPI(metaclass=abc.ABCMeta):
    method: str
    url: str
    before_send: Callable = None
    url_builder: Callable = None
    remove_url_key: Boolean = False
    post_send: Callable = None
    header_builder: Callable = None

    def __post_init__(self):
        if self.url_builder is None:
            self.url_builder = self.default_url_builder

    def default_url_builder(self, url, params: Dict):
        if isinstance(params, dict):

            def extract_parameters(string):
                pattern = r"\{([^}]*)\}"
                matches = re.findall(pattern, string)
                return matches

            url_keys = extract_parameters(url)
            LOGGER.debug(f"default_url_builder extract_parameters: {url_keys}")
            url = url.format(**params)
            if self.remove_url_key:
                for url_key in url_keys:
                    params.pop(url_key, None)
        return url

    async def __call__(
        self,
        params,
        data=None,
        files=None,
        headers=None,
        stream=False,
        cookies=None,
        return_raw_response=False,
        **kwargs,
    ) -> Dict:
        # get trace_id
        if isinstance(self.before_send, Callable):
            self.before_send(params, data, files, headers, **kwargs)

        trace_id = get_traceid()
        async_client = async_client_pool.get_client()
        if stream:
            raise ValueError("not support")
        json_params = None
        if self.method.lower() in ["post", "put"]:
            json_params = params
            params = None
        actual_headers = {
            "trace_id": trace_id,
        }
        if self.header_builder:
            if asyncio.iscoroutinefunction(self.header_builder):
                header_builder_ret = await self.header_builder()
            else:
                header_builder_ret = self.header_builder()
            if header_builder_ret:
                actual_headers.update(header_builder_ret)
        if headers is not None:
            actual_headers.update(headers)
        actual_url = self.url_builder(self.url, params or json_params)
        LOGGER.info(
            f"method: {self.method}, actual_url: {actual_url}, params: {params or json_params}, headers: {actual_headers}"
        )
        response = await async_client.request(
            self.method,
            actual_url,
            params=params,
            json=json_params,
            data=data,
            files=files,
            headers=actual_headers,
            cookies=cookies,
            **kwargs,
        )
        if return_raw_response:
            return response
        return self._process_repsonse(response)

    def sync_call(self, *args, **kwargs):
        return asyncio.run(self.__call__(*args, **kwargs))

    def _process_repsonse(self, response):
        ret = response.json()
        if isinstance(self.post_send, Callable):
            ret = self.post_send(ret)
        return ret


@dataclasses.dataclass
class ASyncRestfulAPI:
    url: str
    resource_key: str = None
    before_send: Callable = None
    url_builder: Callable = None
    api_cls: ClassVar[ASyncAPI] = ASyncAPI
    remove_url_key: Boolean = False
    post_send: Callable = None
    header_builder: Callable = None

    def __getattr__(self, item):
        """"""
        if item.startswith("sync_"):
            async_method = getattr(self, item.replace("sync_", ""))

            def sync_call(*args, **kwargs):
                return asyncio.run(async_method(*args, **kwargs))

            return sync_call
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    async def request(self, method, params, files=None, headers=None, stream=False, specific_resource=False, **kwargs):
        if specific_resource:
            if self.resource_key is None:
                raise APIParamsError("AsyncRestfulEmergingaiAPI: method in [get, update] resource_key cannot be None")
            url = self.url + "/" + "{" + f"{self.resource_key}" + "}"  # noqa
            LOGGER.debug(f"ASyncRestfulAPI specific_resource url: {url}")
        else:
            url = self.url
        inno_api = self.api_cls(
            method,
            url,
            self.before_send,
            self.url_builder,
            remove_url_key=self.remove_url_key,
            post_send=self.post_send,
            header_builder=self.header_builder,
        )
        return await inno_api(params, files=files, headers=headers, stream=stream, **kwargs)

    async def create(self, params, files=None, headers=None, stream=False, specific_resource=False, **kwargs):
        return await self.request(
            method=HttpMethod.POST.value, params=params, files=files, headers=headers, stream=stream, **kwargs
        )

    async def list(self, params, files=None, headers=None, stream=False, specific_resource=False, **kwargs):
        return await self.request(
            method=HttpMethod.GET.value, params=params, files=files, headers=headers, stream=stream, **kwargs
        )

    async def update(self, params, files=None, headers=None, stream=False, specific_resource=False, **kwargs):
        return await self.request(
            method=HttpMethod.PUT.value,
            params=params,
            files=files,
            headers=headers,
            stream=stream,
            specific_resource=True,
            **kwargs,
        )

    async def delete(self, params, files=None, headers=None, stream=False, specific_resource=False, **kwargs):
        return await self.request(
            method=HttpMethod.DELETE.value,
            params=params,
            files=files,
            headers=headers,
            stream=stream,
            specific_resource=True,
            **kwargs,
        )

    async def get(self, params, files=None, headers=None, stream=False, specific_resource=False, **kwargs):
        return await self.request(
            method=HttpMethod.GET.value,
            params=params,
            files=files,
            headers=headers,
            stream=stream,
            specific_resource=True,
            **kwargs,
        )


class ASyncEmergingaiAPI(ASyncAPI):
    def _process_repsonse(self, response):
        if response.headers.get("content-type") == JSON_RESPONSE_HEADER:
            resp = response.json()
            if "code" not in resp:
                raise EmergingaiAPIResponseError("passthrough api is not enova api")
            if resp["code"] == "0" or resp["code"] == 0:
                return resp["result"]
            LOGGER.error(f"api get error code, resp: {resp}")
            raise EmergingaiAPIResponseError(resp["message"], resp["code"])
        raise EmergingaiAPIResponseError("only support json respsonse")


@dataclasses.dataclass
class ASyncRestfulEmergingaiAPI(ASyncRestfulAPI):
    api_cls: ClassVar[ASyncAPI] = ASyncEmergingaiAPI
