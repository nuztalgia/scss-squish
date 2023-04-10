import logging
import re
from string import Template
from typing import Final

import pyperclip
import requests
from csscompressor import compress
from humanize import naturalsize

URL_TEMPLATE: Final[Template] = Template(
    "https://raw.githubusercontent.com/CutieCity/mastodon/main/"
    "app/javascript/flavours/${flavour}/styles/${filename}.scss"
)
FLAVOUR_GLITCH: Final[str] = "glitch"
FLAVOUR_CUTIE_CITY: Final[str] = "cutiecity"

GLITCH_TOP_LEVEL_FILES: Final[tuple[str, ...]] = (
    "reset",
    "basics",
    "branding",
    "containers",
    "forms",
    "accounts",
    "statuses",
)
GLITCH_COMPONENT_FILES: Final[tuple[str, ...]] = (
    "misc",
    "accounts",
    "status",
    "compose_form",
    "columns",
    "search",
    "emoji",
    "drawer",
    "media",
    "single_column",
    "about",
)

SCSS_FILES: Final[tuple[tuple[str, str], ...]] = (
    (FLAVOUR_GLITCH, "_mixins"),
    (FLAVOUR_CUTIE_CITY, "variables"),
    *[(FLAVOUR_GLITCH, f) for f in GLITCH_TOP_LEVEL_FILES],
    *[(FLAVOUR_GLITCH, f"components/{f}") for f in GLITCH_COMPONENT_FILES],
    *[(FLAVOUR_GLITCH, f) for f in ("polls", "about", "tables", "accessibility")],
    *[(FLAVOUR_CUTIE_CITY, f) for f in ("boost", "components", "extra")],
)

SVG_REGEX: Final[re.Pattern] = re.compile(r"['\"]data:image/svg.*?<svg.*?</svg>['\"]")


def get_file_contents(flavour: str, filename: str) -> str:
    request_url = URL_TEMPLATE.substitute(flavour=flavour, filename=filename)
    logging.info(f"Fetching from url: {request_url}")

    response = requests.get(request_url)
    response.raise_for_status()

    logging.debug(response.text)
    return response.text


def get_size_label(content: str) -> str:
    num_bytes = len(content.encode("utf-8"))
    return naturalsize(num_bytes, binary=True, format="%.2f")


def get_squished_scss(raw_scss: str) -> str:
    squished_scss = compress(
        re.sub(r"(\s+//.*|@use [^;]+;)", "", raw_scss),
        preserve_exclamation_comments=False,
    )

    for svg, raw in zip(SVG_REGEX.findall(squished_scss), SVG_REGEX.findall(raw_scss)):
        squished_scss = squished_scss.replace(svg, raw)  # Undo bad SVG compression.

    return squished_scss


def main() -> int:
    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
    logging.info("Starting the `scss-squish` demo script.")

    raw_scss = "$font-sans-serif: 'Roboto'; $font-monospace: 'Roboto Mono';"

    try:
        for file_info in SCSS_FILES:
            raw_scss += get_file_contents(*file_info)
    except requests.exceptions.HTTPError as error:
        logging.error(error)
        return 1

    logging.info(f"Successfully fetched all files ({get_size_label(raw_scss)}).")

    try:
        squished_scss = get_squished_scss(raw_scss)
    except ValueError:
        logging.error("Value Error: Malformed CSS")
        return 1

    size_label = get_size_label(squished_scss)

    try:
        pyperclip.copy(squished_scss)
        logging.info(f"Copied squished SCSS to clipboard ({size_label}).")
        logging.debug(squished_scss)
    except pyperclip.PyperclipException as error:
        logging.warning(
            "Unable to access the clipboard. Here's your squished CSS "
            f"({size_label}):\n\n{squished_scss}\n\nNOTE:{error}\n"
        )

    logging.info("Successfully finished the `scss-squish` demo script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
