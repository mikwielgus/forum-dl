# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from pathlib import PurePosixPath

from ..cached_session import CachedSession


def get_relative_url(url: str, base_url: str):
    parsed_base_url = urlparse(base_url)
    parsed_url = urlparse(url)

    base_path = PurePosixPath(str(parsed_base_url.path))
    path = PurePosixPath(str(parsed_url.path))

    if str(base_path) == ".":
        return path

    return str(path.relative_to(base_path))


def normalize_url(url: str, exclude_query: list[str] = []):
    parsed_url = urlparse(url)

    query = parse_qs(parsed_url.query)
    new_query = {key: query[key] for key in exclude_query}

    new_parsed_url = parsed_url._replace(
        params="", query=urlencode(new_query, doseq=True), fragment=""
    )

    new_url = urlunparse(new_parsed_url)

    if not new_url.endswith("/") and not new_parsed_url.query:
        return f"{new_url}/"

    return new_url


@dataclass
class ExtractorNode:
    path: list[str]
    url: str = ""
    title: str = ""
    content: str = ""


@dataclass
class Post(ExtractorNode):
    username: str = ""


@dataclass
class Thread(ExtractorNode):
    username: str = ""


@dataclass
class Board(ExtractorNode):
    lazy_subboards: dict[str, Board] = field(default_factory=dict)


class ForumExtractor(ABC):
    tests: list[Any]

    @staticmethod
    @abstractmethod
    def detect(session: CachedSession, url: str) -> ForumExtractor | None:
        pass

    def __init__(self, session: CachedSession, base_url: str):
        self._session = session
        self._base_url = base_url
        self.root = Board(path=[], url=base_url)

    @abstractmethod
    def fetch(self):
        pass

    def _resolve_url(self, url: str):
        return url

    @abstractmethod
    def _get_node_from_url(self, url: str) -> ExtractorNode:
        pass

    @final
    def _find_board(self, path: list[str]):
        cur_board = self.root

        for path_part in path:
            cur_board = self.subboards(cur_board)[path_part]

        return cur_board

    @final
    def node_from_url(self, url: str):
        node = self._get_node_from_url(self._resolve_url(url))

        if isinstance(node, Board):
            return self._find_board(cast(Board, node).path)

        return node

    @abstractmethod
    def _fetch_subboard(self, board: Board, id: str):
        # We don't use this at the moment.
        pass

    @final
    def subboards(self, board: Board):
        for id, subboard in board.lazy_subboards.items():
            self._fetch_subboard(subboard, id)

        return board.lazy_subboards

    @abstractmethod
    def _get_board_page_items(
        self, board: Board, page_url: str, *args: Any
    ) -> Generator[Thread, None, tuple[str, ...]]:
        pass

    @final
    def _get_board_items(self, board: Board):
        state = (board.url,)
        while state:
            state = yield from self._get_board_page_items(board, *state)

    @abstractmethod
    def _get_thread_page_items(
        self, thread: Thread, page_url: str, *args: Any
    ) -> Generator[Thread | Post, None, tuple[str, ...]]:
        pass

    @final
    def _get_thread_items(self, thread: Thread):
        state = (thread.url,)
        while state:
            state = yield from self._get_thread_page_items(thread, *state)

    @final
    def items(self, node: ExtractorNode):
        if isinstance(node, Board):
            yield from self._get_board_items(node)
        elif isinstance(node, Thread):
            yield from self._get_thread_items(node)
