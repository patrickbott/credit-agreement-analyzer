"""Retrieval quality tests for the hybrid retriever pipeline.

These tests verify that realistic credit agreement queries actually find
the right chunks -- not just that the mechanical plumbing (RRF, dedup,
ordering) works.  They use real BM25 keyword matching with a mock vector
store to avoid downloading embedding models in CI.

The fixtures simulate a typical leveraged buyout credit agreement with
sections covering: preamble, facility terms (revolver, term loan,
amortization, prepayment), negative covenants (debt, liens, restricted
payments), financial covenants, events of default, and definitions.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from unittest.mock import MagicMock

from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.processing.definitions import DefinitionsIndex
from credit_analyzer.processing.section_detector import SectionType
from credit_analyzer.retrieval.bm25_store import BM25Store
from credit_analyzer.retrieval.embedder import Embedder
from credit_analyzer.retrieval.hybrid_retriever import HybridRetriever
from credit_analyzer.retrieval.vector_store import RetrievedChunk, VectorStore

# ---------------------------------------------------------------------------
# Realistic credit agreement text fixtures
# ---------------------------------------------------------------------------

_DOC_ID = "test_doc"

_FIXTURE_CHUNKS: dict[str, dict[str, Any]] = {
    "preamble": dict(
        text=(
            "CREDIT AGREEMENT dated as of January 15, 2024, among ACME HOLDINGS LLC, "
            "a Delaware limited liability company (the \"Borrower\"), ACME PARENT INC., "
            "a Delaware corporation (\"Holdings\"), the Lenders party hereto, and "
            "JPMORGAN CHASE BANK, N.A., as Administrative Agent. "
            "RECITALS: The Borrower has requested that the Lenders extend credit in the "
            "form of (a) Term Loans in an aggregate principal amount of $500,000,000 and "
            "(b) Revolving Credit Commitments in an aggregate principal amount of $100,000,000."
        ),
        section_type="preamble",
        section_id="PREAMBLE",
        section_title="Preamble and Recitals",
        article_number=0,
        article_title="Preamble and Recitals",
        chunk_type="text",
        chunk_index=0,
    ),
    "facility_terms_revolver": dict(
        text=(
            "2.01 Revolving Credit Commitments. Subject to the terms and conditions "
            "set forth herein, each Revolving Credit Lender agrees to make Revolving Credit "
            "Loans to the Borrower from time to time during the Revolving Credit Availability "
            "Period in an aggregate principal amount that will not result in such Lender's "
            "Revolving Credit Exposure exceeding such Lender's Revolving Credit Commitment. "
            "The Revolving Credit Commitment shall be $100,000,000. The Revolving Credit "
            "Maturity Date shall be January 15, 2029."
        ),
        section_type="facility_terms",
        section_id="2.01",
        section_title="Revolving Credit Commitments",
        article_number=2,
        article_title="THE CREDIT FACILITIES",
        chunk_type="text",
        chunk_index=0,
    ),
    "facility_terms_term_loan": dict(
        text=(
            "2.02 Term Loans. Subject to the terms and conditions set forth herein, "
            "each Term Lender agrees to make a Term Loan to the Borrower on the Closing Date "
            "in a principal amount equal to such Term Lender's Term Loan Commitment. The "
            "aggregate principal amount of Term Loans shall be $500,000,000. The Term Loan "
            "Maturity Date shall be January 15, 2031. Term Loans that are repaid may not "
            "be reborrowed."
        ),
        section_type="facility_terms",
        section_id="2.02",
        section_title="Term Loans",
        article_number=2,
        article_title="THE CREDIT FACILITIES",
        chunk_type="text",
        chunk_index=0,
    ),
    "facility_terms_interest": dict(
        text=(
            "2.03 Interest. (a) Each Term Loan and Revolving Credit Loan shall bear interest "
            "at a rate per annum equal to, at the election of the Borrower, the Adjusted Term "
            "SOFR Rate plus the Applicable Rate or the ABR plus the Applicable Rate. "
            "Interest shall be payable in arrears on each Interest Payment Date."
        ),
        section_type="facility_terms",
        section_id="2.03",
        section_title="Interest",
        article_number=2,
        article_title="THE CREDIT FACILITIES",
        chunk_type="text",
        chunk_index=0,
    ),
    "facility_terms_fees": dict(
        text=(
            "2.04 Fees. (a) Commitment Fee. The Borrower agrees to pay to each Revolving "
            "Credit Lender a commitment fee at a rate equal to the Applicable Rate for "
            "commitment fees on the average daily unused Revolving Credit Commitment of "
            "such Lender during each quarter. (b) Letter of Credit Fee. The Borrower shall "
            "pay a letter of credit fee equal to the Applicable Rate for SOFR Loans times "
            "the daily average stated amount of each Letter of Credit."
        ),
        section_type="facility_terms",
        section_id="2.04",
        section_title="Fees",
        article_number=2,
        article_title="THE CREDIT FACILITIES",
        chunk_type="text",
        chunk_index=0,
    ),
    "facility_terms_amortization": dict(
        text=(
            "2.05 Amortization of Term Loans. The Borrower shall repay Term Loan "
            "Borrowings on the last Business Day of each March, June, September and December, "
            "commencing with the first full fiscal quarter ending after the Closing Date, "
            "in an aggregate principal amount equal to 0.25% of the original aggregate "
            "principal amount of all Term Loans."
        ),
        section_type="facility_terms",
        section_id="2.05",
        section_title="Amortization of Term Loans",
        article_number=2,
        article_title="THE CREDIT FACILITIES",
        chunk_type="text",
        chunk_index=0,
    ),
    "facility_terms_prepayment": dict(
        text=(
            "2.06 Mandatory Prepayment. (a) Excess Cash Flow. Within ten Business Days "
            "after financial statements are delivered for any fiscal year, the Borrower shall "
            "prepay Term Loan Borrowings in an aggregate amount equal to (i) 50% of Excess "
            "Cash Flow for such fiscal year if the Total Net Leverage Ratio exceeds 4.50:1.00, "
            "(ii) 25% of Excess Cash Flow if the Total Net Leverage Ratio exceeds 3.50:1.00 "
            "but is less than or equal to 4.50:1.00, and (iii) 0% if the Total Net Leverage "
            "Ratio is less than or equal to 3.50:1.00."
        ),
        section_type="facility_terms",
        section_id="2.06",
        section_title="Mandatory Prepayment",
        article_number=2,
        article_title="THE CREDIT FACILITIES",
        chunk_type="text",
        chunk_index=0,
    ),
    "negative_covenants_debt": dict(
        text=(
            "7.03 Indebtedness. The Borrower will not, and will not permit any "
            "Restricted Subsidiary to, create, incur, assume or permit to exist any "
            "Indebtedness, except: (a) Indebtedness created under the Loan Documents; "
            "(b) Indebtedness existing on the Closing Date and set forth on Schedule 7.03; "
            "(c) Indebtedness of the Borrower or any Restricted Subsidiary in an aggregate "
            "principal amount not to exceed the greater of $75,000,000 and 15% of "
            "Consolidated EBITDA at any time outstanding (the \"General Debt Basket\");"
        ),
        section_type="negative_covenants",
        section_id="7.03",
        section_title="Indebtedness",
        article_number=7,
        article_title="NEGATIVE COVENANTS",
        chunk_type="text",
        chunk_index=0,
    ),
    "negative_covenants_debt_incremental": dict(
        text=(
            "(d) Incremental Term Loans and Incremental Revolving Credit Commitments "
            "in an aggregate principal amount not to exceed the sum of (I) the greater of "
            "$200,000,000 and 100% of Consolidated EBITDA (the \"Fixed Incremental Amount\") "
            "plus (II) an unlimited amount so long as, on a pro forma basis after giving "
            "effect to the incurrence thereof, the Total Net Leverage Ratio does not exceed "
            "4.00:1.00 (the \"Ratio Incremental Amount\"); provided that Incremental Term Loans "
            "shall have a maturity date no earlier than the Latest Maturity Date."
        ),
        section_type="negative_covenants",
        section_id="7.03",
        section_title="Indebtedness",
        article_number=7,
        article_title="NEGATIVE COVENANTS",
        chunk_type="text",
        chunk_index=1,
    ),
    "negative_covenants_liens": dict(
        text=(
            "7.01 Liens. The Borrower will not, and will not permit any Restricted "
            "Subsidiary to, create, incur, assume or permit to exist any Lien on any property "
            "or asset now owned or hereafter acquired by it, except Permitted Liens. The "
            "general lien basket shall not exceed the greater of $50,000,000 and 10% of "
            "Consolidated EBITDA."
        ),
        section_type="negative_covenants",
        section_id="7.01",
        section_title="Liens",
        article_number=7,
        article_title="NEGATIVE COVENANTS",
        chunk_type="text",
        chunk_index=0,
    ),
    "negative_covenants_rp": dict(
        text=(
            "7.06 Restricted Payments. The Borrower will not, and will not permit any "
            "Restricted Subsidiary to, declare or make any Restricted Payment except: "
            "(a) each Restricted Subsidiary may make Restricted Payments to the Borrower; "
            "(b) the Borrower may make Restricted Payments in an aggregate amount not to "
            "exceed the Available Amount; (c) the Borrower may make Restricted Payments in "
            "an aggregate amount not to exceed the greater of $25,000,000 and 5% of "
            "Consolidated EBITDA."
        ),
        section_type="negative_covenants",
        section_id="7.06",
        section_title="Restricted Payments",
        article_number=7,
        article_title="NEGATIVE COVENANTS",
        chunk_type="text",
        chunk_index=0,
    ),
    "negative_covenants_investments": dict(
        text=(
            "7.04 Investments. The Borrower will not, and will not permit any Restricted "
            "Subsidiary to, make or hold any Investment except: (a) Investments existing on "
            "the Closing Date; (b) Investments in Cash Equivalents; (c) Investments by the "
            "Borrower in any Restricted Subsidiary; (d) Investments in an aggregate amount "
            "not to exceed the greater of $40,000,000 and 8% of Consolidated EBITDA; "
            "(e) Investments funded with the Available Amount."
        ),
        section_type="negative_covenants",
        section_id="7.04",
        section_title="Investments",
        article_number=7,
        article_title="NEGATIVE COVENANTS",
        chunk_type="text",
        chunk_index=0,
    ),
    "negative_covenants_asset_sales": dict(
        text=(
            "7.05 Asset Sales. The Borrower will not, and will not permit any Restricted "
            "Subsidiary to, consummate any Asset Sale unless (a) the consideration received "
            "is at least equal to the fair market value thereof, (b) at least 75% of such "
            "consideration consists of cash or Cash Equivalents, and (c) the Net Cash Proceeds "
            "thereof are applied as a mandatory prepayment pursuant to Section 2.06 to the "
            "extent not reinvested within 365 days."
        ),
        section_type="negative_covenants",
        section_id="7.05",
        section_title="Asset Sales",
        article_number=7,
        article_title="NEGATIVE COVENANTS",
        chunk_type="text",
        chunk_index=0,
    ),
    "financial_covenants": dict(
        text=(
            "8.01 Financial Condition Covenant. (a) Maximum Total Net Leverage Ratio. "
            "The Borrower will not permit the Total Net Leverage Ratio as of the last day of "
            "any Test Period to exceed (i) 5.50:1.00 for the first four Test Periods ending "
            "after the Closing Date, (ii) 5.25:1.00 for the next four Test Periods, "
            "(iii) 5.00:1.00 for the next four Test Periods, and (iv) 4.75:1.00 thereafter. "
            "This covenant shall be tested only if Revolving Credit Exposure exceeds 35% of "
            "the Revolving Credit Commitment as of such date (the \"Springing Covenant\")."
        ),
        section_type="financial_covenants",
        section_id="8.01",
        section_title="Financial Condition Covenant",
        article_number=8,
        article_title="FINANCIAL COVENANTS",
        chunk_type="text",
        chunk_index=0,
    ),
    "financial_covenants_equity_cure": dict(
        text=(
            "8.02 Equity Cure. Notwithstanding Section 8.01, in the event the Borrower "
            "fails to comply with the Financial Condition Covenant, Holdings may make a cash "
            "equity contribution to the Borrower within 10 Business Days after delivery of "
            "financial statements, and such equity contribution shall be deemed to increase "
            "Consolidated EBITDA for such Test Period. The Borrower may exercise this cure "
            "right no more than two times in any four consecutive fiscal quarters and no more "
            "than five times over the life of the facility."
        ),
        section_type="financial_covenants",
        section_id="8.02",
        section_title="Equity Cure",
        article_number=8,
        article_title="FINANCIAL COVENANTS",
        chunk_type="text",
        chunk_index=0,
    ),
    "events_of_default": dict(
        text=(
            "9.01 Events of Default. Each of the following shall constitute an Event "
            "of Default: (a) the Borrower shall fail to pay any principal when due; (b) the "
            "Borrower shall fail to pay any interest or fee within five Business Days after "
            "the date when due; (c) any representation or warranty made by any Loan Party "
            "shall prove to have been incorrect in any material respect; (d) the Borrower "
            "shall fail to observe any covenant contained in Sections 7.01 through 7.10 "
            "or Section 8.01; (e) cross-default: any Indebtedness in excess of $35,000,000 "
            "shall be declared due and payable prior to maturity."
        ),
        section_type="events_of_default",
        section_id="9.01",
        section_title="Events of Default",
        article_number=9,
        article_title="EVENTS OF DEFAULT",
        chunk_type="text",
        chunk_index=0,
    ),
    "affirmative_covenants_reporting": dict(
        text=(
            "6.01 Financial Statements. The Borrower will furnish to the Administrative "
            "Agent: (a) within 90 days after the end of each fiscal year, audited consolidated "
            "financial statements of the Borrower accompanied by an opinion of a nationally "
            "recognized independent public accounting firm; (b) within 45 days after the end "
            "of each fiscal quarter, unaudited consolidated financial statements of the "
            "Borrower; (c) within 5 Business Days after delivery of the financial statements, "
            "a compliance certificate signed by a Responsible Officer."
        ),
        section_type="affirmative_covenants",
        section_id="6.01",
        section_title="Financial Statements",
        article_number=6,
        article_title="AFFIRMATIVE COVENANTS",
        chunk_type="text",
        chunk_index=0,
    ),
    "definitions_applicable_rate": dict(
        text=(
            '"Applicable Rate" means, with respect to any Term Loan or Revolving Credit '
            "Loan, the applicable rate per annum set forth below based upon the Total Net "
            "Leverage Ratio as of the most recent determination date: "
            "Total Net Leverage Ratio > 4.50:1.00: SOFR 3.50% / ABR 2.50% "
            "Total Net Leverage Ratio > 3.50:1.00 but <= 4.50:1.00: SOFR 3.25% / ABR 2.25% "
            "Total Net Leverage Ratio > 2.50:1.00 but <= 3.50:1.00: SOFR 3.00% / ABR 2.00% "
            "Total Net Leverage Ratio <= 2.50:1.00: SOFR 2.75% / ABR 1.75%"
        ),
        section_type="definitions",
        section_id="1.1",
        section_title="Defined Terms",
        article_number=1,
        article_title="DEFINITIONS",
        chunk_type="definition",
        chunk_index=0,
        defined_terms_present=["Applicable Rate"],
    ),
    "definitions_ebitda": dict(
        text=(
            '"Consolidated EBITDA" means, for any period, Consolidated Net Income for '
            "such period plus (a) without duplication and to the extent deducted in determining "
            "Consolidated Net Income, the sum of (i) interest expense, (ii) provision for "
            "income taxes, (iii) depreciation and amortization, (iv) non-cash charges not to "
            "exceed $10,000,000 in the aggregate, and (v) cost savings, operating expense "
            "reductions and synergies projected by the Borrower in good faith to be realized "
            "within 24 months, in an aggregate amount not to exceed 25% of Consolidated EBITDA "
            "(calculated before giving effect to such add-backs)."
        ),
        section_type="definitions",
        section_id="1.1",
        section_title="Defined Terms",
        article_number=1,
        article_title="DEFINITIONS",
        chunk_type="definition",
        chunk_index=1,
        defined_terms_present=["Consolidated EBITDA"],
    ),
    "definitions_leverage_ratio": dict(
        text=(
            '"Total Net Leverage Ratio" means, as of the last day of any Test Period, '
            "the ratio of (a) Consolidated Total Debt as of such date minus unrestricted "
            "cash and Cash Equivalents of the Borrower and the Restricted Subsidiaries in "
            "an amount not to exceed $50,000,000, to (b) Consolidated EBITDA for such "
            "Test Period."
        ),
        section_type="definitions",
        section_id="1.1",
        section_title="Defined Terms",
        article_number=1,
        article_title="DEFINITIONS",
        chunk_type="definition",
        chunk_index=2,
        defined_terms_present=["Total Net Leverage Ratio"],
    ),
    "definitions_available_amount": dict(
        text=(
            '"Available Amount" means, at any time, the sum of (a) $15,000,000 plus '
            "(b) 50% of Consolidated Net Income for each completed fiscal quarter after "
            "the Closing Date (with no offset for negative quarters) plus (c) the aggregate "
            "amount of equity contributions received by the Borrower in cash after the "
            "Closing Date, minus (d) the aggregate amount of Restricted Payments made in "
            "reliance on Section 7.06(b)."
        ),
        section_type="definitions",
        section_id="1.1",
        section_title="Defined Terms",
        article_number=1,
        article_title="DEFINITIONS",
        chunk_type="definition",
        chunk_index=3,
        defined_terms_present=["Available Amount"],
    ),
}


def _build_chunk(key: str) -> Chunk:
    """Build a Chunk object from a fixture entry."""
    spec = _FIXTURE_CHUNKS[key]
    return Chunk(
        chunk_id=key,
        text=spec["text"],
        section_id=spec["section_id"],
        section_title=spec["section_title"],
        article_number=spec["article_number"],
        article_title=spec["article_title"],
        section_type=spec["section_type"],
        chunk_type=spec["chunk_type"],
        page_numbers=spec.get("page_numbers", [1]),
        defined_terms_present=spec.get("defined_terms_present", []),
        chunk_index=spec.get("chunk_index", 0),
        token_count=len(spec["text"].split()),  # rough estimate
    )


def _build_all_chunks() -> list[Chunk]:
    """Build all fixture chunks."""
    return [_build_chunk(key) for key in _FIXTURE_CHUNKS]


def _build_definitions_index() -> dict[str, str]:
    """Build a definitions dict from the definition fixture chunks."""
    definitions: dict[str, str] = {}
    for key, spec in _FIXTURE_CHUNKS.items():
        if spec["chunk_type"] == "definition":
            for term in spec.get("defined_terms_present", []):
                definitions[term] = spec["text"]
    return definitions


def _make_mock_vector_store(chunks: list[Chunk]) -> VectorStore:
    """Create a mock VectorStore that returns results based on keyword overlap.

    Instead of real embeddings, we simulate similarity by counting shared
    words between the query and each chunk's text.  This is intentionally
    crude -- the point is that BM25 does the heavy keyword lifting, and
    the vector store provides supplemental results that should not break
    retrieval.
    """
    mock_store = MagicMock(spec=VectorStore)

    def _search(
        document_id: str,
        query_embedding: Sequence[float],
        top_k: int = 5,
        section_filter: str | None = None,
        section_types_exclude: Sequence[str] | None = None,
    ) -> list[RetrievedChunk]:
        # We stash the query text on the mock so we can do keyword overlap
        query_text = getattr(mock_store, "_last_query_text", "")
        query_words = set(query_text.lower().split())

        candidates = chunks
        if section_filter is not None:
            candidates = [c for c in candidates if c.section_type == section_filter]
        elif section_types_exclude:
            exclude = set(section_types_exclude)
            candidates = [c for c in candidates if c.section_type not in exclude]

        scored: list[tuple[float, Chunk]] = []
        for chunk in candidates:
            chunk_words = set(chunk.text.lower().split())
            overlap = len(query_words & chunk_words)
            if overlap > 0:
                score = overlap / max(len(query_words), 1)
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            RetrievedChunk(chunk=chunk, score=score)
            for score, chunk in scored[:top_k]
        ]

    mock_store.search.side_effect = _search
    return mock_store


def _make_mock_embedder() -> Embedder:
    """Create a mock Embedder that stores the query text for the mock vector store."""
    mock_embedder = MagicMock(spec=Embedder)
    mock_embedder.embed_query.return_value = [0.1] * 384
    return mock_embedder


def _build_test_retriever() -> HybridRetriever:
    """Build a HybridRetriever with real BM25 and mocked vector store.

    Uses real BM25Store for keyword matching (critical for quality tests),
    mock VectorStore with keyword-overlap scoring (avoids model downloads),
    and a DefinitionsIndex built from definition fixtures.

    Patches MIN_RETRIEVAL_SCORE to 0.0 because RRF scores are always
    tiny (0.02-0.04) and the threshold would drop all chunks, leaving
    only the 3-chunk floor -- which obscures real retrieval quality.
    """
    import credit_analyzer.retrieval.hybrid_retriever as _hr
    _hr.MIN_RETRIEVAL_SCORE = 0.0

    chunks = _build_all_chunks()
    definitions = _build_definitions_index()
    defn_index = DefinitionsIndex(definitions=definitions)

    # Real BM25 store with indexed chunks
    bm25_store = BM25Store()
    bm25_store.build_index(chunks)

    # Mock vector store that simulates similarity via keyword overlap
    mock_vector = _make_mock_vector_store(chunks)
    mock_embedder = _make_mock_embedder()

    # Wire up so the mock vector store can access the query text.
    # Capture the return_value directly to avoid recursion through
    # side_effect calling back into the same mock.
    _dummy_embedding: list[float] = [0.1] * 384

    def _embed_and_stash(query: str) -> list[float]:
        mock_vector._last_query_text = query  # type: ignore[attr-defined]
        return _dummy_embedding

    mock_embedder.embed_query.side_effect = _embed_and_stash

    return HybridRetriever(
        vector_store=mock_vector,
        bm25_store=bm25_store,
        embedder=mock_embedder,
        definitions_index=defn_index,
    )


def _get_retrieved_section_ids(
    retriever: HybridRetriever,
    query: str,
    top_k: int = 20,
    section_filter: str | None = None,
) -> set[str]:
    """Run retrieval and return the set of chunk_ids found."""
    result = retriever.retrieve(
        query=query,
        document_id=_DOC_ID,
        top_k=top_k,
        section_filter=section_filter,
    )
    return {hc.chunk.chunk_id for hc in result.chunks}


def _get_retrieved_chunk_ids_for_queries(
    retriever: HybridRetriever,
    queries: list[tuple[str, str | None]],
    top_k: int = 20,
) -> set[str]:
    """Run multiple retrieval queries and return the union of chunk_ids."""
    all_ids: set[str] = set()
    for query, section_filter in queries:
        result = retriever.retrieve(
            query=query,
            document_id=_DOC_ID,
            top_k=top_k,
            section_filter=section_filter,
        )
        all_ids.update(hc.chunk.chunk_id for hc in result.chunks)
    return all_ids


# ---------------------------------------------------------------------------
# Section 1: Transaction Overview
# ---------------------------------------------------------------------------


def test_section1_transaction_overview_retrieves_preamble() -> None:
    """Section 1 queries should retrieve the preamble with borrower and facility info."""
    retriever = _build_test_retriever()

    from credit_analyzer.generation.report_template import SECTION_01_TRANSACTION_OVERVIEW

    queries = [
        (rq.query, rq.section_filter)
        for rq in SECTION_01_TRANSACTION_OVERVIEW.retrieval_queries
    ]
    chunk_ids = _get_retrieved_chunk_ids_for_queries(retriever, queries)

    assert "preamble" in chunk_ids, (
        "Transaction overview queries should retrieve the preamble containing "
        "borrower name, agent, and facility amounts"
    )


# ---------------------------------------------------------------------------
# Section 2: Facility Summary
# ---------------------------------------------------------------------------


def test_section2_facility_summary_retrieves_all_facilities() -> None:
    """Section 2 queries should retrieve revolver, term loan, amortization, and prepayment."""
    retriever = _build_test_retriever()

    from credit_analyzer.generation.report_template import SECTION_02_FACILITY_AND_PRICING

    queries = [
        (rq.query, rq.section_filter)
        for rq in SECTION_02_FACILITY_AND_PRICING.retrieval_queries
    ]
    chunk_ids = _get_retrieved_chunk_ids_for_queries(retriever, queries)

    assert "facility_terms_revolver" in chunk_ids, (
        "Facility summary should retrieve the revolving credit commitment section"
    )
    assert "facility_terms_term_loan" in chunk_ids, (
        "Facility summary should retrieve the term loan section"
    )
    assert "facility_terms_amortization" in chunk_ids, (
        "Facility summary should retrieve the amortization schedule"
    )
    assert "facility_terms_prepayment" in chunk_ids, (
        "Facility summary should retrieve mandatory prepayment terms"
    )


# ---------------------------------------------------------------------------
# Section 3: Pricing
# ---------------------------------------------------------------------------


def test_section3_pricing_retrieves_interest_and_fees() -> None:
    """Section 3 queries should retrieve interest rate, fee, and pricing grid chunks."""
    retriever = _build_test_retriever()

    from credit_analyzer.generation.report_template import SECTION_02_FACILITY_AND_PRICING

    queries = [
        (rq.query, rq.section_filter)
        for rq in SECTION_02_FACILITY_AND_PRICING.retrieval_queries
    ]
    chunk_ids = _get_retrieved_chunk_ids_for_queries(retriever, queries)

    assert "facility_terms_interest" in chunk_ids, (
        "Pricing queries should retrieve the interest rate section"
    )
    assert "facility_terms_fees" in chunk_ids, (
        "Pricing queries should retrieve the fees section (commitment fee, LC fee)"
    )


# ---------------------------------------------------------------------------
# Section 5: Financial Covenants
# ---------------------------------------------------------------------------


def test_section5_financial_covenants_retrieves_leverage_test() -> None:
    """Section 5 queries should retrieve the leverage ratio covenant with test levels."""
    retriever = _build_test_retriever()

    from credit_analyzer.generation.report_template import SECTION_04_FINANCIAL_COVENANTS

    queries = [
        (rq.query, rq.section_filter)
        for rq in SECTION_04_FINANCIAL_COVENANTS.retrieval_queries
    ]
    chunk_ids = _get_retrieved_chunk_ids_for_queries(retriever, queries)

    assert "financial_covenants" in chunk_ids, (
        "Financial covenant queries should retrieve the leverage ratio test section"
    )


def test_section5_financial_covenants_retrieves_equity_cure() -> None:
    """Section 5 equity cure query should retrieve the equity cure provision."""
    retriever = _build_test_retriever()

    from credit_analyzer.generation.report_template import SECTION_04_FINANCIAL_COVENANTS

    # Find the equity cure query specifically
    equity_cure_queries = [
        (rq.query, rq.section_filter)
        for rq in SECTION_04_FINANCIAL_COVENANTS.retrieval_queries
        if "equity cure" in rq.query.lower()
    ]
    assert equity_cure_queries, "Expected an equity cure query in Section 5 template"

    chunk_ids = _get_retrieved_chunk_ids_for_queries(retriever, equity_cure_queries)
    assert "financial_covenants_equity_cure" in chunk_ids, (
        "Equity cure query should retrieve the equity cure provision"
    )


# ---------------------------------------------------------------------------
# Section 6: Debt Capacity (Negative Covenants -- Indebtedness)
# ---------------------------------------------------------------------------


def test_section6_debt_capacity_retrieves_indebtedness() -> None:
    """Section 6 queries should retrieve the indebtedness covenant."""
    retriever = _build_test_retriever()

    from credit_analyzer.generation.report_template import SECTION_05_DEBT_CAPACITY

    queries = [
        (rq.query, rq.section_filter)
        for rq in SECTION_05_DEBT_CAPACITY.retrieval_queries
    ]
    chunk_ids = _get_retrieved_chunk_ids_for_queries(retriever, queries)

    assert "negative_covenants_debt" in chunk_ids, (
        "Debt capacity queries should retrieve the general indebtedness section"
    )


def test_section6_debt_capacity_retrieves_incremental() -> None:
    """Section 6 should retrieve both general debt basket and incremental terms."""
    retriever = _build_test_retriever()

    from credit_analyzer.generation.report_template import SECTION_05_DEBT_CAPACITY

    queries = [
        (rq.query, rq.section_filter)
        for rq in SECTION_05_DEBT_CAPACITY.retrieval_queries
    ]
    chunk_ids = _get_retrieved_chunk_ids_for_queries(retriever, queries)

    assert "negative_covenants_debt_incremental" in chunk_ids, (
        "Debt capacity queries should retrieve the incremental facility terms "
        "(Fixed Incremental Amount, Ratio Incremental Amount)"
    )


# ---------------------------------------------------------------------------
# Section 7: Liens
# ---------------------------------------------------------------------------


def test_section7_liens_retrieves_lien_covenant() -> None:
    """Section 7 queries should retrieve the liens negative covenant."""
    retriever = _build_test_retriever()

    from credit_analyzer.generation.report_template import SECTION_06_LIENS

    queries = [
        (rq.query, rq.section_filter)
        for rq in SECTION_06_LIENS.retrieval_queries
    ]
    chunk_ids = _get_retrieved_chunk_ids_for_queries(retriever, queries)

    assert "negative_covenants_liens" in chunk_ids, (
        "Liens queries should retrieve the liens covenant section (7.01)"
    )


# ---------------------------------------------------------------------------
# Section 8: Restricted Payments
# ---------------------------------------------------------------------------


def test_section8_restricted_payments_retrieves_rp_covenant() -> None:
    """Section 8 queries should retrieve the restricted payments covenant."""
    retriever = _build_test_retriever()

    from credit_analyzer.generation.report_template import SECTION_07_RESTRICTED_PAYMENTS

    queries = [
        (rq.query, rq.section_filter)
        for rq in SECTION_07_RESTRICTED_PAYMENTS.retrieval_queries
    ]
    chunk_ids = _get_retrieved_chunk_ids_for_queries(retriever, queries)

    assert "negative_covenants_rp" in chunk_ids, (
        "Restricted payments queries should retrieve the RP covenant (7.06)"
    )


# ---------------------------------------------------------------------------
# Section 9: Investments and Asset Sales
# ---------------------------------------------------------------------------


def test_section9_investments_retrieves_investment_covenant() -> None:
    """Section 9 queries should retrieve the investments covenant."""
    retriever = _build_test_retriever()

    from credit_analyzer.generation.report_template import (
        SECTION_08_INVESTMENTS_AND_ASSET_SALES,
    )

    queries = [
        (rq.query, rq.section_filter)
        for rq in SECTION_08_INVESTMENTS_AND_ASSET_SALES.retrieval_queries
    ]
    chunk_ids = _get_retrieved_chunk_ids_for_queries(retriever, queries)

    assert "negative_covenants_investments" in chunk_ids, (
        "Investment queries should retrieve the investments covenant (7.04)"
    )


def test_section9_asset_sales_retrieves_asset_sale_covenant() -> None:
    """Section 9 should also retrieve asset sale provisions."""
    retriever = _build_test_retriever()

    from credit_analyzer.generation.report_template import (
        SECTION_08_INVESTMENTS_AND_ASSET_SALES,
    )

    queries = [
        (rq.query, rq.section_filter)
        for rq in SECTION_08_INVESTMENTS_AND_ASSET_SALES.retrieval_queries
    ]
    chunk_ids = _get_retrieved_chunk_ids_for_queries(retriever, queries)

    assert "negative_covenants_asset_sales" in chunk_ids, (
        "Asset sale queries should retrieve the asset sales covenant (7.05)"
    )


# ---------------------------------------------------------------------------
# Section 10: Other Provisions
# ---------------------------------------------------------------------------


def test_section10_retrieves_events_of_default() -> None:
    """Section 10 queries should retrieve events of default."""
    retriever = _build_test_retriever()

    from credit_analyzer.generation.report_template import SECTION_10_OTHER_PROVISIONS

    queries = [
        (rq.query, rq.section_filter)
        for rq in SECTION_10_OTHER_PROVISIONS.retrieval_queries
    ]
    chunk_ids = _get_retrieved_chunk_ids_for_queries(retriever, queries)

    assert "events_of_default" in chunk_ids, (
        "Other provisions queries should retrieve the events of default section"
    )


def test_section10_retrieves_reporting_requirements() -> None:
    """Section 10 should retrieve affirmative covenant reporting requirements."""
    retriever = _build_test_retriever()

    from credit_analyzer.generation.report_template import SECTION_10_OTHER_PROVISIONS

    queries = [
        (rq.query, rq.section_filter)
        for rq in SECTION_10_OTHER_PROVISIONS.retrieval_queries
    ]
    chunk_ids = _get_retrieved_chunk_ids_for_queries(retriever, queries)

    assert "affirmative_covenants_reporting" in chunk_ids, (
        "Other provisions queries should retrieve the financial reporting section (6.01)"
    )


# ---------------------------------------------------------------------------
# Ad-hoc quality tests: specific queries should find specific content
# ---------------------------------------------------------------------------


def test_pricing_grid_retrieved_for_rate_query() -> None:
    """A query about interest rates should retrieve the Applicable Rate definition."""
    retriever = _build_test_retriever()

    chunk_ids = _get_retrieved_section_ids(
        retriever, "What is the interest rate pricing grid?", top_k=10,
    )

    # The Applicable Rate definition contains the full pricing grid
    assert "definitions_applicable_rate" in chunk_ids or "facility_terms_interest" in chunk_ids, (
        "Interest rate query should retrieve either the Applicable Rate definition "
        "or the interest section"
    )


def test_leverage_ratio_query_retrieves_financial_covenant() -> None:
    """A query about the leverage ratio should find the financial covenant section."""
    retriever = _build_test_retriever()

    chunk_ids = _get_retrieved_section_ids(
        retriever, "What is the maximum leverage ratio?", top_k=10,
    )

    assert "financial_covenants" in chunk_ids, (
        "Leverage ratio query should retrieve the financial covenant with test levels"
    )


def test_excess_cash_flow_sweep_query() -> None:
    """Query about excess cash flow sweep should find the prepayment section."""
    retriever = _build_test_retriever()

    chunk_ids = _get_retrieved_section_ids(
        retriever, "What is the excess cash flow sweep percentage?", top_k=10,
    )

    assert "facility_terms_prepayment" in chunk_ids, (
        "Excess cash flow query should retrieve the mandatory prepayment section"
    )


def test_incremental_facility_query() -> None:
    """Query about incremental facilities should find the incremental debt provision."""
    retriever = _build_test_retriever()

    chunk_ids = _get_retrieved_section_ids(
        retriever, "What is the incremental facility capacity?", top_k=10,
    )

    assert "negative_covenants_debt_incremental" in chunk_ids, (
        "Incremental facility query should retrieve the incremental term loan provision"
    )


def test_dividend_distribution_query_retrieves_rp() -> None:
    """Query about dividends/distributions should find restricted payments."""
    retriever = _build_test_retriever()

    chunk_ids = _get_retrieved_section_ids(
        retriever, "Can the borrower pay dividends or distributions?", top_k=10,
    )

    assert "negative_covenants_rp" in chunk_ids, (
        "Dividend/distribution query should retrieve the restricted payments covenant"
    )


def test_ebitda_definition_query() -> None:
    """Query about EBITDA should find the Consolidated EBITDA definition."""
    retriever = _build_test_retriever()

    chunk_ids = _get_retrieved_section_ids(
        retriever, "How is Consolidated EBITDA defined?", top_k=10,
    )

    assert "definitions_ebitda" in chunk_ids, (
        "EBITDA query should retrieve the Consolidated EBITDA definition"
    )


def test_cross_default_query() -> None:
    """Query about cross-default should find the events of default section."""
    retriever = _build_test_retriever()

    chunk_ids = _get_retrieved_section_ids(
        retriever, "What is the cross-default threshold?", top_k=10,
    )

    assert "events_of_default" in chunk_ids, (
        "Cross-default query should retrieve the events of default section"
    )


# ---------------------------------------------------------------------------
# Section filter alignment: ensure report template filters are valid
# ---------------------------------------------------------------------------


def test_section_filters_match_detector_types() -> None:
    """All section_filter values in report templates are valid SectionType values."""
    from credit_analyzer.generation.report_template import ALL_REPORT_SECTIONS

    # Extract all valid section types from the Literal type alias
    valid_types = set(SectionType.__args__)  # type: ignore[attr-defined]

    for section in ALL_REPORT_SECTIONS:
        for rq in section.retrieval_queries:
            if rq.section_filter is not None:
                assert rq.section_filter in valid_types, (
                    f"Section {section.section_number} ({section.title}) has "
                    f"retrieval query with invalid section_filter='{rq.section_filter}'. "
                    f"Valid section types: {sorted(valid_types)}"
                )


# ---------------------------------------------------------------------------
# Retrieval non-empty: every report section query returns at least one chunk
# ---------------------------------------------------------------------------


def test_all_report_queries_return_results() -> None:
    """Every retrieval query in every report section should return at least one chunk.

    This catches queries that would return empty results due to keyword
    mismatches, overly restrictive section filters, or missing fixture
    coverage.
    """
    retriever = _build_test_retriever()

    from credit_analyzer.generation.report_template import ALL_REPORT_SECTIONS

    for section in ALL_REPORT_SECTIONS:
        for rq in section.retrieval_queries:
            result = retriever.retrieve(
                query=rq.query,
                document_id=_DOC_ID,
                top_k=section.top_k,
                section_filter=rq.section_filter,
            )
            assert len(result.chunks) > 0, (
                f"Section {section.section_number} ({section.title}): "
                f"query '{rq.query}' with section_filter={rq.section_filter!r} "
                f"returned no results"
            )


# ---------------------------------------------------------------------------
# Section filter correctness: filtered queries only return matching types
# ---------------------------------------------------------------------------


def test_section_filter_restricts_results() -> None:
    """When a section_filter is applied, only chunks of that type are returned."""
    retriever = _build_test_retriever()

    # Query with facility_terms filter
    result = retriever.retrieve(
        query="revolving credit commitment term loan maturity",
        document_id=_DOC_ID,
        top_k=20,
        section_filter="facility_terms",
    )

    for hc in result.chunks:
        # Definition chunks may be promoted; allow those
        if hc.source == "definition":
            continue
        assert hc.chunk.section_type == "facility_terms", (
            f"Expected section_type='facility_terms' but got "
            f"'{hc.chunk.section_type}' for chunk '{hc.chunk.chunk_id}' "
            f"(source={hc.source})"
        )


def test_negative_covenants_filter_restricts_results() -> None:
    """Negative covenant filter should only return negative covenant chunks."""
    retriever = _build_test_retriever()

    result = retriever.retrieve(
        query="indebtedness limitation permitted debt basket",
        document_id=_DOC_ID,
        top_k=20,
        section_filter="negative_covenants",
    )

    for hc in result.chunks:
        if hc.source == "definition":
            continue
        assert hc.chunk.section_type == "negative_covenants", (
            f"Expected section_type='negative_covenants' but got "
            f"'{hc.chunk.section_type}' for chunk '{hc.chunk.chunk_id}'"
        )


# ---------------------------------------------------------------------------
# No fixture overlap: chunks should not contaminate wrong sections
# ---------------------------------------------------------------------------


def test_financial_covenant_not_in_negative_covenant_results() -> None:
    """Financial covenant chunks should not appear in negative covenant filtered results."""
    retriever = _build_test_retriever()

    result = retriever.retrieve(
        query="leverage ratio covenant",
        document_id=_DOC_ID,
        top_k=20,
        section_filter="negative_covenants",
    )

    for hc in result.chunks:
        if hc.source == "definition":
            continue
        assert hc.chunk.chunk_id != "financial_covenants", (
            "Financial covenant chunk should not appear when filtering to "
            "negative_covenants only"
        )
