import rapidjson
from fastapi import Request, status

from fastapi.responses import JSONResponse, StreamingResponse
from enova.common.constant import JSON_RESPONSE_HEADER
from enova.common.g_vars import get_traceid
from enova.server.middleware.base import BaseMiddleware


class ResponseMiddleware(BaseMiddleware):

    async def _process_response(self, request: Request, response):
        """"""
        if request.url.path in [
            self.api_config["url_prefix"] + "/docs",
            self.api_config["url_prefix"] + "/redoc",
            self.api_config["url_prefix"] + "/openapi.json",
        ] or request.url.path.startswith(f"{self.api_config['url_prefix']}/admin"):
            return response
        trace_id = get_traceid()
        if isinstance(response, StreamingResponse) and response.headers.get("content-type") == JSON_RESPONSE_HEADER:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            resp = rapidjson.loads(response_body)
            if "code" in resp and "message" in resp:
                if "trace_id" not in resp:
                    resp["trace_id"] = trace_id
                resp = JSONResponse(
                    status_code=response.status_code,
                    content=resp,
                )
            else:
                if response.status_code == status.HTTP_200_OK:
                    code = 0
                else:
                    code = response.status_code
                resp = JSONResponse(
                    status_code=response.status_code,
                    content={"message": "", "code": code, "result": resp, "trace_id": trace_id, "version": self.api_config["api_version"]},
                )
            for k, v in response.headers.items():
                if k not in resp.headers:
                    resp.headers[k] = v
            return resp
        if isinstance(response, dict):
            return JSONResponse(
                status_code=200,
                content={"message": "", "code": 0, "result": response, "trace_id": trace_id, "version": self.api_config["api_version"]},
            )
        return response
