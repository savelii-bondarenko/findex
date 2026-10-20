from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from findex.corpus import Document
from findex.tokenize import tokenize


@dataclass(frozen=True, slots=True)
class Posting:
    doc_id: int
    tf: int


@dataclass(frozen=True, slots=True)
class DocMeta:
    path: Path
    title: str


@dataclass(slots=True)
class Index:
    postings: dict[str, list[Posting]]
    doc_lengths: dict[int, int]
    doc_meta: dict[int, DocMeta]


def build_index(documents: Iterable[Document]) -> Index:
    postings: defaultdict[str, list[Posting]] = defaultdict(list)
    doc_lengths: dict[int, int] = {}
    doc_meta: dict[int, DocMeta] = {}

    for document in documents:
        if document.doc_id in doc_meta:
            raise ValueError(f"Duplicate document ID: {document.doc_id}")

        term_counts = Counter(tokenize(document.text))

        doc_lengths[document.doc_id] = sum(term_counts.values())
        doc_meta[document.doc_id] = DocMeta(
            path=document.path,
            title=document.path.stem,
        )

        for term, frequency in term_counts.items():
            postings[term].append(Posting(doc_id=document.doc_id, tf=frequency))

    for term_postings in postings.values():
        term_postings.sort(key=lambda posting: posting.doc_id)

    return Index(
        postings=dict(postings),
        doc_lengths=doc_lengths,
        doc_meta=doc_meta,
    )


def main() -> None:
    import argparse
    import time
    import tracemalloc
    from itertools import islice

    from findex.corpus import iter_documents
    from findex.index import build_index as build
    from findex.store import save

    parser = argparse.ArgumentParser(description="Build an inverted index")
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    if not args.data_dir.is_dir():
        parser.error(f"Directory does not exist: {args.data_dir}")

    if args.limit is not None and args.limit < 0:
        parser.error("--limit must be non-negative")

    tracemalloc.start()
    start = time.perf_counter()

    documents = iter_documents(args.data_dir)

    if args.limit is not None:
        documents = islice(documents, args.limit)

    index = build(documents)
    build_time = time.perf_counter() - start

    save_start = time.perf_counter()
    save(index, args.out)
    save_time = time.perf_counter() - save_start

    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Documents: {len(index.doc_meta)}")
    print(f"Vocabulary: {len(index.postings)}")
    print(f"Build time: {build_time:.6f} s")
    print(f"Save time: {save_time:.6f} s")
    print(f"File size: {args.out.stat().st_size} bytes")
    print(f"Elapsed time: {elapsed:.6f} s")
    print(f"Peak memory: {peak / 1024**2:.2f} MiB")


if __name__ == "__main__":
    main()
