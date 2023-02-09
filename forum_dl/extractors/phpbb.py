# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs
import bs4

from .common import get_relative_url, normalize_url
from .common import ForumExtractor, Board, Thread, Post
from ..cached_session import CachedSession


class PhppbbForumExtractor(ForumExtractor):
    tests = []

    @staticmethod
    def detect(session: CachedSession, url: str):
        response = session.get(urljoin(normalize_url(url), "viewforum.php"))

        if not "The forum you selected does not exist." in str(response.text):
            return None

        parsed_url = urlparse(response.url)
        parts = PurePosixPath(parsed_url.path).parts
        base_path = str(PurePosixPath().joinpath(*parts[:-1]).relative_to("/"))
        base_url = normalize_url(urlunparse(parsed_url._replace(path=base_path)))

        return PhpbbForumExtractor(session, normalize_url(base_url))

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

    def fetch(self):
        # Recursively crawl the site for all `viewforum.php` links. We need to go below depth=1
        # because some forums don't have links to top-level boards at index.php.

        board_ids: list[int | None] = [None]

        i = 0
        while i < len(board_ids):
            board_id = board_ids[i]

            if board_id:
                request_url = urljoin(self._base_url, f"viewforum.php?f={board_id}")
            else:
                request_url = urljoin(self._base_url, "index.php")

            response = self._session.get(request_url)
            soup = bs4.BeautifulSoup(response.content, "html.parser")

            # We determine top board ids from breadcrumbs, as I found them present in all forums.

            breadcrumbs = soup.find(class_="breadcrumbs")

            if breadcrumbs:
                breadcrumb_anchors: bs4.element.ResultSet[Any] = breadcrumbs.find_all(
                    "a", attrs={"href": self._is_viewforum_url}
                )

                board = self.root

                for breadcrumb_anchor in breadcrumb_anchors:
                    href = breadcrumb_anchor.get("href")
                    parsed_href = urlparse(href)
                    parsed_query = parse_qs(parsed_href.query)
                    href_board_id = parsed_query["f"][0]

                    if href_board_id not in board.lazy_subboards:
                        board.lazy_subboards[href_board_id] = Board(
                            path=board.path + [href_board_id],
                            url=urljoin(self._base_url, href),
                            title=breadcrumb_anchor.string,
                        )

                    board = board.lazy_subboards[href_board_id]

            viewforum_anchors = soup.find_all(
                "a", attrs={"href": self._is_viewforum_url}
            )

            for viewforum_anchor in viewforum_anchors:
                parsed_href = urlparse(viewforum_anchor.get("href"))
                parsed_query = parse_qs(parsed_href.query)
                href_board_id = int(parsed_query["f"][0])

                if href_board_id not in board_ids:
                    board_ids.append(href_board_id)

            i += 1

    def _resolve_url(self, url: str):
        return normalize_url(self._session.get(url).url)

    def _get_node_from_url(self, url: str):
        resolved_url = normalize_url(self._session.get(url).url)

        parsed_url = urlparse(resolved_url)
        parts = PurePosixPath(parsed_url.path).parts

        if parts[-1] == "viewforum.php":
            parsed_query = parse_qs(parsed_url.query)

            if "f" not in parsed_query:
                return self.root

            id = parsed_query["f"][0]

            def dfs(board: Board) -> Board | None:
                if board.path[-1] == id:
                    return board

                for _, subboard in self.root.lazy_subboards.items():
                    if result := dfs(subboard):
                        return result

            if result := dfs(self.root):
                return result

            raise ValueError
        elif parts[-1] == "viewtopic.php":
            id = parse_qs(parsed_url.query)["t"][0]
            breadcrumbs = soup.find(class_="breadcrumbs")

            breadcrumb_anchors: bs4.element.ResultSet[Any] = breadcrumbs.find_all(
                "a", attrs={"href": self._is_viewforum_url}
            )

            board = self.root

            for breadcrumb_anchor in breadcrumb_anchors:
                href = breadcrumb_anchor.get("href")
                parsed_href = urlparse(href)
                parsed_query = parse_qs(parsed_href.query)
                href_board_id = parsed_query["f"][0]

                board = board.lazy_subboards[href_board_id]

            return Thread(
                path=board.path + [id],
                url=resolved_url,
                slug=slug,
            )
        elif normalize_url(resolved_url) == self._base_url:
            return self.root

        raise ValueError

    def _fetch_subboard(self, board: Board, id: str):
        pass

    def _get_board_page_items(self, board: Board, page_url: str):
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
        soup = bs4.BeautifulSoup(response.content, "html.parser")
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
                username=topic_anchor.string,
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
            return (urljoin(self._base_url, f"viewforum.php?f={id}&start={min_start}"),)

    def _get_thread_page_items(self, thread: Thread, page_url: str):
        parsed_url = urlparse(page_url)
        thread_id = parse_qs(parsed_url.query)["t"][0]

        parsed_query = parse_qs(parsed_url.query)
        if "start" in parsed_query:
            cur_start = int(parsed_query["start"][0])
        else:
            cur_start = 0

        response = self._session.get(page_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")
        content_divs = soup.find_all("div", class_={"content": "message-content"})

        for content_div in content_divs:
            viewprofile_anchor = content_div.find_previous(
                "a",
                attrs={"href": self._is_viewprofile_url},
            )

            yield Post(
                path=thread.path + ["x"],  # TODO: We use a dummy path for now.
                title="",
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
            return (
                urljoin(
                    self._base_url, f"viewtopic.php?t={thread_id}&start={min_start}"
                ),
            )
