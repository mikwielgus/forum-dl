# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from .common import Writer
from ..extractors.common import ForumExtractor

# from .strictyaml import StrictYamlWriter
from .json import JsonWriter
import inspect

modules = ["json"]


def find(extractor: ForumExtractor):
    return JsonWriter(extractor, "xxx")


def list_classes() -> Iterable[Any]:
    globals_ = globals()

    for module_name in modules:
        module = __import__(module_name, globals_, None, (), 1)
        yield from _get_classes(module)


def _get_classes(module):
    return [
        cls
        for cls in module.__dict__.values()
        if (
            inspect.isclass(cls)
            and not cls.__subclasses__()
            and issubclass(cls, Writer)
        )
    ]
