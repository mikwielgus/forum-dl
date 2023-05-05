# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse
import re

from .common import normalize_url
from .common import Extractor, ExtractorOptions, Board, Thread, Post, PageState
from ..session import Session
from ..soup import Soup


class HyperkittyExtractor(Extractor):
    tests = [
        {
            "url": "https://mail.python.org/archives/",
            "board_count": 5,
            "test_base_url": "https://mail.python.org/archives/",
            "test_boards": {
                ("numpy-discussion@python.org",): {
                    "title": "NumPy-Discussion",
                    "content": "Discussion of Numerical Python",
                },
                ("scipy-dev@python.org",): {
                    "title": "SciPy-Dev",
                    "content": "SciPy Developers List",
                },
                ("charlottepython@python.org",): {
                    "title": "CharlottePython",
                    "content": "List for the Python user group in Charlotte, North Carolina.",
                },
                ("python-dev@python.org",): {
                    "title": "Python-Dev",
                    "content": "Python core developers",
                },
                ("python-ideas@python.org",): {
                    "title": "Python-ideas",
                    "content": "Discussions of speculative Python language ideas",
                },
            },
        },
        {
            "url": "https://mail.python.org/archives/list/mm3_test@python.org",
            "test_base_url": "https://mail.python.org/archives/",
            # "test_contents_hash": "6768033e216468247bd031a0a2d9876d79818f8f",
            "test_item_count": 21,
        },
        {
            "url": "https://mail.python.org/archives/list/mm3_test@python.org/thread/NGFDAQJOJQDRPOU4WLRZEB55KAXPJWGN/",
            "test_base_url": "https://mail.python.org/archives/",
            "test_contents_hash": "b9ef8af9eba069575851015dd37dfab45900603c",
            "test_item_count": 5,
        },
        {
            "url": "https://mail.python.org/archives/list/mm3_test@python.org/thread/JNBVEQQBAI67DBT4HFXI3PO4APTKGQZO/",
            "test_base_url": "https://mail.python.org/archives/",
            "test_contents_hash": "c7493dd61e816329f3eab6b1642a2ecc6163fcb5",
            "test_item_count": 2,
        },
        {
            "url": "https://mail.python.org/archives/list/mm3_test@python.org/thread/IWRIV5ULS4BHY43TRYCHE2TXJB7KZQ7U/",
            "test_base_url": "https://mail.python.org/archives/",
            "test_contents_hash": "e17370233530f5055bb2e9f44a4d58da7fbf04ca",
            "test_item_count": 1,
        },
    ]

    @staticmethod
    def _detect(session: Session, url: str, options: ExtractorOptions):
        response = session.get(url)
        soup = Soup(response.content)

        if extractor := HyperkittyExtractor.detect_postorius(
            session, url, soup, options
        ):
            return extractor

        if extractor := HyperkittyExtractor.detect_hyperkitty(
            session, url, soup, options
        ):
            return extractor

    @staticmethod
    def detect_postorius(
        session: Session, url: str, soup: Soup, options: ExtractorOptions
    ):
        if not (footer := soup.try_find("footer")):
            return None

        if not footer.try_find("a", string="Postorius Documentation"):
            return False

        if not (nav_link_anchors := soup.find_all("a", class_="nav-link")):
            return None

        base_url = normalize_url(urljoin(url, nav_link_anchors[1].get("href")))
        return HyperkittyExtractor(session, base_url, options)

    @staticmethod
    def detect_hyperkitty(
        session: Session, url: str, soup: Soup, options: ExtractorOptions
    ):
        if not (footer := soup.try_find("footer")):
            return None

        if not footer.try_find("a", string="HyperKitty"):
            return False

        if not (navbar_brand_anchor := soup.try_find("a", class_="navbar-brand")):
            return None

        base_url = normalize_url(urljoin(url, navbar_brand_anchor.get("href")))
        return HyperkittyExtractor(session, base_url, options)

    def _fetch_top_boards(self):
        pass

    def _fetch_subboards(self, board: Board):
        pass

    def _get_node_from_url(self, url: str):
        response = self._session.get(url)
        resolved_url = normalize_url(response.url)

        if resolved_url == self.base_url:
            return self.root

        parsed_url = urlparse(resolved_url)
        path = PurePosixPath(parsed_url.path)

        if len(path.parts) >= 4 and path.parts[-2] == "thread":
            board_id = path.parts[-3]
            thread_id = path.parts[-1]

            return Thread(
                path=(board_id, thread_id),
                url=resolved_url,
                origin=resolved_url,
                data={},
                title="",  # TODO.
            )
        elif len(path.parts) >= 2 and path.parts[-2] == "list":
            return self.find_board((path.parts[-1],))

        raise ValueError

    def _fetch_lazy_subboard(self, board: Board, id: str):
        url = normalize_url(urljoin(self.base_url, f"list/{id}"))
        response = self._session.get(url)
        soup = Soup(response.content)

        title = ""

        if title_section := soup.find("section", id="title"):
            if h1 := title_section.find("h1"):
                title = h1.string.strip()
            elif h2 := title_section.find("h2"):
                title = h2.string.strip()

        description = ""

        if description_section := soup.find("p", id="description"):
            description = description_section.string

        return self._set_board(
            path=(id,),
            url=url,
            origin=response.url,
            data={"title": title, "description": description},
        )

    def _fetch_lazy_subboards(self, board: Board):
        href: str = ""
        url: str = self.base_url

        while href != "#":
            response = self._session.get(url)
            soup = Soup(response.content)
            list_anchors = soup.find_all("a", class_="list-name")

            for list_anchor in list_anchors:
                url = urljoin(self.base_url, list_anchor.get("href"))
                yield self._fetch_lazy_subboard(board, url)

            page_link_anchors = soup.find_all("a", class_="page-link")
            next_page_anchor = page_link_anchors[-1]

            href = next_page_anchor.get("href")
            url = urljoin(self.base_url, href)

    def _fetch_board_page_threads(self, board: Board, state: PageState):
        match = re.match(r"^.*latest?page=(\d+)$", state.url)

        if match:
            cur_page = int(match.group(1))
        else:
            cur_page = 1

        if board == self.root:
            return None

        if state.url == board.url:
            state.url = urljoin(state.url, "latest")

        origin = state.url

        response = self._session.get(origin)
        soup = Soup(response.content)

        thread_anchors = soup.find_all("a", class_="thread-title")

        for thread_anchor in thread_anchors:
            yield Thread(
                path=board.path + (thread_anchor.get("name"),),
                url=urljoin(state.url, thread_anchor.get("href")),
                origin=origin,
                data={},
                title="TODO",
            )

        if page_link_tags := soup.find_all(class_="page-link"):
            last_page = int(page_link_tags[-2].string)

            if cur_page < last_page:
                return PageState(url=urljoin(state.url, f"latest?page={cur_page + 1}"))

    def _fetch_thread_page_posts(self, thread: Thread, state: PageState):
        origin = state.url
        response = self._session.get(origin)

        if state.url == thread.url:
            soup = Soup(response.content)

            if email_body_div := soup.find("div", class_="email-body"):
                yield Post(
                    path=thread.path + ("x",),  # TODO: We use a dummy path for now.
                    url=urljoin(
                        origin,
                        soup.find("div", class_="messagelink").find("a").get("href"),
                    ),
                    origin=origin,
                    data={},
                    author="TODO",
                    body=str(email_body_div.contents),
                )

            return PageState(url=urljoin(state.url, "replies?sort=thread"))

        json = response.json()

        replies_html = json["replies_html"]
        soup = Soup(replies_html)

        email_body_divs = soup.find_all("div", class_="email-body")
        for email_body_div in email_body_divs:
            yield Post(
                path=thread.path + ("x",),  # TODO: We use a dummy path for now.
                url=urljoin(
                    origin, soup.find("div", class_="messagelink").find("a").get("href")
                ),
                origin=origin,
                data={},
                author="TODO",
                body=str(email_body_div.contents),
            )

        # soup = Soup(response.content)

        if json["more_pending"]:
            next_offset = json["next_offset"]
            return PageState(
                url=urljoin(state.url, f"replies?sort=thread&offset={next_offset}")
            )
