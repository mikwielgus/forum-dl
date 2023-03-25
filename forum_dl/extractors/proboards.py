# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs
import bs4
import re

from .common import normalize_url
from .common import ForumExtractor, Board, Thread, Post
from ..cached_session import CachedSession


class ProboardsForumExtractor(ForumExtractor):
    tests = []

    _category_name_regex = re.compile(r"^category-(\d+)$")
    _board_id_regex = re.compile(r"^board-(\d+)$")

    @staticmethod
    def detect(session: CachedSession, url: str):
        response = session.get(url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        parsed_url = urlparse(url)

        if parsed_url.netloc.endswith("proboards.com"):
            return ProboardsForumExtractor(session, urljoin(url, "/"))

    def _fetch_top_boards(self):
        self.root.are_subboards_fetched = True

        response = self._session.get(self._base_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        category_anchors = soup.find_all("a", attrs={"name": self._category_name_regex})

        for category_anchor in category_anchors:
            category_id = self._category_name_regex.match(
                category_anchor.get("name")
            ).group(1)

            title_div = category_anchor.find_next("div", class_="title_wrapper")

            self._set_board(
                path=[category_id], title=title_div.string, are_subboards_fetched=True
            )

            category_div = category_anchor.find_next("div", class_="boards")
            board_trs = category_div.find_all("tr", id=self._board_id_regex)

            for board_tr in board_trs:
                board_id = self._board_id_regex.match(board_tr.get("id"))
                board_anchor = board_tr.find("a", class_=self._board_id_regex)

                self._set_board(
                    path=[category_id, board_id],
                    url=urljoin(self._base_url, board_anchor.get("href")),
                    title=board_anchor.string,
                    are_subboards_fetched=True,
                )

        # board_trs = category_anchor.find_all_next("tr", id=self._board_tr_id_regex)
        # for board_tr in board_trs:
        # category_id =

    def _fetch_subboards(self, board: Board):
        if not board.url:
            return

        response = self._session.get(board.url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        subboard_trs = soup.find_all("tr", id=self._board_id_regex)

        for subboard_tr in subboard_trs:
            subboard_id = self._board_id_regex.match(subboard_tr.get("id"))
            subboard_anchor = subboard_tr.find("a", class_=self._board_id_regex)

            self._set_board(
                path=board.path + [subboard_id],
                url=urljoin(self._base_url, subboard_anchor.get("href")),
                title=subboard_anchor.string,
                are_subboards_fetched=True,
            )

    def _get_node_from_url(self, url: str):
        parsed_url = urlparse(url)
        path = PurePosixPath(url.path)

        if path.parts[0] == "thread":
            response = self._session.get(board.url)
            soup = bs4.BeautifulSoup(response.content, "html.parser")

            breadcrumbs_div = soup.find("div", class_="nav-tree-wrapper")
            breadcrumb_anchors = breadcrumbs_div.find_all(
                "a", attrs={"itemprop": "item"}
            )

            board_url = urljoin(self._base_url, breadcrumb_anchors[-2].get("href"))

            for cur_board in self._boards:
                if cur_board.url == board_url:
                    return Thread(path=cur_board.path + [id], url=url)
        elif path.parts[0] == "board":
            for cur_board in self._boards:
                if cur_board.path[-1] == path.parts[1]:
                    return cur_board

        raise ValueError

    def _fetch_lazy_subboard(self, board: Board, id: str):
        pass

    def _fetch_lazy_subboards(self, board: Board):
        pass

    def _get_board_page_items(self, board: Board, page_url: str, cur_page: int = 1):
        response = self._session.get(board.url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        thread_anchors = soup.find_all("a", class_="thread-link")
        for thread_anchor in thread_anchors:
            thread_id = self._thread_id_regex.match(thread_anchor.get("id")).group(1)
            yield Thread(
                path=board.path + [thread_id],
                url=urljoin(self._base_url, thread_anchor.get("href")),
            )

        next_page_li = soup.find("li", class_="next")
        next_page_anchor = next_page_li.find("a")

        if next_page_anchor.get("href"):
            return (urljoin(self._base_url, next_page_anchor.get("href")), cur_page + 1)

    def _get_thread_page_items(self, thread: Thread, page_url: str, cur_page: int = 1):
        response = self._session.get(board.url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        message_divs = soup.find_all("div", class_="message")
        for message_div in message_divs:
            yield Post(path=thread.path, content=str(message_div.encode_contents()))

        next_page_li = soup.find("li", class_="next")
        next_page_anchor = next_page_li.find("a")

        if next_page_anchor:
            return (urljoin(self._base_url, next_page_anchor.get("href")), cur_page + 1)
