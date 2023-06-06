# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

import json

from .common import FileWriter, Entry


class JsonlWriter(FileWriter):
    def _serialize_entry(self, entry: Entry):
        return json.dumps(entry.dict())
