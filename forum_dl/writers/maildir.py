# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from abc import ABC, abstractmethod

from .common import Writer
from ..extractors.common import ForumExtractor, Board, ExtractorNode
import mailbox


class MaildirWriter(Writer):
    tests = []

    def __init__(self, extractor: ForumExtractor, directory: str):
        Writer.__init__(self, extractor, directory)
        self._maildir = mailbox.Maildir(directory)

    def __del__(self):
        print("del")
        self._maildir.flush()
        self._maildir.close()

    def write(self, url: str):
        self._maildir.lock()

        base_node = self._extractor.node_from_url(url)

        if isinstance(base_node, Board):
            self.write_board(base_node)

        self._maildir.unlock()

    def write_item(self, folder: mailbox.Maildir, item: ExtractorNode):
        msg = mailbox.MaildirMessage()
        msg["Subject"] = item.title
        msg.set_payload(item.content)
        folder.add(msg)

        for item in self._extractor.items(item):
            self.write_item(folder, item)

    def write_board(self, board: Board):
        folder = self._maildir.add_folder(".".join(board.path))

        for item in self._extractor.items(board):
            self.write_item(folder, item)

        for _, subboard in self._extractor.subboards(board).items():
            self.write_board(subboard)
