# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from abc import ABC, abstractmethod

from ..extractors.common import Extractor


class Writer(ABC):
    tests: tuple[dict[str, Any], ...]

    def __init__(self, extractor: Extractor, path: str):
        self._extractor = extractor
        self._path = path

    @abstractmethod
    def write(self, url: str):
        pass
