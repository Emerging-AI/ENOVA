import importlib
from typing import Collection

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.trace import get_tracer
from vllm.model_executor.models import _MODELS
from wrapt import wrap_function_wrapper

from .wrappers import forward_wrapper, llmengine_init_wrapper

_instruments = ("vllm >= v0.3.1",)

TARGET_METHODS = {
    "build-in": [
        {
            "package": "vllm.worker.model_runner",
            "object": "CUDAGraphRunner",
            "method": "forward",
            "span_name": "CUDAGraphRunner.forward",
            "wrapper": forward_wrapper,
        },
        {
            "package": "vllm.engine.llm_engine",
            "object": "LLMEngine",
            "method": "__init__",
            "span_name": "LLMEngine.__init__",
            "wrapper": llmengine_init_wrapper,
        }

    ],
    "plug-in": [

    ]
}


def module_exists(module_name):
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


class EnovaVllmInstrumentor(BaseInstrumentor):
    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def __init__(self):
        super().__init__()
        self._original_methods = {}
        self.instrumented_methods = []

    def _instrument(self, **kwargs):
        tracer = get_tracer(__name__)

        for model_name, (sub_package, obj) in _MODELS.items():
            package = f"vllm.model_executor.models.{sub_package}"
            wrapper_method = {
                "package": package,
                "object": obj,
                "method": "forward",
                "span_name": f"{obj}.forward",
                "wrapper": forward_wrapper
            }
            self._apply_wrapper(tracer, wrapper_method)

        for wrapper_method in TARGET_METHODS['build-in']:
            self._apply_wrapper(tracer, wrapper_method)

    def _apply_wrapper(self, tracer, wrapped_method):
        if module_exists(wrapped_method["package"]):
            wrap_function_wrapper(
                wrapped_method["package"],
                f"{wrapped_method['object']}.{wrapped_method['method']}" if wrapped_method["object"] else
                wrapped_method["method"],
                wrapped_method["wrapper"](tracer, wrapped_method)
            )
            self.instrumented_methods.append(wrapped_method)

    def _uninstrument(self, **kwargs):
        for wrapped_method in self.instrumented_methods:
            wrap_package = wrapped_method.get("package")
            if module_exists(wrap_package):
                unwrap(
                    f"{wrapped_method['package']}.{wrapped_method['object']}" if wrapped_method["object"] else wrapped_method["package"],
                    wrapped_method['method'],
                )
