# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from . import extractors
from . import writers
import os.path
import os


class ForumDL:
    def download(self, urls: list[str], output_format: str):
        for url in urls:
            self.download_url(url, output_format)

    def download_url(self, url: str, output_format: str):
        extractor = extractors.find(url)

        if extractor:
            extractor.fetch()
            writer = writers.find(extractor, "xxx", output_format)
            writer.write(url)

    def list_extractors(self) -> list[str]:
        return extractors.modules

    def list_classes(self) -> Iterable[Any]:
        return extractors.list_classes()
