import sys

from .forumdl import ForumDL
from . import options


def main():
    parser = options.build_parser()
    args = parser.parse_args()

    if not args.urls:
        parser.error(
            "The following arguments are required: URL\n"
            "Use 'forum-dl --help' to get a list of all options."
        )

    # with ForumDL() as forumdl:
    forumdl = ForumDL()
    # for cls in forumdl.list_classes():
    # print(cls)

    forumdl.download(args.urls, args.output_format)
