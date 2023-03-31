# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore
from types import ModuleType

import inspect

from .common import ForumExtractor
from ..cached_session import CachedSession

modules = [
    "hackernews",
    "hyperkitty",
    "pipermail",
    "hypermail",
    "xenforo",
    "vbulletin",
    "proboards",
    "invision",
    "discourse",
    "smf",
    "phpbb",
]


def find(url: str):
    session = CachedSession()

    for cls in list_classes():
        obj = cls.detect(session, url)
        if obj:
            return obj


def list_classes() -> Iterable[Any]:
    globals_ = globals()

    for module_name in modules:
        module = __import__(module_name, globals_, None, (), 1)
        yield from _get_classes(module)


def _get_classes(module: ModuleType):
    return [
        cls
        for cls in module.__dict__.values()
        if (
            inspect.isclass(cls)
            and not inspect.isabstract(cls)
            and issubclass(cls, ForumExtractor)
        )
    ]
