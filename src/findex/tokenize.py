import re
import unicodedata
from collections.abc import Iterator

WORD_PATTERN = re.compile(r"\w+")

def tokenize(text: str) -> Iterator[str]:
    normalized = unicodedata.normalize("NFC", text)

    casefolded = normalized.casefold()

    for match in WORD_PATTERN.finditer(casefolded):
        yield match.group()