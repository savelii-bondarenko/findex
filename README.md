# findex

A Python search engine built incrementally: streaming corpus intake, tokenization, an inverted index, Boolean search, persistence, and memory measurements.

## Setup

Install [uv](https://docs.astral.sh/uv/) and Python 3.15, then run:

```powershell
git clone https://github.com/savelii-bondarenko/findex.git
cd findex
uv sync --python 3.15
```

Run all commands below from the project root. Python 3.15.0 was used for Lab 02 measurements; Lab 01 measurements were collected earlier.

## Corpus

Download the UTF-8 [plain-text edition of War and Peace](https://www.gutenberg.org/cache/epub/2600/pg2600.txt) from [Project Gutenberg](https://www.gutenberg.org/ebooks/2600) and place it in `data/`. Each `.txt` file is one document. To reproduce these experiments, use 6 identical copies for Lab 01 or 11 identical copies for Lab 02, with different filenames.

`data/`, generated indexes, and benchmark files should be excluded from Git:

```gitignore
data/
index.bin
index.json
benchmarks/
```

## Lab 01 — Corpus Intake and Streaming Tokenizer

### Implementation

- `corpus.py`: `Document(doc_id, path, text)` and a generator that reads one UTF-8 file at a time; files with decoding errors are reported and skipped.
- `tokenize.py`: a token generator using NFC normalization, `casefold()`, and `re.finditer`.
- `stats.py`: document count, token count, vocabulary size, top-50 terms, elapsed time, and peak traced memory; `--limit` uses `islice`.
- `eager_stats.py`: comparison implementation that retains all documents and materializes the current document's tokens.
- `tests/test_tokenize.py`: checks for case folding, Cyrillic, Unicode normalization, punctuation, empty input, numbers, underscores, and hyphens.

### Tokenization Policy

The tokenizer applies NFC and `casefold()` before matching `\w+`.

- Hyphens split words: `state-of-the-art` becomes four tokens.
- Apostrophes split words: `don't` becomes `don` and `t`.
- Digits and underscores are retained: `covid_19` is one token.

### Run

```powershell
uv run python -m findex.stats data/
uv run python -m findex.stats data/ --limit 2
uv run python -m findex.eager_stats data/
```

### Eager vs. Lazy

Original Lab 01 measurements on 6 documents:

| Version | Documents | Peak memory, MiB | Elapsed time, s |
|---|---:|---:|---:|
| Eager (lists) | 6 | 110.03 | 9.15 |
| Lazy (generators) | 6 | 50.52 | 9.09 |

The eager implementation retains all document texts and builds a token list for each document while processing it. The lazy pipeline avoids these lists and consumes tokens incrementally. The vocabulary counter grows in both versions; document text and normalized strings also contribute to peak memory.

## Lab 02 — Inverted Index, Boolean Search, and Persistence

### Implementation

- **M1 — `index.py`:** builds `term → list[Posting(doc_id, tf)]` in one streaming pass using `defaultdict` and a per-document `Counter`. Postings are sorted by document ID. The index also stores document lengths and path/title metadata. `Posting` and `DocMeta` are frozen, slotted, hashable dataclasses.
- **M2 — `search.py`:** Boolean AND, OR, and NOT using two-pointer merges, with a set-based alternative selected through `--engine`. Results include document IDs, titles, and paths.
- **M3 — `store.py`:** saves and reloads indexes using pickle or JSON. The `.json` extension selects JSON; other extensions select pickle.
- **M4 — `memory_study.py`:** compares plain dataclasses, slotted dataclasses, and pairs of `array('I')` buffers containing document IDs and term frequencies.

Positions and phrase search are not implemented.

### Build and Search

```powershell
# Build and save in both formats
uv run python -m findex.index data/ --out index.bin
uv run python -m findex.index data/ --out index.json

# Boolean search
uv run python -m findex.search index.bin "war peace"
uv run python -m findex.search index.bin "war OR peace"
uv run python -m findex.search index.bin "war NOT peace"
uv run python -m findex.search index.bin "NOT war"

# Set engine and JSON loading
uv run python -m findex.search index.bin "war peace" --engine set
uv run python -m findex.search index.json "war peace"

# Measurements
uv run python -m findex.search index.bin --benchmark
uv run python -m findex.memory_study data/
uv run python -m findex.memory_study data/ --limit 2
```

Operators must be uppercase. Adjacent terms use implicit AND. AND/OR are evaluated left to right; NOT negates the next term, and `a NOT b` means `a AND NOT b`. Parentheses are unsupported. Query terms use the same tokenizer as indexed documents.

Only load trusted pickle files created by this application: `pickle.load()` can execute arbitrary code from an untrusted file.

### M1/M3 — Build and Persistence Results

Corpus: **11 documents**, **17,724 unique terms**. Times are in seconds. Build/save and search/load measurements below were collected with `tracemalloc` enabled.

| Format | Build, s | Save, s | Build + save elapsed, s | File size, bytes | Peak build/save memory, MiB |
|---|---:|---:|---:|---:|---:|
| pickle | 19.456391 | 2.091643 | 21.548056 | 2,991,245 | 63.13 |
| JSON | 19.441602 | 4.813739 | 24.255372 | 1,464,383 | 63.13 |

JSON was smaller and slower to save in this run. It stores compact numeric posting pairs, while pickle stores the Python object representation. Both formats restored an index that returned the same results for `war peace`.

### M2 — Search Results

| Format | Engine | Query | Matches | Query, s | Load, s | Elapsed, s | Peak memory, MiB |
|---|---|---|---:|---:|---:|---:|---:|
| pickle | merge | `war peace` | 11 | 0.000158 | 2.924076 | 2.924248 | 39.41 |
| pickle | merge | `war OR peace` | 11 | 0.000135 | 2.939323 | 2.939472 | 39.41 |
| pickle | merge | `war NOT peace` | 0 | 0.000159 | 2.955733 | 2.955907 | 39.41 |
| pickle | merge | `NOT war` | 0 | 0.000106 | 3.072223 | 3.072343 | 39.41 |
| pickle | set | `war peace` | 11 | 0.000156 | 3.021370 | 3.021540 | 39.41 |
| JSON | merge | `war peace` | 11 | 0.000157 | 1.239812 | 1.239975 | 33.15 |

All files contain the same book, so `war` and `peace` occur in every document. AND/OR return all 11 documents; both exclusion queries return none.

### M2 — Merge vs. Set Benchmark

Average microseconds per query over 1,000 repetitions, without `tracemalloc`. Timings include query parsing, posting ID extraction, set construction where applicable, and sorted results. The benchmark checks that both engines return identical results for each query.

| Selected group | Query | Merge, us | Set, us |
|---|---|---:|---:|
| common | `êtes AND être` | 8.12 | 7.17 |
| common | `êtes OR être` | 11.60 | 16.07 |
| common | `êtes NOT être` | 15.09 | 9.68 |
| rare | `000 AND 07` | 9.67 | 8.44 |
| rare | `000 OR 07` | 10.75 | 7.98 |
| rare | `000 NOT 07` | 9.04 | 8.65 |

The benchmark selects terms by document frequency. Because all 11 documents are identical, every indexed term has document frequency 11. The `common` and `rare` labels therefore represent tied selections, not different posting lengths. These short-list measurements do not establish how the engines compare on a diverse corpus. Set was faster in five cases; merge was faster for `êtes OR être`.

The benchmark command separately reported index load time **2.934196 s**, elapsed time **2.934217 s**, and peak traced memory **39.41 MiB** before running the timed query repetitions.

### M4 — Posting Storage Study

Each variant rebuilds the same corpus and retains document lengths and metadata. Peak memory is measured with `tracemalloc` during construction only. All variants use pickle for file-size and load-time comparisons. Load timing runs without `tracemalloc`; these times should not be compared directly with the instrumented M3 load times.

Full corpus: **11 documents**, **17,724 unique terms**.

| Representation | Build, s | Peak build memory, MiB | Index size, bytes | Load, s |
|---|---:|---:|---:|---:|
| Plain dataclass | 19.713 | 69.91 | 3,771,214 | 0.165137 |
| Slotted dataclass | 19.559 | 62.96 | 2,991,226 | 0.339883 |
| `array('I')` pairs | 19.438 | 57.67 | 2,350,227 | 0.035853 |

Smaller corpus: **2 documents**, **17,724 unique terms**.

| Representation | Build, s | Peak build memory, MiB | Index size, bytes | Load, s |
|---|---:|---:|---:|---:|
| Plain dataclass | 3.620 | 54.04 | 896,452 | 0.035762 |
| Slotted dataclass | 3.656 | 53.18 | 754,618 | 0.063563 |
| `array('I')` pairs | 3.688 | 55.21 | 1,073,208 | 0.030681 |

Plain dataclasses add an attribute dictionary to each posting. Slots remove that overhead; arrays replace posting instances and their integer references with compact integer buffers. On 11 documents, peak build memory fell from 69.91 to 62.96 MiB with slots and to 57.67 MiB with arrays. Text, normalization, counters, and metadata still contribute to the peak. With only two documents, allocating two arrays per term outweighed their compact element storage, producing a larger peak and file. Slots reduced size but loaded more slowly in these runs; compact storage does not guarantee faster deserialization.

Benchmark files are written to `benchmarks/` and are separate from the searchable `index.bin` and `index.json`. Measurements are individual runs, not multi-run averages, except for the repeated Boolean benchmark.

## Checks

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
## Fix

```powershell
uv run ruff check .
uv run ruff format --check .
```

Tokenizer tests are included. The build, search, and benchmark results above are recorded manual runs; successful lint/format checks are not claimed here.
