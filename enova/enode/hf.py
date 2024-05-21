import dataclasses
import functools
import inspect
from typing import Union, List, Callable, Optional, Any, Annotated
from fastapi import Response, HTTPException, Body, Request
from fastapi.responses import JSONResponse
import pydantic
from enova.common.logger import LOGGER
from enova.common.config import CONFIG
from enova.enode.enode import Enode, REMOTE_FUNC_TAG

hf_no_attention_mask_models = {"microsoft/phi-1", "microsoft/phi-1_5"}


def _create_hf_transformers_pipeline(task, model, revision):
    from transformers import pipeline, AutoTokenizer, AutoConfig, AutoModelForCausalLM
    import torch

    kwargs = {}
    if CONFIG.TRUST_REMOTE_CODE:
        kwargs["trust_remote_code"] = CONFIG.TRUST_REMOTE_CODE
    if CONFIG.enova_enode.get("hf_proxy"):
        hf_proxy = CONFIG.enova_enode["hf_proxy"]
        kwargs["proxies"] = {
            "http": hf_proxy,
            "https": hf_proxy,
        }

    # audio-classification pipeline doesn't support automatically
    # converting inputs from fp32 to fp16
    if torch.cuda.is_available() and task != "audio-classification":
        torch_dtype = torch.float16
    else:
        # TODO: check if bfloat16 is well supported
        torch_dtype = torch.float32

    kwargs["torch_dtype"] = torch_dtype

    model_kwargs = {
        "low_cpu_mem_usage": True,
    }

    if task == "text-generation":
        no_attention_mask = model in hf_no_attention_mask_models

        config = AutoConfig.from_pretrained(model, revision=revision, **kwargs)
        if no_attention_mask or not config.tokenizer_class:
            try:
                tokenizer = AutoTokenizer.from_pretrained(model, revision=revision, **kwargs)
                if no_attention_mask:
                    # tokenizer checks if attention_mask is in
                    # model_input_names to set "return_attention_mask"
                    # kwargs
                    tokenizer.model_input_names.remove("attention_mask")

                    model_obj = AutoModelForCausalLM.from_pretrained(
                        model, revision=revision, **kwargs, **model_kwargs
                    )

                    def patch_model_obj(model_obj):
                        orig_generate = model_obj.generate

                        def no_attention_mask_generate(self, *args, **kwargs):
                            # remove attention_mask from kwargs
                            kwargs.pop("attention_mask", None)
                            return orig_generate(*args, **kwargs)

                        model_obj.generate = no_attention_mask_generate.__get__(model_obj)

                    patch_model_obj(model_obj)

                    if torch.cuda.is_available():
                        model_obj = model_obj.to("cuda")
            except Exception as e:
                LOGGER.info(f"Failed to create tokenizer with AutoTokenizer: {e}")
            else:
                kwargs["tokenizer"] = tokenizer
                if no_attention_mask:
                    kwargs["model"] = model_obj

    if "model" not in kwargs:
        kwargs["model_kwargs"] = model_kwargs

    if torch.cuda.is_available():
        kwargs["device"] = 1
    kwargs.setdefault("model", model)
    try:
        pipe = pipeline(task=task, revision=revision, **kwargs)
    except Exception as e:
        LOGGER.info(f"Failed to create pipeline with {torch_dtype}: {e}, fallback to fp32")
        if "low_cpu_mem_usage" in str(e).lower():
            LOGGER.info("error seems to be caused by low_cpu_mem_usage, retry without" " low_cpu_mem_usage")
            kwargs.get("model_kwargs", {}).pop("low_cpu_mem_usage")
            if not kwargs.get("model_kwargs"):
                kwargs.pop("model_kwargs")
        # fallback to fp32
        kwargs.pop("torch_dtype")
        pipe = pipeline(task=task, revision=revision, **kwargs)
    return pipe


if pydantic.version.VERSION < "2.0.0":
    PYDANTIC_MAJOR_VERSION = 1
else:
    PYDANTIC_MAJOR_VERSION = 2


def create_model_for_func(func: Callable, func_name: Optional[str] = None, use_raw_args: bool = False):
    (
        args,
        _,
        varkw,
        defaults,
        kwonlyargs,
        kwonlydefaults,
        annotations,
    ) = inspect.getfullargspec(func)
    if len(args) > 0 and (args[0] == "self" or args[0] == "cls"):
        args = args[1:]  # remove self or cls

    if not use_raw_args and (args or varkw):
        if defaults is None:
            defaults = ()
        non_default_args_count = len(args) - len(defaults)
        defaults = (...,) * non_default_args_count + defaults

        keyword_only_params = {param: kwonlydefaults.get(param, Any) for param in kwonlyargs}
        params = {param: (annotations.get(param, Any), default) for param, default in zip(args, defaults)}

        if varkw:
            if PYDANTIC_MAJOR_VERSION <= 1:

                class config:  # type: ignore
                    extra = "allow"

            else:
                config = pydantic.ConfigDict(extra="allow")  # type: ignore
        else:
            config = None  # type: ignore

        func_name = func_name or func.__name__
        request_model = pydantic.create_model(
            f"{func_name.capitalize()}Input",
            **params,
            **keyword_only_params,
            __config__=config,  # type: ignore
        )
    else:
        request_model = None

    return_type = inspect.signature(func).return_annotation

    if inspect.isclass(return_type) and issubclass(return_type, Response):
        response_model = None
        response_class = return_type
    else:
        if return_type is inspect.Signature.empty:
            return_type = Any

        if PYDANTIC_MAJOR_VERSION <= 1:

            class config:
                arbitrary_types_allowed = True

        else:
            config = pydantic.ConfigDict(arbitrary_types_allowed=True)  # type: ignore

        response_model = pydantic.create_model(
            f"{func_name.capitalize()}Output",
            output=(return_type, None),
            __config__=config,  # type: ignore
        )
        response_class = JSONResponse
    return request_model, response_model, response_class


