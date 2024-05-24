import collections
import numbers
import random
import re
import string
import time
import uuid
from collections import defaultdict
from distutils.sysconfig import get_python_lib
from typing import Union

import cpuinfo
import psutil
import pyopencl as cl
import ulid

from enova.common.config import CONFIG
from enova.common.logger import LOGGER

uuid_alphabet = string.ascii_letters + string.digits


def short_uuid(length=8):
    return "".join(random.choices(uuid_alphabet, k=length))


def random_uuid() -> str:
    return str(uuid.uuid4().hex)


def gen_ulid() -> str:
    return ulid.new().hex[2:]  # rid out the '0x'


def camel_to_snake(name):
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def get_pkg_namespace_path(dist):
    module_path = dist.__file__
    if not module_path:
        namespace_path = dist.__path__._path

        globally_path_lst = []
        maybe_locally_path_lst = []

        for nsp in namespace_path:
            if "__path_hook__" in nsp:
                continue

            if nsp == get_python_lib() + "/" + dist.__name__:
                globally_path_lst.append(nsp)
            else:
                maybe_locally_path_lst.append(nsp)

        if globally_path_lst:
            module_path = globally_path_lst[0]
        else:
            if not maybe_locally_path_lst:
                raise ValueError("web_statics package isn't in the python site-packages")

            module_path = maybe_locally_path_lst[0]

        if CONFIG.api.get("develop_mode"):
            module_path = maybe_locally_path_lst[0]

    LOGGER.debug(f"module_path: {module_path}")
    return module_path


def get_enova_path():
    import enova

    return get_pkg_namespace_path(enova)


def get_web_static_path():
    try:
        import enova.web_statics as web_statics

        return get_pkg_namespace_path(web_statics)
    except Exception as e:
        LOGGER.exception(f"get_web_static_path error: {str(e)}")
        return None


def datetime2timestamp(datetime):
    time_array = time.strptime(datetime, "%Y-%m-%d %H:%M:%S")
    return time.mktime(time_array)


SizeMagnitude = collections.namedtuple("SizeMagnitude", "divider, symbol, name")
CombinedMagnitude = collections.namedtuple("CombinedMagnitude", "decimal, binary")


disk_size_mgnts = (
    CombinedMagnitude(SizeMagnitude(1000**1, "K", "kilo"), SizeMagnitude(1024**1, "Ki", "kibi")),
    CombinedMagnitude(SizeMagnitude(1000**2, "M", "mega"), SizeMagnitude(1024**2, "Mi", "mebi")),
    CombinedMagnitude(SizeMagnitude(1000**3, "G", "giga"), SizeMagnitude(1024**3, "Gi", "gibi")),
    CombinedMagnitude(SizeMagnitude(1000**4, "T", "tera"), SizeMagnitude(1024**4, "Ti", "tebi")),
    CombinedMagnitude(SizeMagnitude(1000**5, "P", "peta"), SizeMagnitude(1024**5, "Pi", "pebi")),
    CombinedMagnitude(SizeMagnitude(1000**6, "E", "exa"), SizeMagnitude(1024**6, "Ei", "exbi")),
    CombinedMagnitude(SizeMagnitude(1000**7, "Z", "zetta"), SizeMagnitude(1024**7, "Zi", "zebi")),
    CombinedMagnitude(SizeMagnitude(1000**8, "Y", "yotta"), SizeMagnitude(1024**8, "Yi", "yobi")),
    CombinedMagnitude(SizeMagnitude(1000**9, "B", "bronto"), SizeMagnitude(1024**9, "Bi", "brobi")),
)


def tokenize_size(text):
    tokenized_input = []
    for token in re.split(r"(\d+(?:\.\d+)?)", text):
        token = token.strip()
        if re.match(r"\d+\.\d+", token):
            tokenized_input.append(float(token))
        elif token.isdigit():
            tokenized_input.append(int(token))
        elif token:
            tokenized_input.append(token)
    return tokenized_input


def round_num(num, round_fmt=".2f"):
    num_txt = f"{num:{round_fmt}}"
    num_txt = re.sub("0+$", "", num_txt)
    num_txt = re.sub(r"\.$", "", num_txt)
    return num_txt


def format_size(num_bytes, suffix="B", is_binary=True, mgnt_repr=("binary", "symbol"), round_fmt=".2f"):
    for mgnt in reversed(disk_size_mgnts):
        if num_bytes >= mgnt.binary.divider and is_binary:
            num = round_num(float(num_bytes) / mgnt.binary.divider, round_fmt=round_fmt)
            unit = getattr(getattr(mgnt, mgnt_repr[0]), mgnt_repr[1])
            return f"{num}{unit}{suffix}"
        elif num_bytes >= mgnt.decimal.divider and (not is_binary):
            num = round_num(float(num_bytes) / mgnt.decimal.divider, round_fmt=round_fmt)
            unit = getattr(getattr(mgnt, mgnt_repr[0]), mgnt_repr[1])
            return f"{num}{unit}{suffix}"
    return f"{num_bytes}{suffix}"


def format_size_by_mgnt(num_bytes, ds_mgnt, is_binary=True, round_fmt=".2f"):
    pass


