"""Query expansion helpers: synonym maps, stop words, and term overlap checks."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Synonym-aware sibling filter
# ---------------------------------------------------------------------------

# Synonym groups for legal/financial terms.  When a query word is a key,
# any word in the corresponding frozenset counts as a match in sibling text.
LEGAL_SYNONYMS: dict[str, frozenset[str]] = {
    "spread": frozenset({"margin", "rate", "spread", "pricing"}),
    "margin": frozenset({"spread", "margin", "rate", "pricing"}),
    "rate": frozenset({"spread", "margin", "rate", "interest", "pricing"}),
    "covenant": frozenset({"covenant", "restriction", "limitation", "prohibition"}),
    "lien": frozenset({"lien", "security", "encumbrance", "pledge", "collateral"}),
    "debt": frozenset({"debt", "indebtedness", "borrowing", "obligation", "loan"}),
    "payment": frozenset({"payment", "distribution", "dividend", "disbursement"}),
    "basket": frozenset({"basket", "exception", "carve-out", "permitted"}),
    "facility": frozenset({"facility", "commitment", "loan", "credit"}),
    "prepayment": frozenset({"prepayment", "repayment", "amortization", "redemption"}),
    "investment": frozenset({"investment", "acquisition", "purchase"}),
    "default": frozenset({"default", "breach", "violation", "event"}),
    "maturity": frozenset({"maturity", "termination", "expiration"}),
    "leverage": frozenset({"leverage", "ratio", "coverage", "test"}),
}

STOP_WORDS: frozenset[str] = frozenset({
    "that", "this", "with", "from", "have", "been", "were", "shall",
    "such", "each", "upon", "into", "under", "more", "than", "also",
})


def query_term_overlap(query: str, text: str, min_overlap: int = 1) -> bool:
    """Check whether *text* shares enough topical vocabulary with *query*.

    Used to filter sibling chunks during expansion so that completely
    unrelated siblings (e.g. a definitions sibling about "Tax" when the
    query is about "liens") are excluded.

    Query words are expanded with ``LEGAL_SYNONYMS`` so that e.g.
    "spread" also matches sibling text containing "margin".
    """
    raw_words = (w.strip(".,;:!?()[]{}\"'") for w in query.split())
    query_words = {
        w.lower() for w in raw_words
        if len(w) >= 4 and w.lower() not in STOP_WORDS
    }
    if not query_words:
        return True  # Can't filter, allow through

    # Expand query words with synonyms (try singular form too)
    expanded_words: set[str] = set()
    for w in query_words:
        expanded_words.add(w)
        if w in LEGAL_SYNONYMS:
            expanded_words.update(LEGAL_SYNONYMS[w])
        elif w.endswith("s") and w[:-1] in LEGAL_SYNONYMS:
            expanded_words.update(LEGAL_SYNONYMS[w[:-1]])

    text_lower = text.lower()
    overlap = sum(1 for w in expanded_words if w in text_lower)
    return overlap >= min_overlap
