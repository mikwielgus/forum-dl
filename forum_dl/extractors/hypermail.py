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
class HypermailThread(Thread):
    page_url: str = ""


class HypermailForumExtractor(ForumExtractor):
    _page_href_regex = re.compile(r"^(\d+)/index.html$")
    _post_href_regex = re.compile(r"^(\d+).html$")

    @staticmethod
    def detect(session: CachedSession, url: str):
        response = session.get(normalize_url(url))
        resolved_url = normalize_url(response.url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        generator_meta = soup.find(
            "meta",
            attrs={
                "name": "generator",
                "content": lambda text: text.startswith("hypermail"),
            },
        )
        if not generator_meta:
            return None

        title_title = soup.find("title")

        if (
            title_title.string.endswith("by thread")
            or title_title.string.endswith("by author")
            or title_title.string.endswith("with attachments")
            or title_title.string.endswith("by date")
        ):
            resolved_url = normalize_url(response.url)
            parsed_url = urlparse(resolved_url)
            base_url = urlunparse(
                parsed_url._replace(path=str(PurePosixPath(*path.parts[:-2])))
            )
            return HypermailForumExtractor(session, base_url)
        else:
            return HypermailForumExtractor(session, response.url)

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

        if len(path.parts) >= 2:
            if (
                path.parts[-1] == "index.html"
                or path.parts[-1] == "author.html"
                or path.parts[-1] == "date.html"
                or path.parts[-1] == "subject.html"
            ):
                return self.find_board([path.parts[-2]])

    def _fetch_lazy_subboard(self, board: Board, id: str):
        pass

    def _fetch_lazy_subboards(self, board: Board):
        pass

    def _get_board_page_items(
        self, board: Board, page_url: str, relative_urls: list[str] | None = None
    ):
        relative_urls = relative_urls or []

        if board.url == page_url:
            response = self._session.get(board.url)
            soup = bs4.BeautifulSoup(response.content, "html.parser")

            page_anchors = soup.find_all("a", attrs={"href": self._page_href_regex})
            relative_urls = list(
                reversed([page_anchor.get("href") for page_anchor in page_anchors])
            )

            relative_url = relative_urls.pop()
            return (urljoin(self._base_url, relative_url), relative_urls)

        response = self._session.get(page_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        root_ul = soup.find("ul")
        child_uls = root_ul.find_all("ul")

        for child_ul in child_uls:
            thread_anchor = child_ul.find("a", attrs={"href": self._post_href_regex})
            href = thread_anchor.get("href")
            id = self._post_href_regex.match(href).group(1)
            yield HypermailThread(
                path=[id],
                url=urljoin(self._base_url, href),
                page_url=urljoin(url, "index.html"),
            )

        if relative_urls:
            relative_url = relative_urls.pop()
            return (urljoin(self._base_url, relative_url), relative_urls)

    def _get_thread_page_items(self, thread: Thread, page_url: str):
        if page_url == thread.url:
            page_url = thread.page_url

        response = self._session.get(page_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        root_anchor = soup.find("a", attrs={"href": f"{thread.path[-1]}.html"})

        yield Post(
            path=thread.path + [thread.path[-1]],
            url=thread.url,
        )

        child_ul = root_anchor.find_next("ul")
        child_anchors = soup.find_all("a", attrs={"href": self._post_href_regex})

        for child_anchor in child_anchors:
            href = child_anchor.get("href")
            id = self._post_href_regex.match(href).group(1)

            yield Post(
                path=thread.path + [id],
                url=urljoin(self._base_url, href),
            )
