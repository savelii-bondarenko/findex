import argparse
import itertools
import time
import tracemalloc
from collections import Counter
from pathlib import Path

from findex.corpus import iter_documents
from findex.tokenize import tokenize


def main():
    parser = argparse.ArgumentParser(description="Eager (greedy) corpus statistics")
    parser.add_argument("data_dir", type=Path, help="Path to the corpus directory")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of documents")
    args = parser.parse_args()

    tracemalloc.start()
    start_time = time.perf_counter()

    docs_generator = iter_documents(args.data_dir)
    if args.limit is not None:
        docs_generator = itertools.islice(docs_generator, args.limit)

    docs_list = list(docs_generator)

    term_counts = Counter()

    for doc in docs_list:
        tokens_list = list(tokenize(doc.text))
        term_counts.update(tokens_list)

    elapsed_time = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print("--- EAGER VERSION ---")
    print(f"Documents processed: {len(docs_list)}")
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    print(f"Peak memory: {peak_mem / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    main()