def parse_mgnt_base_by_unit(storage_unit: str, is_binary=True) -> int:
    ds_unit = str.lower(storage_unit)
    ds_mgnt = ds_unit.rstrip("s").rstrip("byte").rstrip("b")

    if not ds_unit:
        return 1

    for mgnt in disk_size_mgnts:
        if ds_mgnt in (mgnt.binary.symbol.lower(), mgnt.binary.name.lower()):
            return mgnt.binary.divider

        if ds_mgnt in (mgnt.decimal.symbol.lower(), mgnt.decimal.name.lower()):
            return mgnt.binary.divider if is_binary else mgnt.decimal.divider

    raise ValueError(f"parse storage unit failed, (input {storage_unit} do not valid magnitude part as {ds_mgnt})")


def parse_size(ds_txt: str, is_binary=True) -> int:
    tokens = tokenize_size(ds_txt)
    if tokens and isinstance(tokens[0], numbers.Number):
        ds_unit = tokens[1].lower() if len(tokens) == 2 and isinstance(tokens[1], str) else ""
        if len(tokens) == 1 or ds_unit.startswith("b"):
            return int(tokens[0])

        if ds_unit:
            ds_mgnt = ds_unit.rstrip("s").rstrip("byte").rstrip("b")
            for mgnt in disk_size_mgnts:
                # first check binary symbols (ki, mi, gi, etc) and names (kibi, mebi, gibi, etc)
                if ds_mgnt in (mgnt.binary.symbol.lower(), mgnt.binary.name.lower()):
                    return int(tokens[0] * mgnt.binary.divider)
                # second check decimal(maybe same as binary)
                if ds_mgnt in (mgnt.decimal.symbol.lower(), mgnt.decimal.name.lower()):
                    return int(tokens[0] * (mgnt.binary.divider if is_binary else mgnt.decimal.divider))

    raise ValueError(f"parse size failed, (input {ds_txt} was tokenized as {tokens})")


class DiskSize:
    def __init__(self, ds: Union[int, str, "DiskSize"], is_binary=True):
        self.is_binary = is_binary
        if isinstance(ds, int):
            self.bytes = ds
        elif isinstance(ds, str):
            self.bytes = parse_size(ds, self.is_binary)
        elif isinstance(ds, DiskSize):
            self.bytes = ds.bytes
            self.is_binary = ds.is_binary
        else:
            raise ValueError("construct failed, the Type of input must in [int, str, obj of DiskSize]")

    def _common_check(self, other):
        if not isinstance(other, DiskSize):
            raise ValueError(f"operand {other} must be DiskSize Object")

    def _number_check(self, other):
        if not isinstance(other, numbers.Number):
            raise ValueError(f"operand {other} must be a number")
        if other < 0:
            raise ValueError(f"operand {other} be non negative")

    def __mul__(self, other):
        self._number_check(other)
        return DiskSize(self.bytes * other, is_binary=self.is_binary)

    def __truediv__(self, other):
        self._number_check(other)
        return DiskSize(int(self.bytes / other), is_binary=self.is_binary)

    def __add__(self, other):
        self._common_check(other)
        return DiskSize(self.bytes + other.bytes, is_binary=self.is_binary)

    def __sub__(self, other):
        self._common_check(other)
        return DiskSize(self.bytes - other.bytes, is_binary=self.is_binary)

    def __gt__(self, other):
        self._common_check(other)
        return self.bytes > other.bytes

    def __lt__(self, other):
        self._common_check(other)
        return self.bytes < other.bytes

    def __ge__(self, other):
        self._common_check(other)
        return self.bytes >= other.bytes

    def __le__(self, other):
        self._common_check(other)
        return self.bytes <= other.bytes

    def __str__(self):
        return self.dec_repr

    @property
    def dec(self):
        return format_size(self.bytes, suffix="", is_binary=self.is_binary, mgnt_repr=("decimal", "symbol"))

    @property
    def bin(self):
        return format_size(self.bytes, suffix="", is_binary=self.is_binary, mgnt_repr=("binary", "symbol"))

    @property
    def dec_repr(self):
        return format_size(self.bytes, suffix="B", is_binary=self.is_binary, mgnt_repr=("decimal", "symbol"))

    @property
    def bin_repr(self):
        return format_size(self.bytes, suffix="B", is_binary=self.is_binary, mgnt_repr=("binary", "symbol"))


def get_machine_spec():
    machine_spec = {}

    # gpu
    gpu_spec_amount = defaultdict(int)

    platforms = cl.get_platforms()
    for platform in platforms:
        devices = platform.get_devices()
        for device in devices:
            if device.type == cl.device_type.GPU:
                gpu_spec_amount[(device.name, device.global_mem_size)] += 1

    gpu_lst = []
    for spec, amount in gpu_spec_amount.items():
        gpu_lst.append(
            {
                "product": spec[0],
                "video_memory": format_size(spec[1], mgnt_repr=("decimal", "symbol"), round_fmt=".0f"),
                "card_amount": amount,
            }
        )

    gpu = max(gpu_lst, key=lambda item: item.get("card_amount", 0))
    machine_spec["gpu"] = gpu

    # cpu
    cpu_info = cpuinfo.get_cpu_info()
    cpu = {"brand_name": cpu_info["brand_raw"], "core_amount": cpu_info["count"]}
    machine_spec["cpu"] = cpu

    # memory
    mem_info = psutil.virtual_memory()
    machine_spec["memory"] = format_size(mem_info.total, mgnt_repr=("decimal", "symbol"), round_fmt=".0f")

    return machine_spec
