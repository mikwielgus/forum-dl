# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from mailbox import Maildir, MaildirMessage

from .common import WriteOptions, MailWriter
from ..extractors.common import Extractor, Board, Thread, Post


class MaildirWriter(MailWriter):
    tests = []

    def __init__(self, extractor: Extractor, path: str):
        MailWriter.__init__(self, extractor, path)
        self._maildir = Maildir(path)

    def __del__(self):
        self._maildir.flush()
        self._maildir.close()

    def write(self, url: str, options: WriteOptions):
        self._maildir.lock()
        base_node = self._extractor.node_from_url(url)

        if isinstance(base_node, Board):
            self.write_board(base_node, options)

        self._maildir.unlock()

    def write_board(self, board: Board, options: WriteOptions):
        folder = self._maildir.add_folder(".".join(board.path))

        for thread in self._extractor.threads(board):
            self.write_thread(folder, thread, options)

        for _, subboard in self._extractor.subboards(board).items():
            self.write_board(subboard, options)

    def write_thread(self, folder: Maildir, thread: Thread, options: WriteOptions):
        for post in self._extractor.posts(thread):
            self.write_post(folder, thread, post, options)

    def write_post(
        self, folder: Maildir, thread: Thread, post: Post, options: WriteOptions
    ):
        folder.add(self._fill_message(thread, post, MaildirMessage(), options))
