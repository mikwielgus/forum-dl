# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from mailbox import MH, MHMessage

from .common import FolderedMailWriter, WriterOptions
from ..extractors.common import Extractor


class MhWriter(FolderedMailWriter):
    tests = []

    def __init__(self, extractor: Extractor, path: str, options: WriterOptions):
        super().__init__(extractor, path, MH(path), options)

    def _new_message(self):
        return MHMessage()
