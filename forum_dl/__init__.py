import sys

from .forumdl import ForumDl
from . import options


def main():
    parser = options.build_parser()
    args = parser.parse_args()

    # with ForumDL() as forumdl:
    forumdl = ForumDl()
    # for cls in forumdl.list_classes():
    # print(cls)

    if args.list_extractors:
        print("\n".join(forumdl.list_extractors()))
    elif not args.urls:
        parser.error(
            "The following arguments are required: URL\n"
            "Use 'forum-dl --help' to get a list of all options."
        )
    else:
        forumdl.download(args.urls, args.output, args.output_format)
