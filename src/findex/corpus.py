from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple


class Document(NamedTuple):
    doc_id: int
    path: Path
    text: str

def iter_documents(root: Path) -> Iterator[Document]:
    doc_id = 0
    for file_path in root.rglob("*.txt"):
        try:
            text = file_path.read_text(encoding="utf-8")

            yield Document(doc_id=doc_id, path=file_path, text=text)

            doc_id += 1
        except UnicodeDecodeError:
            print(f"Encoding errors, skip: {file_path}")