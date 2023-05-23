# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from dataclasses import dataclass
from urllib.parse import urljoin
import dateutil.parser
import re

from .common import normalize_url, regex_match
from .common import Extractor, ExtractorOptions, Board, Thread, Post, PageState
from ..session import Session
from ..soup import Soup


@dataclass  # (kw_only=True)
class SimplemachinesPageState(PageState):
    page: int


class SimplemachinesExtractor(Extractor):
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
            # "test_contents_hash": "9716f8e58a4bb20934ae026d5d1b7d0b5c9bb449",
            "test_item_count": 6,
        },
        {
            "url": "https://www.simplemachines.org/community/index.php?topic=581247.0",
            "test_base_url": "https://www.simplemachines.org/community/",
            "test_contents_hash": "bafb2382778b3717f490001548106f60b00b06ae",
            "test_item_count": 1,
        },
    ]

    _category_id_regex = re.compile(r"^c(\d+)$")
    _board_id_regex = re.compile(r"^b(\d+)$")
    _span_id_regex = re.compile(r"^msg_(\d+)$")
    _div_id_regex = re.compile(r"^msg_(\d+)$")
    _subject_id_regex = re.compile(r"^subject_(\d+)$")

    @staticmethod
    def _detect(session: Session, url: str, options: ExtractorOptions):
        response = session.try_get(url, should_cache=True, should_retry=False)
        soup = Soup(response.content)

        link = soup.find("link", attrs={"rel": "contents"})
        base_url = normalize_url(link.get("href"))

        simplemachines_anchor = soup.find(
            "a",
            attrs={
                "href": "https://www.simplemachines.org",
                "title": "Simple Machines",
            },
        )

        if simplemachines_anchor:
            return SimplemachinesExtractor(session, base_url, options)

    def _fetch_top_boards(self):
        self._are_subboards_fetched[self.root.path] = True

        response = self._session.get(self.base_url, should_cache=True)
        soup = Soup(response.content)

        category_anchors = soup.find_all("a", id=self._category_id_regex)
        for category_anchor in category_anchors:
            category_id = regex_match(
                self._category_id_regex, category_anchor.get("id")
            ).group(1)
            category_title = str(category_anchor.next_sibling).strip()

            self._set_board(
                path=(category_id,),
                url=urljoin(response.url, f"index.php#c{category_id}"),
                origin=response.url,
                data={},
                title=category_title,
                are_subboards_fetched=True,
            )

            for parent in category_anchor.parents:
                board_anchors = parent.find_all("a", id=self._board_id_regex)

                if board_anchors:
                    for board_anchor in board_anchors:
                        board_id = regex_match(
                            self._board_id_regex, board_anchor.get("id")
                        ).group(1)

                        self._set_board(
                            path=(category_id, board_id),
                            url=board_anchor.get("href"),
                            origin=response.url,
                            data={},
                            title=str(board_anchor.string).strip(),
                            are_subboards_fetched=True,
                        )
                    break

    def _fetch_subboards(self, board: Board):
        if not board.url:
            return

        # Don't fetch top boards.
        if len(board.path) <= 1:
            return

        response = self._session.get(board.url, should_cache=True)
        soup = Soup(response.content)

        subboard_anchors = soup.find_all("a", attrs={"id": self._board_id_regex})

        for subboard_anchor in subboard_anchors:
            subboard_id = regex_match(
                self._board_id_regex, subboard_anchor.get("id")
            ).group(1)
            self._set_board(
                path=board.path + (subboard_id,),
                url=subboard_anchor.get("href"),
                origin=response.url,
                data={},
                title=str(subboard_anchor.string).strip(),
                are_subboards_fetched=True,
            )

    def _resolve_url(self, url: str):
        return normalize_url(
            self._session.get(url, should_cache=True).url,
            append_slash=False,
            keep_queries=["board", "topic"],
        )

    def _get_node_from_url(self, url: str):
        response = self._session.get(url, should_cache=True)
        soup = Soup(response.content)

        breadcrumbs = soup.try_find(class_="navigate_section")
        if not breadcrumbs:
            breadcrumbs = soup.find(class_="linktree")

        breadcrumb_anchors = breadcrumbs.find_all("a")

        # Thread.
        if soup.try_find("div", id="forumposts"):
            breadcrumb_urls = [anchor.get("href") for anchor in breadcrumb_anchors]
            board = self.find_board_from_urls(tuple(breadcrumb_urls[1:-1]))

            topic_input = soup.find("input", attrs={"name": "topic"})
            thread_id = topic_input.get("value")
            title_title = soup.find("title")

            return Thread(
                path=board.path + (thread_id,),
                url=url,
                origin=response.url,
                data={},
                title=str(title_title.string),
            )

        # Board.
        else:
            self._fetch_lower_boards(self.root)

            board_href = self._resolve_url(breadcrumb_anchors[-1].get("href"))

            for cur_board in self._boards:
                if cur_board.url == board_href:
                    return cur_board

        raise ValueError

    def _fetch_lazy_subboard(self, board: Board, subboard_id: str):
        pass

    def _fetch_lazy_subboards(self, board: Board):
        yield from ()

    def _fetch_board_page_threads(self, board: Board, state: PageState):
        if board == self.root:
            return None

        if not state.url:
            return None

        if state.url == board.url:
            state = SimplemachinesPageState(url=state.url, page=1)

        state = cast(SimplemachinesPageState, state)

        response = self._session.get(state.url)
        soup = Soup(response.content)

        msg_spans = soup.find_all("span", id=self._span_id_regex)

        for msg_span in msg_spans:
            thread_id = regex_match(self._span_id_regex, msg_span.get("id")).group(1)
            msg_anchor = msg_span.tags[0]

            yield Thread(
                path=board.path + (thread_id,),
                url=msg_anchor.get("href"),
                origin=response.url,
                data={},
                title=str(msg_anchor.string),
            )

        next_page_anchor = soup.try_find(
            "a", class_="nav_page", string=str(state.page + 1)
        )
        if next_page_anchor:
            return SimplemachinesPageState(
                url=next_page_anchor.get("href"), page=state.page + 1
            )

    def _fetch_thread_page_posts(self, thread: Thread, state: PageState):
        if state.url == thread.url:
            state = SimplemachinesPageState(url=state.url, page=1)

        state = cast(SimplemachinesPageState, state)

        response = self._session.get(state.url)
        soup = Soup(response.content)

        post_wrapper_divs = soup.find_all("div", class_="post_wrapper")

        for post_wrapper_div in post_wrapper_divs:
            msg_div = post_wrapper_div.find("div", id=self._div_id_regex)
            subject_div = post_wrapper_div.find("div", id=self._subject_id_regex)

            time_div = subject_div.find_next("a", class_="smalltext")

            # This is ugly, but it's the best I can do for now.
            date = regex_match(
                re.compile(
                    r"(January|February|March|April|May|June|July|August|September|October|November|December) [a-zA-Z0-9,: ]+"
                ),
                time_div.string,
            ).group(0)

            poster_div = post_wrapper_div.find("div", class_="poster")
            poster_h4 = poster_div.find("h4")

            yield Post(
                path=thread.path,
                subpath=(regex_match(self._div_id_regex, msg_div.get("id")).group(1),),
                url=subject_div.find("a").get("href"),
                origin=response.url,
                data={},
                author=str(poster_h4.find("a").string),
                creation_time=dateutil.parser.parse(date).isoformat(),
                content="".join(str(v) for v in msg_div.contents).strip(),
            )

        next_page_anchor = soup.try_find("a", class_="nav_page", string=str(state.page))
        if next_page_anchor:
            return SimplemachinesPageState(
                url=next_page_anchor.get("href"), page=state.page + 1
            )
