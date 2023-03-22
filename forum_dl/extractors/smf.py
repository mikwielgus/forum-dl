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


class SmfForumExtractor(ForumExtractor):
    tests = [
        {
            "url": "https://simplemachines.org/community",
            "test_base_url": "https://www.simplemachines.org/community/",
            "test_boards": {
                ("2",): {
                    "title": "Simple Machines",
                },
                ("3",): {
                    "title": "SMF Support",
                },
                ("18",): {
                    "title": "Customizing SMF",
                },
                ("15",): {
                    "title": "SMF Development",
                },
                ("4",): {
                    "title": "General Community",
                },
                ("16",): {
                    "title": "Simple Machines Blogs",
                },
                ("5",): {
                    "title": "Archived Boards and Threads...",
                },
            },
        },
        {
            "url": "https://www.simplemachines.org/community/index.php?board=255.0",
            "test_base_url": "https://www.simplemachines.org/community/",
            "test_boards": {
                ("3", "254", "255"): {
                    "title": "PostgreSQL Support",
                },
                ("3", "20", "134"): {
                    "title": "vBulletin",
                },
                ("4", "19"): {
                    "title": "Site Comments, Issues and Concerns",
                },
            },
        },
        {
            "url": "https://www.simplemachines.org/community/index.php?topic=573.0",
            "test_base_url": "https://www.simplemachines.org/community/",
            "test_contents_hash": "fdc4d37625278d71d24b0130c9abf9ecf5050f28",
            "test_item_count": 6,
        },
        {
            "url": "https://www.simplemachines.org/community/index.php?topic=581247.0",
            "test_base_url": "https://www.simplemachines.org/community/",
            "test_contents_hash": "749888009f2724fcff0dd95353d18e9d755e7a3f",
            "test_item_count": 1,
        },
    ]

    _category_id_regex = re.compile(r"^c(\d+)$")
    _board_id_regex = re.compile(r"^b(\d+)$")
    _span_id_regex = re.compile(r"^msg_(\d+)$")
    _div_id_regex = re.compile(r"^msg_(\d+)$")

    @staticmethod
    def detect(session: CachedSession, url: str):
        response = session.get(url)
        # print(response.text)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        if not (link := soup.find("link", attrs={"rel": "contents"})):
            return None

        if not (base_url := normalize_url(link.get("href"))):
            return None

        simplemachines_anchor = soup.find(
            "a",
            attrs={
                "href": "https://www.simplemachines.org",
                "title": "Simple Machines",
            },
        )

        if simplemachines_anchor:
            return SmfForumExtractor(session, base_url)

    def _fetch_top_boards(self):
        self.root.are_subboards_fetched = True

        response = self._session.get(self._base_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        category_anchors = soup.find_all("a", id=self._category_id_regex)
        for category_anchor in category_anchors:
            category_id = self._category_id_regex.match(
                category_anchor.get("id")
            ).group(1)
            title = str(category_anchor.next_sibling).strip()

            self._set_board(path=[category_id], title=title, are_subboards_fetched=True)

            for parent in category_anchor.parents:
                board_anchors = parent.find_all("a", id=self._board_id_regex)

                if board_anchors:
                    for board_anchor in board_anchors:
                        board_id = self._board_id_regex.match(
                            board_anchor.get("id")
                        ).group(1)

                        self._set_board(
                            path=[category_id, board_id],
                            url=board_anchor.get("href"),
                            title=board_anchor.string.strip(),
                            are_subboards_fetched=True,
                        )
                    break

    def _fetch_subboards(self, board: Board):
        if not board.url:
            return

        # Don't fetch top boards.
        if len(board.path) <= 1:
            return

        response = self._session.get(board.url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        subboard_anchors = soup.find_all("a", attrs={"id": self._board_id_regex})

        for subboard_anchor in subboard_anchors:
            subboard_id = self._board_id_regex.match(subboard_anchor.get("id")).group(1)
            self._set_board(
                path=board.path + [subboard_id],
                url=subboard_anchor.get("href"),
                title=subboard_anchor.string.strip(),
                are_subboards_fetched=True,
            )

    def _resolve_url(self, url: str):
        return normalize_url(
            self._session.get(url).url,
            append_slash=False,
            keep_queries=["board", "topic"],
        )

    def _get_node_from_url(self, url: str):
        response = self._session.get(url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        breadcrumbs = soup.find(class_="navigate_section")

        if not breadcrumbs:
            breadcrumbs = soup.find(class_="linktree")

        breadcrumb_anchors: bs4.element.ResultSet[Any] = breadcrumbs.find_all("a")

        # Thread.
        if soup.find("div", id="forumposts"):
            board_href = breadcrumb_anchors[-2].get("href")

            for cur_board in self._boards:
                if cur_board.url == board_href:
                    return Thread(path=cur_board.path + [id], url=url)
        # Board.
        else:
            board_href = self._resolve_url(breadcrumb_anchors[-1].get("href"))

            for cur_board in self._boards:
                if cur_board.url == board_href:
                    return cur_board

        raise ValueError

    def _fetch_lazy_subboard(self, board: Board, id: str):
        pass

    def _fetch_lazy_subboards(self, board: Board):
        pass

    def _get_board_page_items(self, board: Board, page_url: str, cur_page: int = 1):
        if board == self.root:
            return None

        if not page_url:
            return None

        response = self._session.get(page_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        msg_spans = soup.find_all("span", id=self._span_id_regex)

        for msg_span in msg_spans:
            thread_id = self._span_id_regex.match(msg_span.get("id")).group(1)
            msg_anchor = msg_span.contents[0]

            yield Thread(path=board.path + [thread_id], url=msg_anchor.get("href"))

        next_page_anchor = soup.find("a", class_="nav_page", string=str(cur_page + 1))

        if next_page_anchor:
            return (next_page_anchor.get("href"), cur_page + 1)

    def _get_thread_page_items(self, thread: Thread, page_url: str, cur_page: int = 1):
        response = self._session.get(page_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        msg_divs = soup.find_all("div", id=self._div_id_regex)

        for msg_div in msg_divs:
            yield Post(
                path=thread.path + ["x"],  # TODO: We use a dummy path for now.
                content=str(msg_div.encode_contents()),
            )

        next_page_anchor = soup.find("a", class_="nav_page", string=str(cur_page))

        if next_page_anchor:
            return (next_page_anchor.get("href"), cur_page + 1)
