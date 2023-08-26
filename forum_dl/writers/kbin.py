# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from datetime import datetime

import psycopg2
from .common import Writer, WriterOptions
from ..extractors.common import Extractor, Thread, NullThread, Board, Post, File


class KbinWriter(Writer):
    def __init__(self, extractor: Extractor, options: WriterOptions):
        super().__init__(extractor, options)

        self._connection = psycopg2.connect(
            dbname=options.db_name,
            user=options.db_user,
            password=options.db_password,
            host=options.db_host,
            port=options.db_port,
        )
        self._connection.autocommit = True
        self._cursor = self._connection.cursor()
        self._id_to_entry_id: dict[str, str] = {}

        self._cursor.execute(
            'SELECT id FROM public."user" WHERE username = %s',
            (self._options.kbin_user,),
        )

        fetched = self._cursor.fetchone()
        assert fetched
        self._user_id: str = fetched[0]

        self._cursor.execute(
            "SELECT id FROM public.magazine WHERE name = %s",
            (self._options.kbin_magazine,),
        )

        fetched = self._cursor.fetchone()
        assert fetched
        self._magazine_id: str = fetched[0]

    def __del__(self):
        self._cursor.close()  # type: ignore
        self._connection.close()

    def read_metadata(self):
        pass

    def _write_board_object(self, board: Board):
        pass

    def _write_thread_object(self, thread: Thread):
        self._subpath_to_comment_id: dict[tuple[str, ...], str | None] = {(): None}

    def _write_post_object(self, thread: Thread, post: Post):
        if len(post.subpath) == 1:
            content = f"`Originally by u/{post.author} on r/{post.data['subreddit']}`\n{post.content}"

            # Notes: we save Reddit's score into both "ranking" and "score".
            self._cursor.execute(
                "INSERT INTO public.entry ("
                "id, "
                "user_id, "
                "magazine_id, "
                "image_id, "
                "domain_id, "
                "slug, "
                "title, "
                "url, "
                "body, "
                "type, "
                "has_embed, "
                "comment_count, "
                "score, "
                "views, "
                "is_adult, "
                "sticky, "
                "last_active, "
                "ip, "
                "up_votes, "
                "down_votes, "
                "ranking, "
                "visibility, "
                "created_at, "
                "ada_amount, "
                "lang, "
                "is_oc, "
                "favourite_count, "
                "edited_at, "
                "mentions, "
                "ap_id, "
                "tags"
                ") VALUES ("
                "pg_catalog.nextval('public.entry_id_seq'), "  # id
                "%s, "  # user_id
                "%s, "  # magazine_id
                "NULL, "  # image_id
                # "pg_catalog.nextval('public.image_id_seq'), "  # image_id
                "NULL, "  # domain_id
                "NULL, "  # slug
                "%s, "  # title
                "%s, "  # url
                "%s, "  # body
                "'link', "  # type
                "FALSE, "  # has_embed
                "%s, "  # comment_count
                # "0, "  # comment_count
                # "%s, "  # score
                "%s, "  # score
                "0, "  # views
                "FALSE, "  # is_adult
                "FALSE, "  # sticky
                "%s, "  # last_active
                "'192.168.0.1', "  # ip
                # "%s, "  # up_votes
                "0, "  # up_votes
                "0, "  # down_votes
                "%s, "  # ranking
                "'visible', "  # visibility
                "%s, "  # created_at
                "0, "  # ada_amount
                "'en', "  # lang
                "FALSE, "  # is_oc
                # "0, "  # favourite_count
                "%s, "  # favourite_count
                "NULL, "  # edited_at
                "NULL, "  # mentions
                "NULL, "  # ap_id
                "NULL"  # tags
                ") RETURNING id",
                (
                    self._user_id,
                    self._magazine_id,
                    thread.title[:255],
                    (post.data["url"] or "")[:2048],
                    content,
                    post.data["num_comments"],
                    post.data["score"],
                    # post.data["score"],
                    # datetime.now(),
                    post.creation_time,
                    # post.data["score"],
                    post.data["score"],
                    post.creation_time,
                    post.data["score"],
                ),
            )
            fetched = self._cursor.fetchone()
            assert fetched
            self._id_to_entry_id[post.subpath[0]] = fetched[0]
        else:
            if len(post.subpath) >= 3:
                parent_id = self._subpath_to_comment_id[post.subpath[:-1]]
                root_id = self._subpath_to_comment_id[post.subpath[:2]]
            else:
                parent_id = None
                root_id = None

            entry_id = self._id_to_entry_id[post.subpath[0]]
            content = f"`Originally by u/{post.author} on r/{post.data['subreddit']}`\n{post.content}"

            self._cursor.execute(
                "INSERT INTO public.entry_comment ("
                "id, "
                "user_id, "
                "entry_id, "
                "magazine_id, "
                "image_id, "
                "parent_id, "
                "root_id, "
                "body, "
                "last_active, "
                "ip, "
                "up_votes, "
                "down_votes, "
                "visibility, "
                "created_at, "
                "favourite_count, "
                "edited_at, "
                "mentions, "
                "ap_id, "
                "tags, "
                "lang, "
                "is_adult"
                ") VALUES ("
                "pg_catalog.nextval('public.entry_comment_id_seq'), "  # id
                "%s, "  # user_id
                "%s, "  # entry_id
                "%s, "  # magazine_id
                "NULL, "  # image_id
                "%s, "  # parent_id
                "%s, "  # root_id
                "%s, "  # body
                "%s, "  # last_active
                "'192.168.0.1', "  # ip
                "0, "  # up_votes
                "0, "  # down_votes
                "'visible', "  # visibility
                "%s, "  # created_at
                "0, "  # favourite_count
                "NULL, "  # edited_at
                "'{}', "  # mentions
                "NULL, "  # ap_id
                "NULL, "  # tags
                "'en', "  # lang
                "FALSE"  # is_adult
                ") RETURNING id",
                (
                    self._user_id,
                    entry_id,
                    self._magazine_id,
                    # None,
                    # None,
                    # self._subpath_to_comment_id[post.subpath[:-1]],
                    # self._subpath_to_comment_id[post.subpath[:1]],
                    parent_id,
                    root_id,
                    content,
                    post.creation_time,
                    post.creation_time,
                    # datetime.now(),
                    # datetime.now(),
                ),
            )
            fetched = self._cursor.fetchone()
            assert fetched
            self._subpath_to_comment_id[post.subpath] = fetched[0]

            self._cursor.execute(
                "UPDATE public.entry SET last_active = %s WHERE id = %s",
                (
                    post.creation_time,
                    entry_id,
                ),
            )

    def _write_file_object(self, file: File):
        pass
