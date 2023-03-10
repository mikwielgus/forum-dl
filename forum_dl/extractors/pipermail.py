# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse, urlunparse
from dataclasses import dataclass
import bs4
import re

from .common import get_relative_url, normalize_url
from .common import ForumExtractor, Board, Thread, Post
from ..cached_session import CachedSession


@dataclass
class PipermailThread(Thread):
    page_url: str = ""


class PipermailForumExtractor(ForumExtractor):
    tests = [
        {
            "url": "http://lists.opensource.org/mailman/listinfo",
            "test_base_url": "https://lists.opensource.org/",
            "test_boards": {
                ("license-discuss@lists.opensource.org",): {
                    "title": "License-discuss",
                },
                ("license-review@lists.opensource.org",): {
                    "title": "License-review",
                },
                ("publicpolicy@lists.opensource.org",): {
                    "title": "Publicpolicy",
                },
            },
        },
        {
            "url": "http://lists.opensource.org/pipermail/osideas_lists.opensource.org/2020-May/thread.html",
            "test_base_url": "http://lists.opensource.org/",
            "test_contents_hash": "1489f923c4dca729178b3e3233458550d8dddf29",
            "test_item_count": 3,
        },
        {
            "url": "http://lists.opensource.org/pipermail/license-review_lists.opensource.org/2008-January/000031.html",
            "test_base_url": "http://lists.opensource.org/",
            "test_item_count": 22,
        },
    ]

    _listinfo_href_regex = re.compile(r"^listinfo/(.+)$")
    _listinfo_title_regex = re.compile(r"^(.+) Info Page$")
    _pipermail_page_href_regex = re.compile(
        r"^\d\d\d\d-(January|February|March|April|May|June|July|August|September|October|November|December)/thread.html$"
    )
    _post_href_regex = re.compile(r"^(\d+).html$")
    _root_post_comment_regex = re.compile(r"^0 ([^-]+)- $")
    _child_post_comment_regex = re.compile(r"^(1|2|3) ([^-]+)-.* $")

    @staticmethod
    def detect(session: CachedSession, url: str):
        response = session.get(url)
        resolved_url = normalize_url(response.url)

        parsed_url = urlparse(resolved_url)
        path = PurePosixPath(parsed_url.path)

        if len(path.parts) >= 4 and path.parts[-4] == "pipermail":
            return PipermailForumExtractor(
                session,
                urlunparse(
                    parsed_url._replace(path=str(PurePosixPath(*path.parts[:-4])))
                ),
            )
        elif len(path.parts) >= 3 and path.parts[-3] == "pipermail":
            return PipermailForumExtractor(
                session,
                urlunparse(
                    parsed_url._replace(path=str(PurePosixPath(*path.parts[:-3])))
                ),
            )
        elif len(path.parts) >= 2 and (
            path.parts[-2] == "pipermail" or path.parts[-2] == "mailman"
        ):
            return PipermailForumExtractor(
                session,
                urlunparse(
                    parsed_url._replace(path=str(PurePosixPath(*path.parts[:-2])))
                ),
            )
        elif len(path.parts) >= 1 and (
            path.parts[-1] == "pipermail" or path.parts[-1] == "mailman"
        ):
            return PipermailForumExtractor(
                session,
                urlunparse(
                    parsed_url._replace(path=str(PurePosixPath(*path.parts[:-1])))
                ),
            )

    def _fetch_top_boards(self):
        pass

    def _fetch_subboards(self, board: Board):
        pass

    def _get_node_from_url(self, url: str):
        response = self._session.get(url)
        resolved_url = normalize_url(response.url)

        if resolved_url == self._base_url:
            return self.root

        parsed_url = urlparse(resolved_url)
        path = PurePosixPath(parsed_url.path)

        if len(path.parts) >= 4 and path.parts[-4] == "pipermail":
            if path.parts[-1] == "thread.html":
                return self.find_board([path.parts[-3]])

            id = path.parts[-1].removesuffix(".html")
            board_id = path.parts[-3]

            # TODO: Properly read board name instead.
            board_id.replace("_", "@")

            return PipermailThread(
                path=[board_id] + [id], url=url, page_url=urljoin(url, "thread.html")
            )
        elif len(path.parts) >= 3 and path.parts[-3] == "pipermail":
            return self.find_board([path.parts[-2]])
        elif (
            len(path.parts) >= 3
            and path.parts[-3] == "mailman"
            and path.parts[-2] == "listinfo"
        ):
            return self.find_board([path.parts[-1]])
        elif len(path.parts) >= 2:
            if path.parts[-2] == "pipermail":
                return self.find_board([path.parts[-1]])

            return self.root

        raise ValueError

    def _fetch_lazy_subboard(self, board: Board, id: str):
        nice_id = id.replace("@", "_")

        url = normalize_url(urljoin(self._base_url, f"mailman/listinfo/{nice_id}"))
        response = self._session.get(url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        title = ""

        if isinstance(title_title := soup.find("title"), bs4.Tag):
            title = self._listinfo_title_regex.match(title_title.string).group(1)

        content = soup.find("p").find_all("p")[1].string
        self._set_board(path=[id], url=url, title=title, content=content)

    def _fetch_lazy_subboards(self, board: Board):
        # TODO use a for loop over _fetch_lazy_subboard() instead
        url = normalize_url(urljoin(self._base_url, f"mailman/listinfo"))
        response = self._session.get(url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        listinfo_anchors = soup.find_all("a", attrs={"href": self._listinfo_href_regex})

        for listinfo_anchor in listinfo_anchors:
            href = listinfo_anchor.get("href")
            id = self._listinfo_href_regex.match(href).group(1)
            self._fetch_lazy_subboard(board, id)

    def _get_board_page_items(
        self, board: Board, page_url: str, relative_urls: list[str] | None = None
    ):
        if board == self.root:
            return None

        relative_urls = relative_urls or []

        if board.url == page_url:
            id = board.path[0]
            pipermail_url = urljoin(self._base_url, f"pipermail/{id}")

            response = self._session.get(pipermail_url)
            soup = bs4.BeautifulSoup(response.content, "html.parser")

            page_anchors = soup.find_all(
                "a", attrs={"href": self._pipermail_page_href_regex}
            )

            relative_urls = list(
                reversed([page_anchor.get("href") for page_anchor in page_anchors])
            )

            relative_url = relative_urls.pop()
            return (
                urljoin(urljoin(self._base_url, f"pipermail/{id}/"), relative_url),
                relative_urls,
            )

        response = self._session.get(page_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        root_comments = soup.find_all(
            string=lambda text: isinstance(text, bs4.element.Comment)
            and bool(self._root_post_comment_regex.match(text))
        )

        for root_comment in root_comments:
            thread_anchor = root_comment.find_next(
                "a", attrs={"href": self._post_href_regex}
            )
            href = thread_anchor.get("href")
            id = self._post_href_regex.match(href).group(1)

            yield PipermailThread(
                path=board.path + [id],
                url=urljoin(self._base_url, href),
                page_url=page_url,
            )

        if relative_urls:
            relative_url = relative_urls.pop()
            board_id = board.path[0]
            return (
                urljoin(
                    urljoin(self._base_url, f"pipermail/{board_id}/"), relative_url
                ),
            )

    def _get_thread_page_items(self, thread: PipermailThread, page_url: str):
        if page_url == thread.url:
            page_url = thread.page_url

        response = self._session.get(page_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        root_anchor = soup.find("a", attrs={"href": f"{thread.path[-1]}.html"})
        root_comment = root_anchor.find_previous(
            string=lambda text: isinstance(text, bs4.element.Comment)
        )

        yield Post(
            path=thread.path + [thread.path[-1]],
            url=thread.url,
        )

        thread_long_id = self._root_post_comment_regex.match(root_comment.string).group(
            1
        )

        child_comments = soup.find_all(
            string=lambda text: isinstance(text, bs4.element.Comment)
            and bool(self._child_post_comment_regex.match(text))
            and (
                text.startswith(f"1 {thread_long_id}-")
                or text.startswith(f"2 {thread_long_id}-")
                or text.startswith(f"3 {thread_long_id}-")
            )
        )

        for child_comment in child_comments:
            thread_anchor = child_comment.find_next(
                "a", attrs={"href": self._post_href_regex}
            )
            href = thread_anchor.get("href")
            id = self._post_href_regex.match(href).group(1)

            yield Post(
                path=thread.path + [id],
                url=urljoin(self._base_url, href),
            )
