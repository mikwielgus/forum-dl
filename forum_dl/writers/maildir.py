# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from .common import Writer
from ..extractors.common import ForumExtractor, Board, Thread, Post
import mailbox
import email.utils


class MaildirWriter(Writer):
    tests = []

    def __init__(self, extractor: ForumExtractor, directory: str):
        Writer.__init__(self, extractor, directory)
        self._maildir = mailbox.Maildir(directory)

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

        for item in self._extractor.items(board):
            self.write_thread(folder, item)

        for _, subboard in self._extractor.subboards(board).items():
            self.write_board(subboard)

    def write_thread(self, folder: mailbox.Maildir, thread: Thread):
        for item in self._extractor.items(thread):
            self.write_post(folder, thread, item)

    def write_post(self, folder: mailbox.Maildir, thread: Thread, post: Post):
        msg = mailbox.MaildirMessage()
        msg["Message-ID"] = "<" + ".".join(post.path) + ">"

        if len(post.path) >= 2:
            msg["In-Reply-To"] = f"<{'.'.join(post.path[:-1])}>"

            refs = f"{post.path[0]}"
            for ref in post.path[1:-1]:
                refs += f" <{ref}>"

        msg["Subject"] = thread.title
        msg["Date"] = email.utils.formatdate(post.date)

        msg.set_payload(post.content, "utf-8")
        folder.add(msg)
