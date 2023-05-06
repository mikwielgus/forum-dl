# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse
import re

from .common import regex_match
from .common import Extractor, ExtractorOptions, Board, Thread, Post, PageState
from ..session import Session
from ..soup import Soup


class ProboardsExtractor(Extractor):
    tests = [
        {
            "url": "https://support.proboards.com",
            "test_base_url": "https://support.proboards.com/",
            "test_boards": {
                ("4",): {
                    "title": "Tech Support",
                },
                ("4", "80"): {
                    "title": "Help Guide",
                },
                ("4", "80", "138"): {
                    "title": "Help Guide Index",
                },
                ("4", "80", "76"): {
                    "title": "Admins and Moderators",
                },
                ("4", "80", "74"): {
                    "title": "Users and Members",
                },
                ("4", "80", "134"): {
                    "title": "Support FAQs",
                },
                ("4", "80", "72"): {
                    "title": "Plugin Developers",
                },
                ("4", "44"): {
                    "title": "Support Board",
                },
                ("4", "112"): {
                    "title": "Forums.net Sales Questions",
                },
                ("32",): {
                    "title": "ProBoards Development",
                },
                ("32", "92"): {
                    "title": "Development Blog",
                },
                ("32", "174"): {
                    "title": "ProBoards Contributions",
                },
                ("32", "176"): {
                    "title": "ProBoards v6 Beta",
                },
                ("16",): {
                    "title": "Coding, Development and Design",
                },
                ("16", "151"): {
                    "title": "Coding Help",
                },
                ("16", "38"): {
                    "title": "Plugins",
                },
                ("16", "38", "35"): {
                    "title": "Plugin Library",
                },
                ("16", "38", "36"): {
                    "title": "Request a Plugin",
                },
                ("16", "38", "96"): {
                    "title": "Plugin Development",
                },
                ("16", "82"): {
                    "title": "Themes",
                },
                ("16", "82", "64"): {
                    "title": "Theme Library",
                },
                ("16", "82", "86"): {
                    "title": "Request a Theme",
                },
                ("16", "45"): {
                    "title": "Templates",
                },
                ("16", "45", "78"): {
                    "title": "Template Library",
                },
                ("16", "45", "84"): {
                    "title": "Request a Template",
                },
                ("16", "55"): {
                    "title": "Headers & Footers",
                },
                ("16", "55", "90"): {
                    "title": "Headers & Footers Library",
                },
                ("16", "55", "88"): {
                    "title": "Request a Header & Footer Code",
                },
                ("16", "22"): {
                    "title": "Graphic Design",
                },
                ("16", "22", "126"): {
                    "title": "Graphic Design Library",
                },
                ("16", "22", "21"): {
                    "title": "Graphic Design Requests",
                },
                ("6",): {
                    "title": "Your Forum",
                },
                ("6", "140"): {
                    "title": "Open for Discussion - Staff of Forums Sharing Ideas",
                },
                ("6", "140", "40"): {
                    "title": "Promoting Your Forum Discussions",
                },
                ("6", "140", "40", "18"): {
                    "title": "Archived Threads",
                },
                ("6", "31"): {
                    "title": "Get Opinions About Your Forum",
                },
                ("6", "31", "179"): {
                    "title": "GOAYF Archive",
                },
                ("6", "1"): {
                    "title": "Advertise Your Forum",
                },
                ("6", "1", "2"): {
                    "title": "Art/Music/Tech",
                },
                ("6", "1", "4"): {
                    "title": "Graphics/Coding",
                },
                ("6", "1", "8"): {
                    "title": "ProBoards Related",
                },
                ("6", "1", "3"): {
                    "title": "General Forums",
                },
                ("6", "1", "9"): {
                    "title": "Roleplay Forums",
                },
                ("6", "1", "19"): {
                    "title": "Fan Forums",
                },
                ("6", "1", "32"): {
                    "title": "Archives",
                },
                ("6", "142"): {
                    "title": "Affiliate Exchange",
                },
                ("20",): {
                    "title": "General",
                },
                ("20", "33"): {
                    "title": "General Talk",
                },
                ("20", "33", "20"): {
                    "title": "The Game Board",
                },
                ("20", "33", "20", "143"): {
                    "title": "Proposing A New Game",
                },
                ("20", "33", "26"): {
                    "title": "Welcome",
                },
            },
        },
        {
            "url": "https://support.proboards.com/thread/426372/why-respond-ads-wants",
            "test_base_url": "https://support.proboards.com/",
            "test_contents_hash": "9ec24265615d028682fa61961694835a65f97adb",
            "test_item_count": 76,
        },
        {
            "url": "https://support.proboards.com/thread/15052/visual-conceptions",
            "test_base_url": "https://support.proboards.com/",
            "test_contents_hash": "45893917ef8e126559f4d166d667b15f1b162a23",
            "test_item_count": 31,
        },
    ]

    _category_name_regex = re.compile(r"^category-(\d+)$")
    _board_id_regex = re.compile(r"^board-(\d+)$")
    _thread_class_regex = re.compile(r"^thread-(\d+)$")

    @staticmethod
    def _detect(session: Session, url: str, options: ExtractorOptions):
        parsed_url = urlparse(url)

        if parsed_url.netloc.endswith("proboards.com"):
            return ProboardsExtractor(session, urljoin(url, "/"), options)

    def _fetch_top_boards(self):
        self._are_subboards_fetched[self.root.path] = True

        response = self._session.get(self.base_url)
        soup = Soup(response.content)

        category_anchors = soup.find_all("a", attrs={"name": self._category_name_regex})

        for category_anchor in category_anchors:
            category_id = regex_match(
                self._category_name_regex, category_anchor.get("name")
            ).group(1)

            title_div = category_anchor.find_next("div", class_="title_wrapper")

            self._set_board(
                path=(category_id,),
                url="",  # TODO.
                origin=response.url,
                data={},
                title=title_div.string,
                are_subboards_fetched=True,
            )

            category_div = category_anchor.find_next("div", class_="boards")
            board_trs = category_div.find_all("tr", id=self._board_id_regex)

            for board_tr in board_trs:
                board_id = regex_match(self._board_id_regex, board_tr.get("id")).group(
                    1
                )
                board_anchor = board_tr.find("a", class_=self._board_id_regex)

                self._set_board(
                    path=(category_id, board_id),
                    url=urljoin(self.base_url, board_anchor.get("href")),
                    origin=response.url,
                    data={},
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
        soup = Soup(response.content)

        subboard_trs = soup.find_all("tr", id=self._board_id_regex)
        for subboard_tr in subboard_trs:
            subboard_id = regex_match(
                self._board_id_regex, subboard_tr.get("id")
            ).group(1)
            subboard_anchor = subboard_tr.find("a", class_=self._board_id_regex)

            self._set_board(
                path=board.path + (subboard_id,),
                url=urljoin(self.base_url, subboard_anchor.get("href")),
                title=subboard_anchor.string,
                are_subboards_fetched=True,
            )

    def _get_node_from_url(self, url: str):
        parsed_url = urlparse(url)
        url_parts = PurePosixPath(parsed_url.path).parts

        if len(url_parts) <= 1:
            return self.root

        if url_parts[1] == "thread":
            response = self._session.get(url)
            soup = Soup(response.content)

            breadcrumbs_div = soup.find("div", class_="nav-tree-wrapper")
            breadcrumb_anchors = breadcrumbs_div.find_all(
                "a", attrs={"itemprop": "item"}
            )

            board_url = urljoin(self.base_url, breadcrumb_anchors[-2].get("href"))

            for cur_board in self._boards:
                if cur_board.url == board_url:
                    thread_link_anchor = soup.find("a", class_="thread-link")
                    thread_id = regex_match(
                        self._thread_class_regex,
                        thread_link_anchor.get_list("class"),
                    ).group(1)
                    return Thread(
                        path=cur_board.path + (thread_id,),
                        url=url,
                        origin="",  # TODO.
                        data={},
                        title="",  # TODO.
                    )
        elif url_parts[1] == "board":
            for cur_board in self._boards:
                if cur_board.path[-1] == url_parts[1]:
                    return cur_board

        raise ValueError

    def _fetch_lazy_subboard(self, board: Board, id: str):
        pass

    def _fetch_lazy_subboards(self, board: Board):
        yield from ()

    def _fetch_board_page_threads(self, board: Board, state: PageState):
        if board == self.root:
            return None

        response = self._session.get(state.url)
        soup = Soup(response.content)

        thread_anchors = soup.find_all("a", class_="thread-link")
        for thread_anchor in thread_anchors:
            thread_id = regex_match(
                self._thread_class_regex, thread_anchor.get_list("class")
            ).group(1)
            yield Thread(
                path=board.path + (thread_id,),
                url=urljoin(self.base_url, thread_anchor.get("href")),
                origin=response.url,
                data={},
                title="",  # TODO.
            )

        next_page_li = soup.try_find("li", class_="next")
        if not next_page_li:
            return None

        next_page_anchor = next_page_li.try_find("a")

        if next_page_anchor and next_page_anchor.try_get("href"):
            return PageState(
                url=urljoin(self.base_url, next_page_anchor.get("href")),
            )

    def _fetch_thread_page_posts(self, thread: Thread, state: PageState):
        response = self._session.get(state.url)
        soup = Soup(response.content)

        message_divs = soup.find_all("div", class_="message")
        for message_div in message_divs:
            yield Post(
                path=thread.path,
                subpath=("TODO",),
                url="",  # TODO.
                origin=response.url,
                data={},
                author="",  # TODO.
                content=str(message_div.encode_contents()),
            )

        next_page_li = soup.try_find("li", class_="next")
        if not next_page_li:
            return None

        next_page_anchor = next_page_li.try_find("a")

        if next_page_anchor and next_page_anchor.try_get("href"):
            return PageState(
                url=urljoin(self.base_url, next_page_anchor.get("href")),
            )
