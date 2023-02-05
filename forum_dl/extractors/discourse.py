# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse, urlunparse
from dataclasses import dataclass
import bs4

from .common import get_relative_url, normalize_url
from .common import ForumExtractor, Board, Thread, Post
from ..cached_session import CachedSession


@dataclass
class DiscourseThread(Thread):
    slug: str = ""


@dataclass
class DiscourseBoard(Board):
    slug: str = ""


class DiscourseForumExtractor(ForumExtractor):
    tests = [
        {
            "url": "https://meta.discourse.org/",
            "test_base_url": "https://meta.discourse.org/",
            "test_boards": {
                "67": {
                    "title": "announcements",
                    "path": ["67"],
                },
            },
        },
        {
            "url": "https://meta.discourse.org/c/announcements",
            "test_base_url": "https://meta.discourse.org/",
            "test_boards": {
                "13": {
                    "title": "blog",
                    "path": ["67", "13"],
                },
            },
        },
    ]

    @staticmethod
    def detect(session: CachedSession, url: str):
        url = url.removesuffix("/")
        url = url.removesuffix(".json")

        response = session.get(normalize_url(url))
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        data_discourse_setup = soup.find("meta", attrs={"id": "data-discourse-setup"})
        if not data_discourse_setup:
            return None

        base_url: str = data_discourse_setup.get("data-base-url")
        return DiscourseForumExtractor(session, normalize_url(base_url))

    def fetch(self):
        site_json = self._session.get(urljoin(self._base_url, "site.json")).json()

        for category_data in site_json["categories"]:
            if "parent_category_id" not in category_data:
                slug = category_data["slug"]
                id = str(category_data["id"])

                self.root.lazy_subboards[id] = DiscourseBoard(
                    path=[id],
                    url=urljoin(self._base_url, f"c/{slug}/{id}"),
                    title=category_data["name"],
                    slug=slug,
                )

        for category_data in site_json["categories"]:
            if "parent_category_id" in category_data:
                slug = category_data["slug"]
                id = str(category_data["id"])
                parent_id = str(category_data["parent_category_id"])

                self.root.lazy_subboards[parent_id].lazy_subboards[id] = DiscourseBoard(
                    path=[parent_id, id],
                    url=urljoin(self._base_url, f"c/{slug}/{id}"),
                    title=category_data["name"],
                    slug=slug,
                )

    def _get_node_from_url(self, url: str):
        url = url.removesuffix(".json")

        relative_url = get_relative_url(url, self._base_url)
        url_parts = PurePosixPath(relative_url).parts

        if len(url_parts) <= 1:
            return self.root

        if url_parts[0] == "c":
            slug = url_parts[1]

            for _, board in self.root.lazy_subboards.items():
                if cast(DiscourseBoard, board).slug == slug:
                    return board

                for _, subboard in board.lazy_subboards.items():
                    if cast(DiscourseBoard, subboard).slug == slug:
                        return subboard
        elif url_parts[0] == "t":
            id = url_parts[1]
            topic_json = self._session.get(
                urljoin(self._base_url, f"t/{id}.json")
            ).json()

            slug = topic_json["slug"]
            category_id = str(topic_json["category_id"])

            if category_id in self.root.lazy_subboards:
                path = [category_id, f"t{id}"]
            else:
                for _, subboard in self.root.lazy_subboards.items():
                    if category_id in subboard.lazy_subboards:
                        path = subboard.path + [category_id, f"t{id}"]
                        break

            return DiscourseThread(
                path=path,
                url=url,
                title=topic_json["title"],
                slug=slug,
            )

        raise ValueError

    def _fetch_subboard(self, board: Board, id: str):
        pass

    def _get_board_page_items(self, board: Board, page_url: str):
        if page_url == board.url:
            relative_url = get_relative_url(page_url, self._base_url)
            url_parts = PurePosixPath(relative_url).parts

            if len(url_parts) <= 1 or url_parts[0] != "c":
                return None

            page_url = f"{page_url}.json"

        page_json = self._session.get(page_url).json()

        for topic_data in page_json["topic_list"]["topics"]:
            id = str(topic_data["id"])
            slug = topic_data["slug"]
            yield DiscourseThread(
                path=board.path + [id],
                url=urljoin(self._base_url, f"t/{slug}/{id}"),
                title=topic_data["title"],
                slug=slug,
            )

        if more_topics_url := page_json["topic_list"].get("more_topics_url", None):
            parsed_more_topics_url = urlparse(more_topics_url)
            parsed_more_topics_url = parsed_more_topics_url._replace(
                path=parsed_more_topics_url.path + ".json"
            )

            return (urljoin(self._base_url, urlunparse(parsed_more_topics_url)),)

    def _get_thread_page_items(self, thread: Thread, page_url: str, stream_data=None):
        if page_url == thread.url:
            page_url = f"{page_url}.json"
            page_json = self._session.get(page_url).json()
            stream_data = page_json["post_stream"]["stream"]
        else:
            post_ids = tuple(stream_data[:20])
            page_json = self._session.get(
                page_url, params={"post_ids[]": post_ids}
            ).json()

        posts_data = page_json["post_stream"]["posts"]

        for post_data in posts_data:
            topic_slug = post_data["topic_slug"]

            stream_data.pop(0)
            yield Post(
                path=thread.path + [str(post_data["id"])],
                url=urljoin(self._base_url, f"t/{topic_slug}/{id}"),
                title="",
                content=post_data["cooked"],
                username=post_data["username"],
            )

        topic_id = str(page_json["id"])

        if stream_data:
            return (urljoin(self._base_url, f"t/{topic_id}/posts.json"), stream_data)
