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


class XenforoForumExtractor(ForumExtractor):
    _category_class_regex = re.compile(r"^block--category(\d+)$")
    _board_class_regex = re.compile(r"^node--id(\d+)$")
    _thread_class_regex = re.compile(r"^js-threadListItem-(\d+)$")

    @staticmethod
    def detect(session: CachedSession, url: str):
        response = session.get(
            normalize_url(url, remove_suffixes=[], append_slash=False)
        )
        soup = bs4.BeautifulSoup(response.content, "html.parser")
        xenforo_anchor = soup.find(
            "a",
            attrs={"rel": "sponsored noopener"},
        )

        if not xenforo_anchor:
            return None

        return XenforoForumExtractor(session, normalize_url(response.url))

    def _fetch_top_boards(self):
        self.root.are_subboards_fetched = True

        response = self._session.get(self._base_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        block_category_divs = soup.find_all("div", class_=self._category_class_regex)
        for block_category_div in block_category_divs:
            category_header = block_category_div.find("h2", class_="block-header")
            category_anchor = category_header.find("a")
            category_id = self._category_class_regex.match(
                block_category_div.get("class")[-1]
            ).group(1)

            self._set_board(
                path=[category_id],
                title=category_anchor.string.strip(),
                are_subboards_fetched=True,
            )

            node_id_divs = block_category_div.find_all(
                "div", class_=self._board_class_regex
            )

            for node_id_div in node_id_divs:
                subboard_id = self._board_class_regex.match(
                    node_id_div.get("class")[1]
                ).group(1)

                node_description_anchor = node_id_div.find(
                    "a", attrs={"data-shortcut": "node-description"}
                )

                href = node_description_anchor.get("href")

                self._set_board(
                    path=[category_id] + [subboard_id],
                    url=urljoin(self._base_url, href),
                    title=node_description_anchor.string.strip(),
                )

    def _fetch_subboards(self, board: Board):
        pass

    def _get_node_from_url(self, url: str):
        response = self._session.get(url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        breadcrumbs_ul = soup.find("ul", class_="p-breadcrumbs")
        breadcrumb_anchors = breadcrumbs_ul.find_all("a", attrs={"itemprop": "item"})

        if len(breadcrumb_anchors) <= 1:
            return self.root

        # Thread.
        if soup.find("article"):
            board_href = breadcrumb_anchors[-2].get("href")

            for cur_board in self._boards:
                if cur_board.url == board_href:
                    return Thread(
                        path=cur_board.path + [id], url=urljoin(self._base_url, url)
                    )
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

        thread_divs = soup.find_all("div", class_=self._thread_class_regex)

        for thread_div in thread_divs:
            thread_id = self._thread_class_regex.match(
                thread_div.get("class")[-1]
            ).group(1)

            title_div = thread_div.find("div", class_="structItem-title")
            title_anchor = title_div.find("a")

            href = title_anchor.get("href")
            url = urljoin(self._base_url, href)

            yield Thread(path=board.path + [thread_id], url=url)

        next_page_anchor = soup.find("a", class_="pageNav-jump--next")

        if next_page_anchor:
            return (urljoin(self._base_url, next_page_anchor.get("href")), cur_page + 1)

    def _get_thread_page_items(self, thread: Thread, page_url: str):
        response = self._session.get(page_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        bbwrapper_divs = soup.find_all("div", class_="bbWrapper")

        for bbwrapper_div in bbwrapper_divs:
            yield Post(
                path=thread.path,
                content=str(bbwrapper_div.encode_contents()),
            )

        next_page_anchor = soup.find("a", class_="pageNav-jump--next")

        if next_page_anchor:
            return (next_page_anchor.get("href"), cur_page + 1)
