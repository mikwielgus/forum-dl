NOTE: This software is in early alpha stage. Expect a lot of bugs and missing features.

# forum-dl

Forum-dl is a downloader (scraper) for forums, mailing lists, and news aggregators. It can be used to crawl, extract, and archive individual threads and entire boards into a variety of output formats.

![Peek 2023-04-23 01-59](https://user-images.githubusercontent.com/58011230/233812474-31fc4999-5cb6-4deb-b450-68d66dd56e10.gif)

Downloading from the following software is supported:

- Discourse
- Hacker News
- Hyperkitty
- Hypermail
- Invision Power Board
- PhpBB
- Pipermail
- Proboards
- Simple Machines Forum
- vBulletin
- Xenforo

The following output formats are supported:

- Babyl
- JSONL
- Maildir
- Mbox
- MH
- MMDF

# Installation

Execute `pip install -e .` in the project directory.

# Usage

```
forum-dl [--help] [--version] [--list-extractors] [--user-agent USER_AGENT] [-q] [-v] [-g] [-o FILE] [-f FORMAT] [--no-boards]
         [--no-threads] [--no-posts] [--textify] [--content-as-title]
```

## General Options:

```
  --help                Show this help message and exit
  --version             Print program version and exit
  --list-extractors     List all supported extractors and exit
  --user-agent USER_AGENT
                        User-Agent request header
```

## Output Options:

```
  -q, --quiet           Activate quiet mode
  -v, --verbose         Print various debugging information
  -g, --get-urls        Print URLs instead of downloading
  -o FILE, --output FILE
                        Output all results concatenated to FILE, or stdout if FILE is -
  -f FORMAT, --output-format FORMAT
                        Output format
  --no-boards           Do not write board objects
  --no-threads          Do not write thread objects
  --no-posts            Do not write post objects
  --textify             Lossily convert HTML content to plaintext
  --content-as-title    Write 98 initial characters of content in title field of each post
```
