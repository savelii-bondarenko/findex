import argparse
import gc
import pickle
import time
import tracemalloc
from array import array
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import islice
from pathlib import Path

from findex.corpus import iter_documents
from findex.index import DocMeta, Posting
from findex.tokenize import tokenize


@dataclass(frozen=True)
class PlainPosting:
    doc_id: int
    tf: int


def build_variant(root: Path, variant: str, limit: int | None) -> dict:
    if variant == "array":
        postings = defaultdict(lambda: (array("I"), array("I")))
    else:
        postings = defaultdict(list)

    doc_lengths = {}
    doc_meta = {}

    documents = iter_documents(root)

    if limit is not None:
        documents = islice(documents, limit)

    previous_id = -1

    for document in documents:
        if document.doc_id <= previous_id:
            raise ValueError("Document IDs must be strictly increasing")

        previous_id = document.doc_id
        term_counts = Counter(tokenize(document.text))

        doc_lengths[document.doc_id] = sum(term_counts.values())
        doc_meta[document.doc_id] = DocMeta(
            path=document.path,
            title=document.path.stem,
        )

        for term, frequency in term_counts.items():
            if variant == "plain":
                postings[term].append(PlainPosting(document.doc_id, frequency))
            elif variant == "slots":
                postings[term].append(Posting(document.doc_id, frequency))
            else:
                doc_ids, frequencies = postings[term]
                doc_ids.append(document.doc_id)
                frequencies.append(frequency)

    return {
        "postings": dict(postings),
        "doc_lengths": doc_lengths,
        "doc_meta": doc_meta,
    }


def measure(root: Path, variant: str, limit: int | None, output: Path) -> dict:
    gc.collect()

    tracemalloc.start()
    build_start = time.perf_counter()

    index = build_variant(root, variant, limit)

    build_time = time.perf_counter() - build_start
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    doc_count = len(index["doc_meta"])
    vocabulary = len(index["postings"])
    token_count = sum(index["doc_lengths"].values())

    with output.open("wb") as file:
        pickle.dump(index, file, protocol=pickle.HIGHEST_PROTOCOL)

    file_size = output.stat().st_size

    del index
    gc.collect()

    load_start = time.perf_counter()

    with output.open("rb") as file:
        restored = pickle.load(file)

    load_time = time.perf_counter() - load_start

    if (
        len(restored["doc_meta"]) != doc_count
        or len(restored["postings"]) != vocabulary
        or sum(restored["doc_lengths"].values()) != token_count
    ):
        raise RuntimeError(f"Invalid round trip for {variant}")

    del restored
    gc.collect()

    return {
        "variant": variant,
        "documents": doc_count,
        "vocabulary": vocabulary,
        "tokens": token_count,
        "build_time": build_time,
        "peak_mib": peak_memory / 1024**2,
        "file_size": file_size,
        "load_time": load_time,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Posting memory study")
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("benchmarks"),
    )
    args = parser.parse_args()

    if not args.data_dir.is_dir():
        parser.error(f"Directory does not exist: {args.data_dir}")

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for variant in ("plain", "slots", "array"):
        print(f"Measuring {variant}...", flush=True)

        result = measure(
            root=args.data_dir,
            variant=variant,
            limit=args.limit,
            output=args.out_dir / f"{variant}.pkl",
        )
        results.append(result)

        print(
            f"Documents: {result['documents']}, "
            f"vocabulary: {result['vocabulary']}, "
            f"build: {result['build_time']:.3f} s"
        )

    signatures = {
        (row["documents"], row["vocabulary"], row["tokens"]) for row in results
    }

    if len(signatures) != 1:
        raise RuntimeError("Corpus statistics differ between variants")

    print()
    print(
        "| Representation | Peak build memory, MiB | Index size, bytes | Load time, s |"
    )
    print("|---|---:|---:|---:|")

    labels = {
        "plain": "Plain dataclass",
        "slots": "Slotted dataclass",
        "array": "array('I') pairs",
    }

    for row in results:
        print(
            f"| {labels[row['variant']]} "
            f"| {row['peak_mib']:.2f} "
            f"| {row['file_size']} "
            f"| {row['load_time']:.6f} |"
        )


if __name__ == "__main__":
    main()
