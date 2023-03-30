# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from . import version

import argparse


def build_parser():
    parser = argparse.ArgumentParser(
        add_help=True,
    )

    general = parser.add_argument_group("General Options")
    general.add_argument(
        "--version",
        action="version",
        version=version.__version__,
        help="Print program version and quit",
    )
    parser.add_argument(
        "urls",
        metavar="URL",
        nargs="*",
        help=argparse.SUPPRESS,
    )

    return parser
