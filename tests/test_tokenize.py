from findex.tokenize import tokenize


def test_empty_string():
    assert list(tokenize("")) == []

def test_mixed_case_and_casefold():
    assert list(tokenize("HeLLo WoRlD")) == ["hello", "world"]
    assert list(tokenize("Straße")) == ["strasse"]

def test_cyrillic_support():
    assert list(tokenize("Привет, мир!")) == ["привет", "мир"]

def test_punctuation_is_ignored():
    assert list(tokenize("hello... world?!")) == ["hello", "world"]

def test_unicode_normalization_cafe():
    tokens = list(tokenize("café cafe\u0301"))
    assert tokens[0] == tokens[1]

def test_numbers_and_underscores():
    assert list(tokenize("covid_19 data")) == ["covid_19", "data"]

def test_hyphenated_words():
    assert list(tokenize("state-of-the-art")) == ["state", "of", "the", "art"]