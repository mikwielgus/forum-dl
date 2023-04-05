# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from abc import ABC, abstractmethod
from dataclasses import dataclass
from mailbox import Message
from html2text import html2text
from email.utils import formatdate

from ..extractors.common import Extractor, Thread, Post


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
    def __init__(self, extractor: Extractor, path: str):
        Writer.__init__(self, extractor, path)

    def _fill_message(
        self, thread: Thread, post: Post, msg: Message, options: WriteOptions
    ):
        msg["Message-ID"] = "<" + ".".join(post.path) + ">"
        msg["From"] = post.username

        if len(post.path) >= 2:
            msg["In-Reply-To"] = f"<{'.'.join(post.path[:-1])}>"

            refs = f"{post.path[0]}"
            for ref in post.path[1:-1]:
                refs += f" <{ref}>"

        if options.content_as_title:
            msg["Subject"] = html2text(post.content[:98]).partition("\n")[0]
        else:
            msg["Subject"] = thread.title

        msg["Date"] = formatdate(post.date)

        if options.textify:
            msg.set_type("text/plain")
            msg.set_payload(html2text(post.content), "utf-8")
        else:
            msg.set_type("text/html")
            msg.set_payload(post.content, "utf-8")

        return msg