def _get_generated_text(res):
    if isinstance(res, str):
        return res
    elif isinstance(res, dict):
        return res["generated_text"]
    elif isinstance(res, list):
        if len(res) == 1:
            return _get_generated_text(res[0])
        else:
            return [_get_generated_text(r) for r in res]
    else:
        raise ValueError(f"Unsupported result type in _get_generated_text: {type(res)}")


@dataclasses.dataclass
class HFText2TextEnode(Enode):
    def __post_init__(self):
        self.pipeline = None

    def init(self):
        self.load_model()

    def load_model(self):
        """"""
        self.pipeline = _create_hf_transformers_pipeline("text-generation", self.model, None)

    @Enode.remote_func(method="POST", path="generate")
    async def generate(
        self,
        inputs: Union[str, List[str]],
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        temperature: Optional[float] = 1.0,
        repetition_penalty: Optional[float] = None,
        max_new_tokens: Optional[int] = None,
        max_time: Optional[float] = None,
        return_full_text: bool = True,
        num_return_sequences: int = 1,
        do_sample: bool = True,
        **kwargs,
    ):
        """"""
        res = self._run_pipeline(
            inputs,
            top_k=top_k,
            top_p=top_p,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
            max_new_tokens=max_new_tokens,
            max_time=max_time,
            return_full_text=return_full_text,
            num_return_sequences=num_return_sequences,
            do_sample=do_sample,
            **kwargs,
        )
        return _get_generated_text(res)

    def _run_pipeline(self, *args, **kwargs):
        import torch

        # autocast causes invalid value (and generates black images) for text-to-image and image-to-image
        if torch.cuda.is_available():
            with torch.autocast(device_type="cuda"):
                return self.pipeline(*args, **kwargs)
        else:
            return self.pipeline(*args, **kwargs)

    def _create_typed_handler(self, path, http_method, func, kwargs):
        method = func.__get__(self, self.__class__)

        request_model, response_model, response_class = create_model_for_func(
            func,
            func_name=self.__class__.__name__ + "_" + path,
            use_raw_args=kwargs.get("use_raw_args"),
        )

        if http_method.lower() == "post" and request_model is not None:
            if "example" in kwargs:
                request_model = Annotated[request_model, Body(example=kwargs["example"])]
            if "examples" in kwargs:
                request_model = Annotated[request_model, Body(examples=kwargs["examples"])]

        async def handle_request(
            request: Optional[Request],
            callback,
            *args,
            **kwargs,
        ):
            """
            Common handler for processing requests.
            """
            try:
                res = await callback(*args, **kwargs)
            except Exception as e:
                LOGGER.exception(f"handle_request exception: {str(e)}")
                if isinstance(e, TimeoutError):
                    return JSONResponse(
                        {"error": (f"handler timeout after {self.handler_timeout} seconds")},
                        status_code=504,
                    )
                elif isinstance(e, HTTPException):
                    return JSONResponse({"error": e.detail}, status_code=e.status_code)
                else:
                    return JSONResponse({"error": str(e)}, status_code=500)
            else:
                if res is None:
                    res = Response(status_code=204)
                elif not isinstance(res, response_class):
                    res = response_class(res)
                return res

        # for post handler, we change endpoint function's signature to make
        # it taking json body as input, so do not copy the
        # `__annotations__` attribute here
        typed_handler_wrapper = functools.wraps(
            method,
            assigned=(wa for wa in functools.WRAPPER_ASSIGNMENTS if wa != "__annotations__"),  # type: ignore
        )

        if http_method.lower() == "post":
            # In the post mode, we do the following:
            # - If the handler specifies "use_raw_args", then we don't wrap the args to a
            # json body, but instead just pass the raw args up to fastapi.
            # - Otherwise, we wrap the args to a json body, and use the request_model
            # as the pydantic model to validate the json body.
            # - If no args are specified, we don't wrap anything.

            vd = pydantic.decorator.validate_arguments(method).vd  # type: ignore

            @typed_handler_wrapper
            async def typed_handler(raw_request: Request, request: request_model):  # type: ignore
                return await handle_request(raw_request, vd.execute, request)

            delattr(typed_handler, "__wrapped__")

        elif http_method.lower() == "get":

            @functools.wraps(method)
            async def typed_handler(*args, **kwargs):
                return await handle_request(None, False, method, *args, **kwargs)

        else:
            raise ValueError(f"Unsupported http method {http_method}")

        typed_handler_kwargs = {
            "response_model": response_model,
            "response_class": response_class,
        }

        # Programming note: explicitly add other kwargs here if needed.
        if "include_in_schema" in kwargs:
            typed_handler_kwargs["include_in_schema"] = kwargs["include_in_schema"]

        return typed_handler, typed_handler_kwargs

    def register_api_router(self, api_router):
        for attr_name in dir(self):
            attr_val = getattr(self, attr_name)
            if hasattr(attr_val, REMOTE_FUNC_TAG) and callable(attr_val):
                remote_func_ins = getattr(attr_val, REMOTE_FUNC_TAG)
                typed_handler, typed_handler_kwargs = self._create_typed_handler(
                    remote_func_ins.path, remote_func_ins.method.lower(), attr_val, {}
                )
                api_router.add_api_route(
                    f"/{remote_func_ins.path}",
                    typed_handler,
                    name=remote_func_ins.path,
                    methods=[remote_func_ins.method.lower()],
                    **typed_handler_kwargs,
                )
