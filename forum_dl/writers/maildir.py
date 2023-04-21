# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from mailbox import Maildir, MaildirMessage

from .common import FolderedMailWriter, WriterOptions
from ..extractors.common import Extractor


class MaildirWriter(FolderedMailWriter):
    tests = []

    def __init__(self, extractor: Extractor, path: str, options: WriterOptions):
        super().__init__(extractor, path, Maildir(path), options)

    def _new_message(self):
        return MaildirMessage()
