# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..extractors.common import Extractor


@dataclass
class WriteOptions:
    content_as_title: bool


class Writer(ABC):
    tests: list[dict[str, Any]]

    def __init__(self, extractor: Extractor, path: str):
        self._extractor = extractor
        self._path = path

    @abstractmethod
    def write(self, url: str, options: WriteOptions):
        pass
