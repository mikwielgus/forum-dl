# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from .common import Writer
from ..extractors.common import ForumExtractor

# from .strictyaml import StrictYamlWriter
from .mbox import MboxWriter
import inspect

modules = ["json", "mbox", "maildir"]


def find(extractor: ForumExtractor, directory: str, module_name: str):
    globals_ = globals()

    if module_name in modules:
        module = __import__(module_name, globals_, None, (), 1)

        for cls in module.__dict__.values():
            if (
                inspect.isclass(cls)
                and not inspect.isabstract(cls)
                and issubclass(cls, Writer)
            ):
                return cls(extractor, directory)
