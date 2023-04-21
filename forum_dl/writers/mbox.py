# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from mailbox import mbox, mboxMessage

from .common import MailWriter, WriterOptions
from ..extractors.common import Extractor


class MboxWriter(MailWriter):
    tests = []

    def __init__(self, extractor: Extractor, path: str, options: WriterOptions):
        super().__init__(extractor, path, mbox(path), options)

    def _new_message(self):
        return mboxMessage()
