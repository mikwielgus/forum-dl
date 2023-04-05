# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from abc import ABC, abstractmethod
from dataclasses import dataclass
from mailbox import Mailbox, Message
from html2text import html2text
from email.utils import formatdate

from ..extractors.common import Extractor, Thread, Board, Post


@dataclass
class WriteOptions:
    content_as_title: bool
    textify: bool


class Writer(ABC):
    tests: list[dict[str, Any]]

    def __init__(self, extractor: Extractor, path: str):
        self._extractor = extractor
        self._path = path

    @abstractmethod
    def write(self, url: str, options: WriteOptions):
        pass


class MailWriter(Writer):
    def __init__(self, extractor: Extractor, path: str, mailbox: Mailbox[Any]):
        super().__init__(extractor, path)
        self._mailbox = mailbox

    def __del__(self):
        self._mailbox.flush()
        self._mailbox.close()

    def write(self, url: str, options: WriteOptions):
        self._mailbox.lock()
        base_node = self._extractor.node_from_url(url)

        if isinstance(base_node, Board):
            self.write_board(base_node, options)

        self._mailbox.unlock()

    def write_board(self, board: Board, options: WriteOptions):
        for thread in self._extractor.threads(board):
            self.write_thread(thread, options)

        for _, subboard in self._extractor.subboards(board).items():
            self.write_board(subboard, options)

    def write_thread(self, thread: Thread, options: WriteOptions):
        for post in self._extractor.posts(thread):
            self.write_post(thread, post, options)

    def write_post(self, thread: Thread, post: Post, options: WriteOptions):
        self._mailbox.add(self._build_message(thread, post, options))

    @abstractmethod
    def _new_message(self) -> Message:
        pass

    def _build_message(self, thread: Thread, post: Post, options: WriteOptions):
        msg = self._new_message()

        msg["Message-ID"] = "<" + ".".join(post.path) + ">"
        msg["From"] = post.username

        if len(post.path) >= 2:
            msg["In-Reply-To"] = f"<{'.'.join(post.path[:-1])}>"

            refs = f"{post.path[0]}"
            for ref in post.path[1:-1]:
                refs += f" <{ref}>"

        if len(post.path) >= 2 and options.content_as_title:
            msg["Subject"] = html2text(post.content[:98]).partition("\n")[0]
        else:
            msg["Subject"] = thread.title

        msg["Date"] = formatdate(post.date)

        for prop_name, prop_val in post.properties.items():
            msg[f"X-Forumdl-{prop_name.capitalize()}"] = str(prop_val)

        if options.textify:
            msg.set_type("text/plain")
            msg.set_payload(html2text(post.content), "utf-8")
        else:
            msg.set_type("text/html")
            msg.set_payload(post.content, "utf-8")

        return msg


class FolderedMailWriter(MailWriter):
    def write_board(self, board: Board, options: WriteOptions):
        folder: Mailbox[Any] = getattr(self._mailbox, "add_folder")(
            ".".join(board.path)
        )

        for thread in self._extractor.threads(board):
            self.write_thread(folder, thread, options)

        for _, subboard in self._extractor.subboards(board).items():
            self.write_board(subboard, options)

    def write_thread(self, folder: Mailbox[Any], thread: Thread, options: WriteOptions):
        for post in self._extractor.posts(thread):
            self.write_post(folder, thread, post, options)

    def write_post(
        self, folder: Mailbox[Any], thread: Thread, post: Post, options: WriteOptions
    ):
        folder.add(self._build_message(thread, post, options))
