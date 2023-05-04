# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from abc import ABC, abstractmethod
from dataclasses import dataclass
from mailbox import Mailbox, Message
from html2text import html2text
import sys

from ..extractors.common import Extractor, Item, Thread, Board, Post, PageState
from ..version import __version__


@dataclass(kw_only=True)
class WriterOptions:
    output_path: str
    write_board_objects: bool
    write_thread_objects: bool
    write_post_objects: bool
    content_as_title: bool
    textify: bool


@dataclass(kw_only=True)
class WriterState:
    board_path: list[str] | None = None
    board_page: PageState | None = None
    thread_page: PageState | None = None


@dataclass(kw_only=True)
class Entry:
    version: str
    extractor: str
    type: str
    item: Item


class Writer(ABC):
    tests: list[dict[str, Any]]

    def __init__(self, extractor: Extractor, options: WriterOptions):
        self._extractor = extractor
        self._options = options
        self._initial_state = WriterState()

    def write(self, url: str):
        self.read_metadata()

        base_node = self._extractor.node_from_url(url)

        if isinstance(base_node, Board):
            self.write_board(base_node)
        elif isinstance(base_node, Thread):
            self.write_thread(base_node)

    @abstractmethod
    def read_metadata(self):
        pass

    @abstractmethod
    def _write_board_object(self, board: Board):
        pass

    def _write_board_threads(self, board: Board):
        for thread in self._extractor.threads(board, self._initial_state.board_page):
            self.write_thread(thread)

    @final
    def write_board(self, board: Board):
        if (
            self._initial_state.board_path is not None
            and board.path != self._initial_state.board_path
        ):
            return

        if self._options.write_board_objects:
            self._write_board_object(board)

        self._write_board_threads(board)

        for _, subboard in self._extractor.subboards(board).items():
            self.write_board(subboard)

    @abstractmethod
    def _write_thread_object(self, thread: Thread):
        pass

    def _write_thread_posts(self, thread: Thread):
        for post in self._extractor.posts(thread, self._initial_state.thread_page):
            self.write_post(thread, post)

    @final
    def write_thread(self, thread: Thread):
        if self._options.write_thread_objects:
            self._write_thread_object(thread)

        self._write_thread_posts(thread)

    @abstractmethod
    def _write_post_object(self, thread: Thread, post: Post):
        pass

    @final
    def write_post(self, thread: Thread, post: Post):
        if self._options.write_post_objects:
            self._write_post_object(thread, post)


class SimulatedWriter(Writer):
    def read_metadata(self):
        pass

    def _write_board_object(self, board: Board):
        pass

    def _write_thread_object(self, thread: Thread):
        pass

    def _write_post_object(self, thread: Thread, post: Post):
        pass


class FileWriter(Writer):
    def __init__(self, extractor: Extractor, options: WriterOptions):
        super().__init__(extractor, options)

        if options.output_path != "-":
            try:
                self._file = open(options.output_path, "r+")
            except FileNotFoundError:
                self._file = open(options.output_path, "w+")
        else:
            self._file = None

    def __del__(self):
        if self._file:
            self._file.close()

    def read_metadata(self):
        pass  # TODO.

    def _write_board_object(self, board: Board):
        entry = self._make_entry(board)

        if self._file:
            self._file.write(f"{self._serialize_entry(entry)}\n")
        else:
            sys.stdout.write(f"{self._serialize_entry(entry)}\n")

    def _write_thread_object(self, thread: Thread):
        entry = self._make_entry(thread)

        if self._file:
            self._file.write(f"{self._serialize_entry(entry)}\n")
        else:
            sys.stdout.write(f"{self._serialize_entry(entry)}\n")

    def _write_post_object(self, thread: Thread, post: Post):
        entry = self._make_entry(post)

        if self._file:
            self._file.write(f"{self._serialize_entry(entry)}\n")
        else:
            sys.stdout.write(f"{self._serialize_entry(entry)}\n")

    def _make_entry(self, item: Item):
        if isinstance(item, Board):
            type = "board"
        elif isinstance(item, Thread):
            type = "thread"
        elif isinstance(item, Post):
            type = "post"
        else:
            raise ValueError

        return Entry(
            version=__version__,
            extractor="TODO",
            type=type,
            item=item,
        )

    @abstractmethod
    def _serialize_entry(self, entry: Entry) -> str:
        pass


class MailWriter(Writer):
    def __init__(
        self,
        extractor: Extractor,
        mailbox: Mailbox[Any],
        options: WriterOptions,
    ):
        super().__init__(extractor, options)
        self._mailbox = mailbox

        for key, msg in self._mailbox.iteritems():
            if msg.get("X-Forumdl-Version"):
                self._metadata_key = key
        else:
            msg = self._new_message()
            self._metadata_key = self._mailbox.add(msg)

    def __del__(self):
        self._mailbox.flush()
        self._mailbox.close()

    def write(self, url: str):
        self._mailbox.lock()
        super().write(url)
        self._mailbox.unlock()

    def read_metadata(self):
        pass  # TODO.

    def _write_board_object(self, board: Board):
        pass  # TODO.

    def _write_thread_object(self, thread: Thread):
        pass  # TODO.

    def _write_post_object(self, thread: Thread, post: Post):
        self._mailbox.add(self._build_message(thread, post))

    @abstractmethod
    def _new_message(self) -> Message:
        pass

    def _build_message(self, thread: Thread, post: Post):
        msg = self._new_message()

        msg["Message-ID"] = "<" + ".".join(post.path) + ">"
        msg["From"] = post.data["author"]

        if len(post.path) >= 2:
            msg["In-Reply-To"] = f"<{'.'.join(post.path[:-1])}>"

            refs = f"{post.path[0]}"
            for ref in post.path[1:-1]:
                refs += f" <{ref}>"

        if len(post.path) >= 2 and self._options.content_as_title:
            msg["Subject"] = html2text(post.data["body"][:98]).partition("\n")[0]
        else:
            msg["Subject"] = thread.data["title"]

        # msg["Date"] = formatdate(post.date)

        if self._options.textify:
            msg.set_type("text/plain")
            msg.set_payload(html2text(post.data["body"]), "utf-8")
        else:
            msg.set_type("text/html")
            msg.set_payload(post.data["body"], "utf-8")

        return msg


class FolderedMailWriter(MailWriter):
    def __init__(
        self,
        extractor: Extractor,
        mailbox: Mailbox[Any],
        options: WriterOptions,
    ):
        super().__init__(extractor, mailbox, options)
        self.folders: dict[str, Mailbox[Any]] = {}

    def _folder_name(self, board: Board):
        return ".".join(board.path)

    def _write_board_object(self, board: Board):
        folder_name = self._folder_name(board)
        self.folders[folder_name] = getattr(self._mailbox, "add_folder")(folder_name)
        super()._write_board_object(board)

    def _write_post_object(self, thread: Thread, post: Post):
        board = self._extractor.find_board(thread.path[:-1])
        folder_name = self._folder_name(board)
        self.folders[folder_name].add(self._build_message(thread, post))
