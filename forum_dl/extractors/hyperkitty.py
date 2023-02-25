# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse
import bs4

from .common import get_relative_url, normalize_url
from .common import ForumExtractor, Board, Thread, Post
from ..cached_session import CachedSession


class HyperkittyForumExtractor(ForumExtractor):
    tests = []

    @staticmethod
    def detect(session: CachedSession, url: str):
        response = session.get(url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        if extractor := HyperkittyForumExtractor.detect_postorius(session, url, soup):
            return extractor

        if extractor := HyperkittyForumExtractor.detect_hyperkitty(session, url, soup):
            return extractor

    @staticmethod
    def detect_postorius(session: CachedSession, url: str, soup: bs4.BeautifulSoup):
        if not (footer := soup.find("footer")):
            return None

        if not (doc_anchor := footer.find("a", string="Postorius Documentation")):
            return None

        # if navbar_brand_anchor := soup.find("a", class_="nav-item"):
        if not (nav_link_anchors := soup.find_all("a", class_="nav-link")):
            return None

        base_url = normalize_url(urljoin(url, nav_link_anchors[1].get("href")))
        return HyperkittyForumExtractor(session, base_url)

    @staticmethod
    def detect_hyperkitty(session: CachedSession, url: str, soup: bs4.BeautifulSoup):
        if not (footer := soup.find("footer")):
            return None

        if not (doc_anchor := footer.find("a", string="HyperKitty")):
            return None

        if not (navbar_brand_anchor := soup.find("a", class_="navbar-brand")):
            return None

        base_url = normalize_url(urljoin(url, navbar_brand_anchor.get("href")))
        return HyperkittyForumExtractor(session, base_url)

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

        if len(path.parts) >= 2 and path.parts[-2] == "list":
            return self.find_board([path.parts[-1]])

        raise ValueError

    def _fetch_lazy_subboard(self, board: Board, id: str):
        url = normalize_url(urljoin(self._base_url, f"list/{id}"))
        response = self._session.get(url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        if title := soup.find("h2"):
            title = title.encode_contents().strip()

        self._set_board(path=[id], url=url, title=title)

    def _fetch_lazy_subboards(self, board: Board):
        href: str = ""
        url: str = self._base_url

        while href != "#":
            response = self._session.get(url)
            soup = bs4.BeautifulSoup(response.content, "html.parser")
            list_anchors = soup.find_all("a", class_="list-name")

            for list_anchor in list_anchors:
                url = urljoin(self._base_url, list_anchor.get("href"))
                self._set_board(path=[url], url=url)

            page_link_anchors = soup.find_all("a", class_="page-link")
            next_page_anchor = page_link_anchors[-1]

            href = next_page_anchor.get("href")
            url = urljoin(self._base_url, href)

    def _get_board_page_items(self, board: Board, page_url: str, cur_page: int = 1):
        response = self._session.get(page_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        thread_spans = soup.find_all("span", class_="thread-title")

        for thread_span in thread_spans:
            anchor = thread_span.find("a")
            yield Thread(path=board.path + [anchor.get("name")], url=anchor.get("href"))

        return (urljoin(page_url, f"latest?page={cur_page}"), cur_page + 1)

    def _get_thread_page_items(self, thread: Thread, page_url: str):
        if thread.url == page_url:
            page_url = urljoin(page_url, "replies?sort=thread")

        response = self._session.get(page_url)
        json = response.json()

        replies_html = json["replies_html"]
        soup = bs4.BeautifulSoup(replies_html)
        email_body_divs = soup.find_all("div", class_="email-body")

        for email_body_div in email_body_divs:
            yield Post(
                path=thread.path + ["x"],  # TODO: We use a dummy path for now.
                content=email_body_div.encode_contents(),
            )

        # soup = bs4.BeautifulSoup(response.content, "html.parser")

        if json["more_pending"]:
            next_offset = json["next_offset"]
            return (urljoin(page_url, f"replies?sort=thread&offset={next_offset}"),)
