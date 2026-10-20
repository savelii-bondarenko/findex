import json
import pickle
from pathlib import Path

from findex.index import DocMeta, Index, Posting


def save(index: Index, path: Path) -> None:
    if path.suffix.lower() == ".json":
        data = {
            "postings": {
                term: [[posting.doc_id, posting.tf] for posting in postings]
                for term, postings in index.postings.items()
            },
            "doc_lengths": {
                str(doc_id): length for doc_id, length in index.doc_lengths.items()
            },
            "doc_meta": {
                str(doc_id): {
                    "path": str(meta.path),
                    "title": meta.title,
                }
                for doc_id, meta in index.doc_meta.items()
            },
        }

        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, separators=(",", ":"))
    else:
        with path.open("wb") as file:
            pickle.dump(index, file, protocol=pickle.HIGHEST_PROTOCOL)


def load(path: Path) -> Index:
    if path.suffix.lower() == ".json":
        with path.open(encoding="utf-8") as file:
            data = json.load(file)

        return Index(
            postings={
                term: [Posting(doc_id=doc_id, tf=tf) for doc_id, tf in postings]
                for term, postings in data["postings"].items()
            },
            doc_lengths={
                int(doc_id): length for doc_id, length in data["doc_lengths"].items()
            },
            doc_meta={
                int(doc_id): DocMeta(
                    path=Path(meta["path"]),
                    title=meta["title"],
                )
                for doc_id, meta in data["doc_meta"].items()
            },
        )

    with path.open("rb") as file:
        index = pickle.load(file)

    if not isinstance(index, Index):
        raise TypeError("The file does not contain a findex Index")

    return index
