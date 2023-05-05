# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse, urlunparse
from dataclasses import dataclass

from .common import get_relative_url, normalize_url
from .common import Extractor, ExtractorOptions, Board, Thread, Post, PageState
from ..session import Session
from ..soup import Soup


@dataclass
class DiscourseBoard(Board):
    slug: str = ""


@dataclass
class DiscourseThread(Thread):
    slug: str = ""


@dataclass
class DiscourseThreadPageState(PageState):
    stream_data: list[int]


class DiscourseExtractor(Extractor):
    tests = [
        {
            "url": "https://meta.discourse.org/",
            "test_base_url": "https://meta.discourse.org/",
            "test_boards": {
                ("67",): {
                    "title": "announcements",
                },
            },
        },
        {
            "url": "https://meta.discourse.org/c/announcements",
            "test_base_url": "https://meta.discourse.org/",
            "test_boards": {
                ("67", "13"): {
                    "title": "blog",
                },
            },
            "test_min_item_count": 400,
            "test_items": {
                0: {
                    "title": "About the announcements category",
                    "path": ["67", "68629"],
                }
            },
        },
        {
            "url": "https://meta.discourse.org/t/welcome-to-meta-discourse-org/1",
            "test_base_url": "https://meta.discourse.org/",
            "test_contents_hash": "36eab8dfa910b45bf8757d5d977743b90405f53f",
            "test_item_count": 1,
        },
        {
            "url": "https://meta.discourse.org/t/try-out-the-new-sidebar-and-notification-menus/238821",
            "test_base_url": "https://meta.discourse.org/",
            "test_min_item_count": 200,
        },
    ]

    @staticmethod
    def _detect(session: Session, url: str, options: ExtractorOptions):
        url = url.removesuffix("/")
        url = url.removesuffix(".json")

        response = session.get(normalize_url(url))
        soup = Soup(response.content)

        data_discourse_setup = soup.find("meta", attrs={"id": "data-discourse-setup"})
        base_url = data_discourse_setup.get("data-base-url")
        return DiscourseExtractor(session, normalize_url(base_url), options)

    def __init__(self, session: Session, base_url: str, options: ExtractorOptions):
        super().__init__(session, base_url, options)
        self.root = DiscourseBoard(
            path=(), url=self._resolve_url(base_url), origin=base_url, data={}
        )

    def _fetch_top_boards(self):
        self._are_subboards_fetched[self.root.path] = True
        response = self._session.get(urljoin(self.base_url, "site.json"))
        site_json = response.json()

        for category_data in site_json["categories"]:
            if "parent_category_id" not in category_data:
                slug = category_data["slug"]
                id = str(category_data["id"])

                self._set_board(
                    path=(id,),
                    url=urljoin(self.base_url, f"c/{slug}/{id}"),
                    origin=response.url,
                    data={},
                    slug=slug,
                    are_subboards_fetched=True,
                )

        for category_data in site_json["categories"]:
            if "parent_category_id" in category_data:
                slug = category_data["slug"]
                id = str(category_data["id"])
                parent_id = str(category_data["parent_category_id"])

                self._set_board(
                    path=(parent_id, id),
                    url=urljoin(self.base_url, f"c/{slug}/{id}"),
                    origin=response.url,
                    data={},
                    slug=slug,
                    are_subboards_fetched=True,
                )

    def _fetch_subboards(self, board: Board):
        pass

    def _get_node_from_url(self, url: str):
        url = url.removesuffix(".json")

        relative_url = get_relative_url(url, self.base_url)
        url_parts = PurePosixPath(relative_url).parts

        if len(url_parts) <= 1:
            return self.root

        if url_parts[0] == "c":
            slug = url_parts[1]

            for _, board in self._subboards[self.root.path].items():
                if cast(DiscourseBoard, board).slug == slug:
                    return board

                for _, subboard in self._subboards[board.path].items():
                    if cast(DiscourseBoard, subboard).slug == slug:
                        return subboard
        elif url_parts[0] == "t":
            id = url_parts[1]
            json_url = urljoin(self.base_url, f"t/{id}.json")
            response = self._session.get(json_url)
            data = response.json()

            slug = data["slug"]
            category_id = str(data["category_id"])

            if category_id in self._subboards[self.root.path]:
                path = (category_id, f"t{id}")
            else:
                for _, subboard in self._subboards[self.root.path].items():
                    if category_id in self._subboards[self.root.path]:
                        path = subboard.path + (category_id, f"t{id}")
                        break
                else:
                    raise ValueError

            return DiscourseThread(
                path=path,
                url=url,
                origin=response.url,
                data=data,
                title=data.get("title", None),
                slug=slug,
            )

        raise ValueError

    def _fetch_lazy_subboard(self, board: Board, id: str):
        pass

    def _fetch_lazy_subboards(self, board: Board):
        yield from ()

    def _fetch_board_page_threads(self, board: Board, state: PageState):
        if state.url == board.url:
            relative_url = get_relative_url(state.url, self.base_url)
            url_parts = PurePosixPath(relative_url).parts

            if len(url_parts) <= 1 or url_parts[0] != "c":
                return None

            state.url = f"{state.url}.json"

        response = self._session.get(state.url)
        page_json = response.json()

        for data in page_json["topic_list"]["topics"]:
            id = str(data["id"])
            slug = data["slug"]
            yield DiscourseThread(
                path=board.path + (id,),
                url=urljoin(self.base_url, f"t/{slug}/{id}"),
                origin=response.url,
                data=data,
                title=data.get("topic", None),
                slug=slug,
            )

        if more_topics_url := page_json["topic_list"].get("more_topics_url", None):
            parsed_more_topics_url = urlparse(str(more_topics_url))
            parsed_more_topics_url = parsed_more_topics_url._replace(
                path=f"{parsed_more_topics_url.path}.json"
            )

            return PageState(
                url=urljoin(self.base_url, str(urlunparse(parsed_more_topics_url)))
            )

    def _fetch_thread_page_posts(self, thread: Thread, state: PageState):
        if state.url == thread.url:
            json_url = f"{state.url}.json"
            response = self._session.get(json_url)
            page_json = response.json()
            state = DiscourseThreadPageState(
                url=response.url, stream_data=page_json["post_stream"]["stream"]
            )
        else:
            origin = state.url
            state = cast(DiscourseThreadPageState, state)
            post_ids = tuple(state.stream_data[:20])
            response = self._session.uncached_get(
                origin, params={"post_ids[]": post_ids}
            )
            page_json = response.json()

        datas = page_json["post_stream"]["posts"]

        for data in datas:
            topic_slug = data["topic_slug"]

            state.stream_data.pop(0)
            yield Post(
                path=thread.path + (str(data["id"]),),
                url=urljoin(self.base_url, f"t/{topic_slug}/{id}"),
                origin=response.url,
                data=data,
                author=data.get("username", None),
                body=data.get("cooked", None),
            )

        topic_id = str(page_json["id"])

        if state.stream_data:
            state.url = urljoin(self.base_url, f"t/{topic_id}/posts.json")
            return state
