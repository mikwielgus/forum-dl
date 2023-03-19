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
    tests = [
        {
            "url": "https://xenforo.com/community",
            "test_base_url": "https://xenforo.com/community/",
            "test_boards": {
                ("1",): {
                    "title": "Official forums",
                },
                ("1", "2"): {
                    "title": "Announcements",
                },
                ("1", "3"): {
                    "title": "Have you seen...?",
                },
                ("1", "19"): {
                    "title": "Frequently asked questions",
                },
                ("17",): {
                    "title": "Public forums",
                },
                ("17", "5"): {
                    "title": "XenForo pre-sales questions",
                },
                ("17", "18"): {
                    "title": "XenForo suggestions",
                },
                ("46",): {
                    "title": "XenForo bug reports",
                },
                ("46", "91"): {
                    "title": "Bug reports",
                },
                ("46", "105"): {
                    "title": "Importer bug reports",
                },
                ("46", "92"): {
                    "title": "Resolved bug reports",
                },
                ("46", "43"): {
                    "title": "Future-fix bug reports",
                },
                ("22",): {
                    "title": "Customer forums",
                },
                ("22", "23"): {
                    "title": "Installation, upgrade, and import support",
                },
                ("22", "24"): {
                    "title": "Troubleshooting and problems",
                },
                ("22", "25"): {
                    "title": "XenForo questions and support",
                },
                ("22", "47"): {
                    "title": "Styling and customization questions",
                },
                ("22", "48"): {
                    "title": "Server configuration and hosting",
                },
                ("22", "84"): {
                    "title": "Forum management",
                },
                ("22", "79"): {
                    "title": "Tips and guides [1.x]",
                },
                ("22", "94"): {
                    "title": "Tips and guides [2.x]",
                },
                ("22", "45"): {
                    "title": "Other XenForo discussions and feedback",
                },
                ("22", "49"): {
                    "title": "XenForo help and manual",
                },
                ("54",): {
                    "title": "Official XenForo add-ons",
                },
                ("54", "86"): {
                    "title": "Media Gallery suggestions",
                },
                ("54", "87"): {
                    "title": "Media Gallery support",
                },
                ("54", "88"): {
                    "title": "Media Gallery bug reports",
                },
                ("54", "65"): {
                    "title": "Resource Manager suggestions",
                },
                ("54", "82"): {
                    "title": "Resource Manager support",
                },
                ("54", "66"): {
                    "title": "Resource Manager bug reports",
                },
                ("54", "55"): {
                    "title": "Enhanced Search suggestions",
                },
                ("54", "56"): {
                    "title": "Enhanced Search support",
                },
                ("54", "57"): {
                    "title": "Enhanced Search bug reports",
                },
                ("60",): {
                    "title": "XenForo resources and add-ons",
                },
                ("60", "70"): {
                    "title": "Resources and add-ons",
                },
                ("60", "71"): {
                    "title": "Resource and add-on releases [1.x]",
                },
                ("60", "93"): {
                    "title": "Resource and add-on releases [2.x]",
                },
                ("60", "68"): {
                    "title": "Resource and add-on requests",
                },
                ("60", "63"): {
                    "title": "Resource and add-on discussions",
                },
                ("60", "69"): {
                    "title": "Custom service/development requests",
                },
                ("60", "42"): {
                    "title": "Third-party services & offers",
                },
                ("60", "62"): {
                    "title": "Resource and add-on archive",
                },
                ("51",): {
                    "title": "Development help",
                },
                ("51", "106"): {
                    "title": "Resource standards",
                },
                ("51", "80"): {
                    "title": "Development tutorials and resources [1.x]",
                },
                ("51", "101"): {
                    "title": "Development tutorials [2.x]",
                },
                ("51", "34"): {
                    "title": "XenForo development discussions",
                },
                ("51", "52"): {
                    "title": "General PHP and MySQL discussions",
                },
                ("4",): {
                    "title": "General discussions",
                },
                ("4", "53"): {
                    "title": "Forum showcase and critiques",
                },
                ("4", "7"): {
                    "title": "Off topic",
                },
                ("14",): {
                    "title": "Tests and examples",
                },
                ("14", "109"): {
                    "title": "Resolved bugs",
                },
                ("14", "110"): {
                    "title": "Implemented suggestions",
                },
                ("14", "11"): {
                    "title": "Example page",
                },
            },
        },
    ]

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
