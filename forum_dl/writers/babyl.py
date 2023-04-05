# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from mailbox import Babyl, BabylMessage

from .common import FolderedMailWriter
from ..extractors.common import Extractor


class BabylWriter(FolderedMailWriter):
    tests = []

    def __init__(self, extractor: Extractor, path: str):
        super().__init__(extractor, path, Babyl(path))

    def _new_message(self):
        return BabylMessage()
