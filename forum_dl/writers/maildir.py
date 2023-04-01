# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from .common import Writer
from ..extractors.common import Extractor, Board, Thread, Post
from mailbox import Maildir, MaildirMessage
import email.utils


class MaildirWriter(Writer):
    tests = []

    def __init__(self, extractor: Extractor, path: str):
        Writer.__init__(self, extractor, path)
        self._maildir = Maildir(path)

    def __del__(self):
        self._maildir.flush()
        self._maildir.close()

    def write(self, url: str):
        self._maildir.lock()
        base_node = self._extractor.node_from_url(url)

        if isinstance(base_node, Board):
            self.write_board(base_node)

        self._maildir.unlock()

    def write_board(self, board: Board):
        folder = self._maildir.add_folder(".".join(board.path))

        for thread in self._extractor.threads(board):
            self.write_thread(folder, thread)

        for _, subboard in self._extractor.subboards(board).items():
            self.write_board(subboard)

    def write_thread(self, folder: Maildir, thread: Thread):
        for post in self._extractor.posts(thread):
            self.write_post(folder, thread, post)

    def write_post(self, folder: Maildir, thread: Thread, post: Post):
        msg = MaildirMessage()
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
        folder.add(msg)
