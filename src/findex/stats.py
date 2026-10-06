import argparse
import itertools
import time
import tracemalloc
from collections import Counter
from pathlib import Path

from findex.corpus import iter_documents
from findex.tokenize import tokenize

RESULT_TOP_NUMBERS = 50

def main():
    parser = argparse.ArgumentParser(description="Corpus statistics pipeline")
    parser.add_argument("data_dir", type=Path, help="Path to the corpus directory")

    parser.add_argument("--limit", type=int, default=None, help="Limit the number of documents processed")
    args = parser.parse_args()

    tracemalloc.start()
    start_time = time.perf_counter()

    docs = iter_documents(args.data_dir)

    if args.limit is not None:
        docs = itertools.islice(docs, args.limit)

    doc_count = 0
    term_counts = Counter()

    for doc in docs:
        doc_count += 1

        tokens = tokenize(doc.text)
        term_counts.update(tokens)

    elapsed_time = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    total_tokens = sum(term_counts.values())
    vocab_size = len(term_counts)
    top_50 = term_counts.most_common(RESULT_TOP_NUMBERS)

    print(f"Documents processed: {doc_count}")
    print(f"Total tokens: {total_tokens}")
    print(f"Vocabulary size: {vocab_size}")
    print("\nTop 50 terms:")
    for rank, (term, count) in enumerate(top_50, 1):
        print(f"{rank:2d}. {term:<15} {count}")

    print(f"\nElapsed time: {elapsed_time:.2f} seconds")

    print(f"Peak memory: {peak_mem / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    main()