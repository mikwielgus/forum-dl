# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from mailbox import mbox, mboxMessage

from .common import WriteOptions, MailWriter
from ..extractors.common import Extractor, Board, Thread, Post


class MboxWriter(MailWriter):
    tests = []

    def __init__(self, extractor: Extractor, path: str):
        MailWriter.__init__(self, extractor, path)
        self._mbox = mbox(path)

    def write(self, url: str, options: WriteOptions):
        self._mbox.lock()
        base_node = self._extractor.node_from_url(url)

        if isinstance(base_node, Board):
            self.write_board(base_node, options)

        self._mbox.unlock()

    def write_board(self, board: Board, options: WriteOptions):
        for thread in self._extractor.threads(board):
            self.write_thread(thread, options)

    def write_thread(self, thread: Thread, options: WriteOptions):
        for post in self._extractor.posts(thread):
            self.write_post(thread, post, options)

    def write_post(self, thread: Thread, post: Post, options: WriteOptions):
        self._mbox.add(self._fill_message(thread, post, mboxMessage(), options))
