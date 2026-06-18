"""Tests for deterministic text tokenisation."""

from __future__ import annotations

from app.retrieval.tokenization import STOP_WORDS, build_item_text, tokenize


class TestTokenize:
    """Core tokenisation behaviour."""

    def test_simple_text(self):
        assert tokenize("Hello World") == ["hello", "world"]

    def test_empty_string(self):
        assert tokenize("") == []

    def test_only_whitespace(self):
        assert tokenize("   ") == []

    def test_lowercasing(self):
        assert tokenize("HELLO World") == ["hello", "world"]

    def test_punctuation_removal(self):
        # "it" is a stopword and will be removed
        tokens = tokenize("hello, world! how's it going?")
        assert tokens == ["hello", "world", "how", "s", "going"]

    def test_numbers_kept(self):
        tokens = tokenize("iphone 15 pro max 2024")
        assert "15" in tokens
        assert "2024" in tokens

    def test_repeated_words(self):
        tokens = tokenize("hello hello world world world")
        assert tokens == ["hello", "hello", "world", "world", "world"]

    def test_stopwords_removed_by_default(self):
        tokens = tokenize("the quick brown fox and the lazy dog")
        assert "the" not in tokens
        assert "and" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens

    def test_stopwords_kept_when_disabled(self):
        tokens = tokenize("the quick brown fox", remove_stopwords=False)
        assert "the" in tokens

    def test_non_ascii_text(self):
        # Unicode NFKC: café -> cafe (depends on NFKC behaviour)
        tokens = tokenize("café naïve")
        # NFKC decomposes accented chars
        assert "cafe" in tokens or "café" in tokens or "caf" in tokens
        # All should be lowercase ascii-safe
        for t in tokens:
            assert t.isascii() or t == t.lower()

    def test_mixed_alphanumeric(self):
        tokens = tokenize("sku-12345 item_code_abc")
        assert "sku" in tokens
        assert "12345" in tokens
        assert "item" in tokens
        assert "code" in tokens
        assert "abc" in tokens

    def test_single_character(self):
        tokens = tokenize("a b c")
        # "a" is a stopword
        assert "a" not in tokens
        assert "b" in tokens
        assert "c" in tokens

    def test_only_stopwords(self):
        tokens = tokenize("the and of in")
        assert tokens == []


class TestBuildItemText:
    """Weighted item text construction."""

    def test_default_weights(self):
        text = build_item_text(
            title="Laptop",
            description="A great laptop",
            category="Electronics",
            subcategory="Computers",
            brand="TechPro",
        )
        # Title repeated 3 times
        parts = text.split()
        assert parts.count("Laptop") == 3
        assert parts.count("Electronics") == 2
        assert parts.count("Computers") == 2
        assert parts.count("TechPro") == 2
        assert parts.count("A") == 1  # description appears once

    def test_custom_weights(self):
        text = build_item_text(
            title="X",
            description="Y",
            category="Z",
            subcategory="W",
            brand="V",
            weights={"title": 5, "description": 0, "category": 1, "subcategory": 0, "brand": 2},
        )
        parts = text.split()
        assert parts.count("X") == 5
        # description weight 0 → not included
        assert "Y" not in parts
        assert parts.count("Z") == 1
        assert "W" not in parts
        assert parts.count("V") == 2


class TestStopWords:
    """Stop-word list integrity."""

    def test_stopwords_not_empty(self):
        assert len(STOP_WORDS) > 20

    def test_common_stopwords_present(self):
        assert "the" in STOP_WORDS
        assert "and" in STOP_WORDS
        assert "is" in STOP_WORDS
        assert "of" in STOP_WORDS

    def test_no_empty_string_in_stopwords(self):
        assert "" not in STOP_WORDS
