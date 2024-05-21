import abc
from fastapi import Request


class BaseExceptionHandler(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_exception_class(self):
        """"""

    @abc.abstractmethod
    def exception_handler(self, request: Request, exc):
        """"""
