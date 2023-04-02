# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse, parse_qs

from .common import get_relative_url, normalize_url
from .common import Extractor, Board, Thread, Post
from ..cached_session import CachedSession
from ..soup import Soup


class PhpbbExtractor(Extractor):
    tests = [
        {
            "url": "https://phpbb.com/community",
            "test_base_url": "https://www.phpbb.com/community/",
            "test_boards": {
                ("47",): {
                    "title": "General",
                },
                ("551",): {
                    "title": "Support Forums",
                },
                ("451",): {
                    "title": "Extensions Forums",
                },
                ("471",): {
                    "title": "Styles Forums",
                },
                ("52",): {
                    "title": "Non-support Specific",
                },
                ("48",): {
                    "title": "phpBB Archives",
                },
            },
        },
        {
            "url": "https://phpbb.com/community/viewforum.php?f=556",
            "test_base_url": "https://www.phpbb.com/community/",
            "test_boards": {
                ("551", "556", "561"): {
                    "title": "[3.2.x] Convertors",
                },
                ("551", "556", "566"): {
                    "title": "[3.2.x] Translations",
                },
            },
        },
        {
            "url": "https://www.phpbb.com/community/viewtopic.php?t=2377611",
            "test_base_url": "https://www.phpbb.com/community/",
            "test_contents_hash": "106811a36319a20612b9b08453134fe7efe256a6",
            "test_item_count": 7,
        },
        {
            "url": "https://www.phpbb.com/community/viewtopic.php?t=2534156",
            "test_base_url": "https://www.phpbb.com/community/",
            "test_contents_hash": "ade82b481979311829ea915a396ac57754ff04f0",
            "test_item_count": 1,
        },
    ]

    @staticmethod
    def _detect(session: CachedSession, url: str):
        response = session.get(
            urljoin(
                normalize_url(url, remove_suffixes=["viewforum.php", "viewtopic.php"]),
                "viewforum.php",
            )
        )

        if not "The forum you selected does not exist." in str(response.text):
            return None

        return PhpbbExtractor(
            session,
            normalize_url(
                response.url, remove_suffixes=["viewforum.php", "viewtopic.php"]
            ),
        )

    def _is_viewforum_url(self, url: str):
        parsed_url = urlparse(url)
        path = PurePosixPath(str(parsed_url.path))

        if len(path.parts) != 1:
            try:
                get_relative_url(url, self._base_url)
            except ValueError:
                return False

        if path.parts[-1] != "viewforum.php":
            return False

        parsed_query = parse_qs(parsed_url.query)

        if "f" not in parsed_query:
            return False

        return True

    def _is_viewforum_pagination_url(self, url: str):
        if not self._is_viewforum_url(url):
            return False

        parsed_url = urlparse(url)
        parsed_query = parse_qs(parsed_url.query)

        if not {"f", "start"} <= parsed_query.keys():
            return False

        return True

    def _is_viewtopic_url(self, url: str, thread_id: int | None = None):
        parsed_url = urlparse(url)
        path = PurePosixPath(str(parsed_url.path))

        if len(path.parts) != 1:
            try:
                get_relative_url(url, self._base_url)
            except ValueError:
                return False

        if path.parts[-1] != "viewtopic.php":
            return False

        parsed_query = parse_qs(parsed_url.query)

        if "t" not in parsed_query:
            return False

        return True

    def _is_viewtopic_pagination_url(self, url: str, thread_id: int | None = None):
        if not self._is_viewtopic_url(url, thread_id):
            return False

        parsed_url = urlparse(url)
        parsed_query = parse_qs(parsed_url.query)

        if not {"t", "start"} <= parsed_query.keys():
            return False

        return True

    def _is_viewprofile_url(self, url: str):
        parsed_url = urlparse(url)
        path = PurePosixPath(str(parsed_url.path))

        if len(path.parts) != 1:
            try:
                get_relative_url(url, self._base_url)
            except ValueError:
                return False

        if path.parts[-1] != "memberlist.php":
            return False

        parsed_query = parse_qs(parsed_url.query)

        if "mode" not in parsed_query or parsed_query["mode"][0] != "viewprofile":
            return False

        return True

    def _fetch_top_boards(self):
        self.root.are_subboards_fetched = True

    def _fetch_subboards(self, board: Board):
        if board is self.root:
            request_url = urljoin(self._base_url, "index.php")
        else:
            request_url = urljoin(self._base_url, f"viewforum.php?f={board.path[-1]}")

        response = self._session.get(request_url)

        try:
            get_relative_url(response.url, self._base_url)
        except ValueError:
            return

        soup = Soup(response.content)
        breadcrumbs = soup.find(class_="breadcrumbs")

        if board is not self.root and breadcrumbs:
            breadcrumb_anchors = breadcrumbs.find_all(
                "a", attrs={"href": self._is_viewforum_url}
            )

            path: list[str] = []
            href: str = ""
            title: str = ""

            for breadcrumb_anchor in breadcrumb_anchors:
                href = breadcrumb_anchor.get("href")
                parsed_href = urlparse(href)
                parsed_query = parse_qs(parsed_href.query)
                href_board_id = parsed_query["f"][0]

                path.append(href_board_id)
                title = breadcrumb_anchor.string

            if path:
                cur_board = self._set_board(
                    replace_path=board.path,
                    path=path,
                    url=urljoin(self._base_url, href),
                    title=title,
                    are_subboards_fetched=True,
                )

        viewforum_anchors = soup.find_all("a", attrs={"href": self._is_viewforum_url})

        for viewforum_anchor in viewforum_anchors:
            parsed_href = urlparse(viewforum_anchor.get("href"))
            parsed_query = parse_qs(parsed_href.query)
            href_board_id = parsed_query["f"][0]

            for cur_board in self._boards:
                if cur_board is not self.root and cur_board.path[-1] == href_board_id:
                    break
            else:
                self._set_board(path=[href_board_id], are_subboards_fetched=True)

    def _resolve_url(self, url: str):
        return normalize_url(self._session.get(url).url, keep_queries=["f", "t"])

    def _get_node_from_url(self, url: str):
        response = self._session.get(url)
        resolved_url = normalize_url(response.url, keep_queries=["f", "t"])

        parsed_url = urlparse(resolved_url)
        parts = PurePosixPath(parsed_url.path).parts

        if parts[-1] == "viewforum.php":
            parsed_query = parse_qs(parsed_url.query)

            if "f" not in parsed_query:
                return self.root

            id = parsed_query["f"][0]

            for board in self._boards:
                if board is not self.root and board.path[-1] == id:
                    return board

            raise ValueError
        elif parts[-1] == "viewtopic.php":
            id = parse_qs(parsed_url.query)["t"][0]
            soup = Soup(response.content)
            breadcrumbs = soup.find(class_="breadcrumbs")

            breadcrumb_anchors = breadcrumbs.find_all(
                "a", attrs={"href": self._is_viewforum_url}
            )

            board = self.root

            for breadcrumb_anchor in breadcrumb_anchors:
                href = breadcrumb_anchor.get("href")
                parsed_href = urlparse(href)
                parsed_query = parse_qs(parsed_href.query)
                href_board_id = parsed_query["f"][0]

                board = board.subboards[href_board_id]

            return Thread(
                path=board.path + [id],
                url=resolved_url,
            )
        elif normalize_url(resolved_url) == self._base_url:
            return self.root

        raise ValueError

    def _fetch_lazy_subboard(self, board: Board, id: str):
        pass

    def _fetch_lazy_subboards(self, board: Board):
        yield from ()

    def _get_board_page_threads(self, board: Board, page_url: str, *args: Any):
        if board == self.root:
            return None

        parsed_url = urlparse(page_url)
        board_id = parse_qs(parsed_url.query)["f"]

        parsed_query = parse_qs(parsed_url.query)
        if "start" in parsed_query:
            cur_start = int(parsed_query["start"][0])
        else:
            cur_start = 0

        response = self._session.get(page_url)
        soup = Soup(response.content)
        topic_anchors = soup.find_all(
            "a", class_="topictitle", attrs={"href": self._is_viewtopic_url}
        )

        if not topic_anchors:
            topic_anchors = soup.find_all("a", attrs={"href": self._is_viewtopic_url})

        for topic_anchor in topic_anchors:
            href = urljoin(self._base_url, topic_anchor.get("href"))
            parsed_href = urlparse(href)
            parsed_query = parse_qs(parsed_href.query)
            thread_id = parsed_query["t"][0]

            yield Thread(
                path=board.path + [thread_id],
                url=href,
                title="",
            )

        pagination_anchors = soup.find_all(
            "a", attrs={"href": self._is_viewforum_pagination_url}
        )

        # Look for pagination links. Always choose the one with the smallest increment.
        min_start = None

        for pagination_anchor in pagination_anchors:
            parsed_href = urlparse(pagination_anchor.get("href"))
            parsed_query = parse_qs(parsed_href.query)
            start = int(parsed_query["start"][0])

            if start > cur_start and (not min_start or start < min_start):
                min_start = start

        if min_start:
            return urljoin(
                self._base_url, f"viewforum.php?f={board_id}&start={min_start}"
            )

    def _get_thread_page_posts(self, thread: Thread, page_url: str, *args: Any):
        parsed_url = urlparse(page_url)
        thread_id = parse_qs(parsed_url.query)["t"][0]

        parsed_query = parse_qs(parsed_url.query)
        if "start" in parsed_query:
            cur_start = int(parsed_query["start"][0])
        else:
            cur_start = 0

        response = self._session.get(page_url)
        soup = Soup(response.content)
        content_divs = soup.find_all("div", class_={"content": "message-content"})

        for content_div in content_divs:
            viewprofile_anchor = content_div.find_previous(
                "a",
                attrs={"href": self._is_viewprofile_url},
            )

            yield Post(
                path=thread.path + ["x"],  # TODO: We use a dummy path for now.
                username=viewprofile_anchor.string,
                content=str(content_div.encode_contents()),
            )

        pagination_anchors = soup.find_all(
            "a",
            attrs={"href": self._is_viewtopic_pagination_url},
        )

        # Look for pagination links. Always choose the one with the smallest increment.
        min_start = None

        for pagination_anchor in pagination_anchors:
            parsed_href = urlparse(pagination_anchor.get("href"))
            parsed_query = parse_qs(parsed_href.query)
            start = int(parsed_query["start"][0])

            if start > cur_start and (not min_start or start < min_start):
                min_start = start

        if min_start:
            return urljoin(
                self._base_url, f"viewtopic.php?t={thread_id}&start={min_start}"
            )
