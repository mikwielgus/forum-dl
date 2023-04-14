# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from abc import ABC, abstractmethod
from dataclasses import dataclass
from mailbox import Mailbox, Message
from html2text import html2text
from email.utils import formatdate

from ..extractors.common import Extractor, Thread, Board, Post
from ..version import __version__


@dataclass
class WriteOptions:
    content_as_title: bool
    textify: bool


class Writer(ABC):
    tests: list[dict[str, Any]]

    def __init__(self, extractor: Extractor, path: str):
        self._extractor = extractor
        self._path = path

    def write(self, url: str, options: WriteOptions):
        self.write_version(options)

        base_node = self._extractor.node_from_url(url)

        if isinstance(base_node, Board):
            self.write_board(base_node, options)
    
    @abstractmethod
    def write_version(self, options: WriteOptions):
        pass

    def write_board(self, board: Board, options: WriteOptions):
        for thread in self._extractor.threads(board):
            self.write_thread(thread, options)

        for _, subboard in self._extractor.subboards(board).items():
            self.write_board(subboard, options)

    def write_thread(self, thread: Thread, options: WriteOptions):
        for post in self._extractor.posts(thread):
            self.write_post(thread, post, options)

    @abstractmethod
    def write_post(self, thread: Thread, post: Post, options: WriteOptions):
        pass


class MailWriter(Writer):
    def __init__(self, extractor: Extractor, path: str, mailbox: Mailbox[Any]):
        super().__init__(extractor, path)
        self._mailbox = mailbox
        self._metadata = self._get_metadata()

    def __del__(self):
        self._mailbox.flush()
        self._mailbox.close()

    def write(self, url: str, options: WriteOptions):
        self._mailbox.lock()
        super().write(url, options)
        self._mailbox.unlock()

    def write_version(self, options: WriteOptions):
        self._metadata["X-Forumdl-Version"] = __version__

    def write_post(self, thread: Thread, post: Post, options: WriteOptions):
        self._mailbox.add(self._build_message(thread, post, options))

    @abstractmethod
    def _new_message(self) -> Message:
        pass
    
    def _get_metadata(self):
        for _, msg in self._mailbox.itervalues():
            if msg.get("X-Forumdl-Version"):
                return msg
        
        return self._new_message()

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
            msg[f"X-Forumdl-Property-{prop_name.capitalize()}"] = str(prop_val)

        if options.textify:
            msg.set_type("text/plain")
            msg.set_payload(html2text(post.content), "utf-8")
        else:
            msg.set_type("text/html")
            msg.set_payload(post.content, "utf-8")

        return msg


class FolderedMailWriter(MailWriter):
    def __init__(self, extractor: Extractor, path: str, mailbox: Mailbox[Any]):
        super().__init__(extractor, path, mailbox)
        self.folders: dict[str, Mailbox[Any]] = {}

    def _folder_name(self, board: Board):
        return ".".join(board.path)

    def write_board(self, board: Board, options: WriteOptions):
        folder_name = self._folder_name(board)
        self.folders[folder_name] = getattr(self._mailbox, "add_folder")(folder_name)
        super().write_board(board, options)

    def write_post(self, thread: Thread, post: Post, options: WriteOptions):
        board = self._extractor.find_board(thread.path[:-1])
        folder_name = self._folder_name(board)
        self.folders[folder_name].add(self._build_message(thread, post, options))
