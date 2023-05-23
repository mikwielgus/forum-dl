# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from urllib.parse import urljoin
import re

from .common import normalize_url, regex_match
from .common import Extractor, ExtractorOptions, Board, Thread, Post, PageState
from ..session import Session
from ..soup import Soup


class XenforoExtractor(Extractor):
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
        {
            "url": "https://xenforo.com/community/threads/darkness-free-xenforo-2-gaming-skin-deleted.154782/",
            "test_base_url": "https://xenforo.com/community/",
            "test_contents_hash": "00cd24c8a7aba0f567d6a0868cfe27fada450ca4",
            "test_item_count": 53,
        },
        {
            "url": "https://xenforo.com/community/threads/steam-authentication-deleted.141309/",
            "test_base_url": "https://xenforo.com/community/",
            "test_contents_hash": "47091f2cb3f716ee16f5057f8350a2f514ed4bce",
            "test_item_count": 26,
        },
    ]

    _category_class_regex = re.compile(r"^block--category(\d+)$")
    _board_class_regex = re.compile(r"^node--id(\d+)$")
    _thread_class_regex = re.compile(r"^js-threadListItem-(\d+)$")
    _thread_key_regex = re.compile(r"^thread-(\d+)$")
    _post_id_regex = re.compile(r"^post-(\d+)$")

    @staticmethod
    def _detect(session: Session, url: str, options: ExtractorOptions):
        response = session.try_get(
            normalize_url(url, remove_suffixes=[], append_slash=False),
            should_cache=True,
            should_retry=False,
        )
        soup = Soup(response.content)

        data_nav_id_anchor = soup.find("a", attrs={"data-nav-id": "forums"})
        base_url = normalize_url(urljoin(url, data_nav_id_anchor.get("href")))
        if not base_url:
            return None

        if not soup.find("a", attrs={"rel": "sponsored noopener"}):
            return None

        return XenforoExtractor(session, base_url, options)

    def _fetch_top_boards(self):
        self._are_subboards_fetched[self.root.path] = True

        response = self._session.get(self.base_url, should_cache=True)
        soup = Soup(response.content)

        block_category_divs = soup.find_all("div", class_=self._category_class_regex)
        for block_category_div in block_category_divs:
            category_header = block_category_div.find("h2", class_="block-header")
            category_anchor = category_header.find("a")
            category_id = regex_match(
                self._category_class_regex, block_category_div.get_list("class")
            ).group(1)
            category_href = category_header.find("a").get("href")

            self._set_board(
                path=(category_id,),
                url=urljoin(response.url, category_href),
                origin=response.url,
                data={},
                title=category_anchor.string.strip(),
                are_subboards_fetched=True,
            )

            node_id_divs = block_category_div.find_all(
                "div", class_=self._board_class_regex
            )

            for node_id_div in node_id_divs:
                subboard_id = regex_match(
                    self._board_class_regex, node_id_div.get_list("class")
                ).group(1)

                node_description_anchor = node_id_div.find(
                    "a", attrs={"data-shortcut": "node-description"}
                )

                href = node_description_anchor.get("href")

                self._set_board(
                    path=(category_id, subboard_id),
                    url=urljoin(self.base_url, href),
                    origin=response.url,
                    data={},
                    title=node_description_anchor.string.strip(),
                )

        self._fetch_lower_boards(self.root)

    def _fetch_subboards(self, board: Board):
        pass

    def _get_node_from_url(self, url: str):
        response = self._session.get(url, should_cache=True)
        soup = Soup(response.content)

        breadcrumbs_ul = soup.find("ul", class_="p-breadcrumbs")
        breadcrumb_anchors = breadcrumbs_ul.find_all("a", attrs={"itemprop": "item"})

        if len(breadcrumb_anchors) <= 1:
            return self.root

        # Thread.
        if soup.find("article"):
            board_url = urljoin(url, breadcrumb_anchors[-2].get("href"))
            html = soup.find("html")
            thread_id = regex_match(
                self._thread_key_regex, html.get("data-content-key")
            ).group(1)
            title_h1 = soup.find("h1", class_="p-title-value")

            for cur_board in self._boards:
                if cur_board.url == board_url:
                    return Thread(
                        path=cur_board.path + (thread_id,),
                        url=urljoin(self.base_url, url),
                        origin=response.url,
                        data={},
                        title=title_h1.string,
                    )
        # Board.
        else:
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

        response = self._session.get(state.url)
        soup = Soup(response.content)

        thread_divs = soup.find_all("div", class_=self._thread_class_regex)
        for thread_div in thread_divs:
            thread_id = regex_match(
                self._thread_class_regex, thread_div.get_list("class")[-1]
            ).group(1)

            title_div = thread_div.find("div", class_="structItem-title")
            title_anchor = title_div.find("a")

            url = urljoin(self.base_url, title_anchor.get("href"))

            yield Thread(
                path=board.path + (thread_id,),
                url=url,
                origin=response.url,
                data={},
                title=title_anchor.string,
            )

        next_page_anchor = soup.try_find("a", class_="pageNav-jump--next")
        if next_page_anchor:
            return PageState(
                url=urljoin(self.base_url, next_page_anchor.get("href")),
            )

    def _fetch_thread_page_posts(self, thread: Thread, state: PageState):
        response = self._session.get(state.url)
        soup = Soup(response.content)

        message_articles = soup.find_all("article", class_="message")

        for message_article in message_articles:
            bbwrapper_div = message_article.find("div", class_="bbWrapper")
            message_attribution_ul = message_article.find(
                "ul", class_="message-attribution-main"
            )
            url_anchor = message_attribution_ul.find("a")
            time_tag = message_attribution_ul.find("time")

            yield Post(
                path=thread.path,
                subpath=(
                    regex_match(
                        self._post_id_regex, message_article.get("data-content")
                    ).group(1),
                ),
                url=urljoin(state.url, url_anchor.get("href")),
                origin=response.url,
                data={},
                author=message_article.get("data-author"),
                creation_time=time_tag.get("datetime"),
                content=str(bbwrapper_div.encode_contents()),
            )

        next_page_anchor = soup.try_find("a", class_="pageNav-jump--next")
        if next_page_anchor:
            return PageState(
                url=urljoin(self.base_url, next_page_anchor.get("href")),
            )
