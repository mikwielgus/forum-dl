# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse, urlunparse
from dataclasses import dataclass
import bs4
import re

from .common import normalize_url
from .common import Extractor, Board, Thread, Post
from ..cached_session import CachedSession


@dataclass
class HypermailThread(Thread):
    page_url: str = ""


class HypermailExtractor(Extractor):
    tests = [
        {
            "url": "https://hypermail-project.org/archive/08/index.html",
            "test_base_url": "https://hypermail-project.org/archive/",
            "test_contents_hash": "83b453b64d8d916717aebda6528f5371d50a3c57",
            "test_item_count": 1155,
        },
        {
            "url": "https://hypermail-project.org/archive/98/0001.html",
            "test_base_url": "https://hypermail-project.org/archive/",
            "test_contents_hash": "4595c5b7ac9f265cdf89acec0069630697680f96",
            "test_item_count": 15,
        },
    ]

    _page_href_regex = re.compile(r"^(\d+)/index.html$")
    _post_href_regex = re.compile(r"^(\d+).html$")

    @staticmethod
    def detect(session: CachedSession, url: str):
        response = session.get(
            normalize_url(url, remove_suffixes=[], append_slash=False)
        )
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

        header_metas = soup.find(
            "meta", attrs={"name": re.compile("^(Author)|(Subject)|(Date)$")}
        )
        title_title = soup.find(
            "title",
            string=re.compile(
                "^.*?(by thread)|(by author)|(with attachments)|(by date)$"
            ),
        )

        if header_metas or title_title:
            parsed_url = urlparse(response.url)
            path = PurePosixPath(parsed_url.path)
            base_url = normalize_url(
                urlunparse(
                    parsed_url._replace(path=str(PurePosixPath(*path.parts[:-2])))
                )
            )
            return HypermailExtractor(session, base_url)

        return HypermailExtractor(session, response.url)

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

        if len(path.parts) >= 2 and self._post_href_regex.match(path.parts[-1]):
            id = path.parts[-1].removesuffix(".html")
            return HypermailThread(
                path=[id], url=url, page_url=urljoin(url, "index.html")
            )

        return self.root

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

        messages_list_div = cast(
            bs4.element.Tag, soup.find("div", class_="messages-list")
        )
        root_ul = cast(bs4.element.Tag, messages_list_div.find("ul"))
        child_uls = root_ul.find_all("ul")

        for child_ul in child_uls:
            if not (
                thread_anchor := child_ul.find(
                    "a", attrs={"href": self._post_href_regex}
                )
            ):
                continue

            href = thread_anchor.get("href")
            id = self._post_href_regex.match(href).group(1)
            yield HypermailThread(
                path=[id],
                url=urljoin(self._base_url, href),
                page_url=urljoin(page_url, "index.html"),
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
        child_anchors = child_ul.find_all("a", attrs={"href": self._post_href_regex})

        for child_anchor in child_anchors:
            href = child_anchor.get("href")
            id = self._post_href_regex.match(href).group(1)

            yield Post(
                path=thread.path + [id],
                url=urljoin(self._base_url, href),
            )
