# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from .common import Writer
from ..extractors.common import Extractor, Board, Thread, Post
from mailbox import mbox, mboxMessage
import email.utils


class MboxWriter(Writer):
    tests = []

    def __init__(self, extractor: Extractor, path: str):
        Writer.__init__(self, extractor, path)
        self._mbox = mbox(path)

    def write(self, url: str):
        self._mbox.lock()
        base_node = self._extractor.node_from_url(url)

        if isinstance(base_node, Board):
            self.write_board(base_node)

        self._mbox.unlock()

    def write_board(self, board: Board):
        for thread in self._extractor.threads(board):
            self.write_thread(thread)

    def write_thread(self, thread: Thread):
        for post in self._extractor.posts(thread):
            self.write_post(thread, post)

    def write_post(self, thread: Thread, post: Post):
        msg = mboxMessage()
        msg["Message-ID"] = "<" + ".".join(post.path) + ">"
        msg["From"] = post.username

        if len(post.path) >= 2:
            msg["In-Reply-To"] = f"<{'.'.join(post.path[:-1])}>"

            refs = f"{post.path[0]}"
            for ref in post.path[1:-1]:
                refs += f" <{ref}>"

        msg["Subject"] = thread.title
        msg["Date"] = email.utils.formatdate(post.date)

        msg.set_payload(post.content, "utf-8")
        self._mbox.add(msg)
