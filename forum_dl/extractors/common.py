# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
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


def normalize_url(
    url: str,
    remove_suffixes: list[str] = ["index.php"],
    append_slash: bool = True,
    keep_queries: list[str] = [],
):
    parsed_url = urlparse(url)
    new_path = parsed_url.path.removesuffix("/")

    if not keep_queries or not parsed_url.query:
        for remove_suffix in remove_suffixes:
            new_path = new_path.removesuffix(remove_suffix)

    new_path = new_path.removesuffix("/")

    query = parse_qs(parsed_url.query)
    new_query = {key: query[key] for key in keep_queries if key in query}

    new_parsed_url = parsed_url._replace(
        path=new_path, params="", query=urlencode(new_query, doseq=True), fragment=""
    )

    new_url = urlunparse(new_parsed_url)

    if append_slash and not new_parsed_url.query:
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
    date: int | None = None


@dataclass
class Thread(ExtractorNode):
    username: str = ""
    post_count: int = 0


@dataclass
class Board(ExtractorNode):
    subboards: dict[str, Board] = field(default_factory=dict)
    are_subboards_fetched: bool = False


class ForumExtractor(ABC):
    tests: list[Any]
    board_type = Board

    @staticmethod
    @abstractmethod
    def detect(session: CachedSession, url: str) -> ForumExtractor | None:
        pass

    def __init__(self, session: CachedSession, base_url: str):
        self._session = session
        self._base_url = base_url
        self.root = Board(path=[], url=self._resolve_url(base_url))
        self._boards: list[Board] = [self.root]

    @final
    def fetch(self):
        self._fetch_top_boards()

        i = 0
        while i < len(self._boards):
            board = self._boards[i]
            self._fetch_subboards(board)
            i += 1

    @abstractmethod
    def _fetch_top_boards(self):
        pass

    def _set_board(self, **kwargs: Any):
        path = kwargs["path"]

        if not (replace_path := kwargs.pop("replace_path", None)):
            replace_path = path

        parent_board = self.find_board(replace_path[:-1])

        if replace_path[-1] in parent_board.subboards:
            for k, v in kwargs.items():
                setattr(parent_board.subboards[replace_path[-1]], k, v)

            new_parent_board = self.find_board(path[:-1])
            new_parent_board.subboards[path[-1]] = parent_board.subboards.pop(
                replace_path[-1]
            )

            return new_parent_board.subboards[path[-1]]
        else:
            # We use self.root as base because its type may be a subclass of Board.
            parent_board.subboards[replace_path[-1]] = self.board_type(**kwargs)
            self._boards.append(parent_board.subboards[replace_path[-1]])

            return parent_board.subboards[replace_path[-1]]

    @abstractmethod
    def _fetch_subboards(self, board: Board):
        pass

    def _resolve_url(self, url: str):
        return url

    @abstractmethod
    def _get_node_from_url(self, url: str) -> ExtractorNode:
        pass

    @final
    def find_board(self, path: list[str]):
        cur_board: Board = self.root

        for path_part in path:
            if path_part not in cur_board.subboards:
                self._fetch_lazy_subboard(cur_board, path_part)

            cur_board = cur_board.subboards[path_part]

        return cur_board

    @final
    def node_from_url(self, url: str):
        node = self._get_node_from_url(self._resolve_url(url))

        if isinstance(node, Board):
            return self.find_board(cast(Board, node).path)

        return node

    @abstractmethod
    def _fetch_lazy_subboard(self, board: Board, id: str):
        pass

    @abstractmethod
    def _fetch_lazy_subboards(self, board: Board) -> Generator[Board, None, None]:
        pass

    @final
    def subboards(self, board: Board):
        if not board.are_subboards_fetched:
            self._fetch_lazy_subboards(board)
            board.are_subboards_fetched = True

        return board.subboards

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
