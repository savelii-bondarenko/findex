import argparse
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path

from findex.index import Index
from findex.store import load
from findex.tokenize import tokenize


def merge_and(left: list[int], right: list[int]) -> list[int]:
    result = []
    i = j = 0

    while i < len(left) and j < len(right):
        if left[i] == right[j]:
            result.append(left[i])
            i += 1
            j += 1
        elif left[i] < right[j]:
            i += 1
        else:
            j += 1

    return result


def merge_or(left: list[int], right: list[int]) -> list[int]:
    result = []
    i = j = 0

    while i < len(left) and j < len(right):
        if left[i] == right[j]:
            result.append(left[i])
            i += 1
            j += 1
        elif left[i] < right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    result.extend(left[i:])
    result.extend(right[j:])
    return result


def merge_not(left: list[int], right: list[int]) -> list[int]:
    """Return IDs present in left but absent from right."""
    result = []
    i = j = 0

    while i < len(left) and j < len(right):
        if left[i] == right[j]:
            i += 1
            j += 1
        elif left[i] < right[j]:
            result.append(left[i])
            i += 1
        else:
            j += 1

    result.extend(left[i:])
    return result


def set_and(left: list[int], right: list[int]) -> list[int]:
    return sorted(set(left) & set(right))


def set_or(left: list[int], right: list[int]) -> list[int]:
    return sorted(set(left) | set(right))


def set_not(left: list[int], right: list[int]) -> list[int]:
    return sorted(set(left) - set(right))


Operation = Callable[[list[int], list[int]], list[int]]

ENGINES: dict[str, dict[str, Operation]] = {
    "merge": {
        "AND": merge_and,
        "OR": merge_or,
        "NOT": merge_not,
    },
    "set": {
        "AND": set_and,
        "OR": set_or,
        "NOT": set_not,
    },
}


def parse_query(query: str) -> list[str]:
    parts = []

    for part in query.split():
        if "(" in part or ")" in part:
            raise ValueError("Parentheses are not supported")

        if part in {"AND", "OR", "NOT"}:
            parts.append(part)
        else:
            parts.extend(tokenize(part))

    return parts


def search(
    index: Index,
    query: str,
    engine: str = "merge",
) -> list[int]:
    if engine not in ENGINES:
        raise ValueError(f"Unknown engine: {engine}")

    parts = parse_query(query)

    if not parts:
        return []

    operations = ENGINES[engine]
    position = 0
    universe = None

    def read_operand() -> list[int]:
        nonlocal position, universe

        negate = False

        while position < len(parts) and parts[position] == "NOT":
            negate = not negate
            position += 1

        if position >= len(parts) or parts[position] in {"AND", "OR"}:
            raise ValueError("Expected a term after an operator")

        term = parts[position]
        position += 1

        doc_ids = [posting.doc_id for posting in index.postings.get(term, [])]

        if negate:
            if universe is None:
                universe = sorted(index.doc_meta)

            return operations["NOT"](universe, doc_ids)

        return doc_ids

    result = read_operand()

    while position < len(parts):
        operator = "AND"

        if parts[position] in {"AND", "OR"}:
            operator = parts[position]
            position += 1

        right = read_operand()
        result = operations[operator](result, right)

    return result


def benchmark(index: Index, repeats: int) -> None:
    if len(index.postings) < 2:
        raise ValueError("Benchmark requires at least two distinct terms")

    terms = sorted(
        index.postings,
        key=lambda term: (len(index.postings[term]), term),
    )

    pairs = {
        "common": terms[-2:],
        "rare": terms[:2],
    }

    print("\nBoolean operations benchmark")
    print("Includes ID extraction, set creation and sorted results.")
    print("| Terms | Query | Engine | Average, us |")
    print("|---|---|---|---:|")

    for label, pair in pairs.items():
        for operator in ("AND", "OR", "NOT"):
            query = f"{pair[0]} {operator} {pair[1]}"

            expected = search(index, query, "merge")
            actual = search(index, query, "set")

            if expected != actual:
                raise RuntimeError(f"Engine results differ: {query}")

            for engine in ENGINES:
                start = time.perf_counter()

                for _ in range(repeats):
                    search(index, query, engine)

                average_us = (time.perf_counter() - start) / repeats * 1_000_000

                print(f"| {label} | {query} | {engine} | {average_us:.2f} |")


def main() -> None:
    parser = argparse.ArgumentParser(description="Boolean search")
    parser.add_argument("index_path", type=Path)
    parser.add_argument("query", nargs="?")
    parser.add_argument(
        "--engine",
        choices=ENGINES,
        default="merge",
    )
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--repeat", type=int, default=1000)
    args = parser.parse_args()

    if args.query is None and not args.benchmark:
        parser.error("Provide a query or --benchmark")

    if args.repeat < 1:
        parser.error("--repeat must be positive")

    tracemalloc.start()
    start = time.perf_counter()

    index = load(args.index_path)
    load_time = time.perf_counter() - start

    try:
        query_start = time.perf_counter()
        results = (
            search(index, args.query, args.engine) if args.query is not None else []
        )
        query_time = time.perf_counter() - query_start
    except ValueError as error:
        tracemalloc.stop()
        parser.error(str(error))

    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    if args.query is not None:
        print(f"Matches: {len(results)}")

        for doc_id in results:
            meta = index.doc_meta[doc_id]
            print(f"{doc_id}: {meta.title} ({meta.path})")

        print(f"Query time: {query_time:.6f} s")

    print(f"Load time: {load_time:.6f} s")
    print(f"Elapsed time: {elapsed:.6f} s")
    print(f"Peak memory: {peak / 1024**2:.2f} MiB")

    if args.benchmark:
        try:
            benchmark(index, args.repeat)
        except ValueError as error:
            parser.error(str(error))


if __name__ == "__main__":
    main()
