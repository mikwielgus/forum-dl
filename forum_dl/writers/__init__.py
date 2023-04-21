# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from .common import Writer, SimulatedWriter, WriterOptions
from ..extractors.common import Extractor
from ..exceptions import NoExtractorError
from ..session import SessionOptions

# from .strictyaml import StrictYamlWriter
import inspect

modules = ["babyl", "maildir", "mbox", "mh", "mmdf", "jsonl"]


def find(
    extractor: Extractor,
    module_name: str,
    path: str,
    session_options: SessionOptions,
    writer_options: WriterOptions,
):
    if session_options.get_urls:
        return SimulatedWriter(extractor, path, writer_options)

    globals_ = globals()

    if module_name in modules:
        module = __import__(module_name, globals_, None, (), 1)

        for cls in module.__dict__.values():
            if (
                inspect.isclass(cls)
                and not inspect.isabstract(cls)
                and issubclass(cls, Writer)
            ):
                return cls(extractor, path, writer_options)

    raise NoExtractorError
