# Lab 01: Corpus Intake and Streaming Tokenizer

## Corpus
The corpus for this project consists of 6 plain-text copies of Leo Tolstoy's *War and Peace*, downloaded from Project Gutenberg. 
To run the pipeline, ensure these `.txt` files are placed inside the `data/` directory at the root of the project. The `data/` directory is intentionally ignored by git.

## Tokenization Policy
The tokenizer normalizes all text using Unicode NFC and `casefold()` before extracting words with the `\w+` regular expression. 
* **Hyphens:** Words containing hyphens (e.g., "state-of-the-art") are split into separate individual tokens.
* **Apostrophes:** Punctuation is ignored by the regex, meaning words with apostrophes are split (e.g., "don't" becomes "don" and "t").
* **Digits/Numbers:** Numeric characters are matched by `\w+` and are kept as valid tokens.

## Eager vs Lazy Comparison

| Version           | Documents | Peak memory | Elapsed time |
|-------------------|-----------|-------------|--------------|
| eager (lists)     | 6         | 110.03 MB   | 9.15 s       |
| lazy (generators) | 6         | 50.52 MB    | 9.09 s       |

**Why the numbers differ:**
In the eager version, wrapping the operations in `list()` forces the program to load the entire text of all documents (all 6 copies of a massive novel) into RAM at once, and then build massive arrays containing every single token. In the lazy version, the pipeline uses generators (`yield`) to stream the data. It holds only one document in memory at any given time and processes its tokens one by one. As a result, the memory footprint is halved, because the only data structure that actually accumulates data in memory is the `Counter` vocabulary dictionary at the very end of the pipeline.