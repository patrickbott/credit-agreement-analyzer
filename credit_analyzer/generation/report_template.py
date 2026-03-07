"""Report section definitions, retrieval strategies, and extraction prompts.

Encodes the report structure as typed Python
objects.  Each ``ReportSectionTemplate`` defines:
- retrieval queries (multiple per section for comprehensive coverage),
- section_type filters for targeted retrieval,
- the extraction prompt sent to the LLM, and
- optional flags for special handling (e.g. sub-section splitting).

Prompts are tuned for Claude Sonnet: structured output with explicit
field labels, strict citation requirements, and silent omission of missing data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SectionStatus = Literal["pending", "generating", "complete", "error"]


@dataclass(frozen=True)
class RetrievalQuery:
    """A single retrieval query with optional section-type filtering.

    Attributes:
        query: The search query string.
        section_filter: If set, restrict retrieval to this section_type.
    """

    query: str
    section_filter: str | None = None


@dataclass(frozen=True)
class ReportSectionTemplate:
    """Template for one section of the generated report.

    Attributes:
        section_number: Display order (1-10).
        title: Section heading in the final report.
        retrieval_queries: Queries to run for context gathering.
        extraction_prompt: The prompt sent to the LLM with retrieved context.
        top_k: Number of chunks to retrieve per query (before dedup).
        max_generation_tokens: Max tokens for the LLM response.
        include_preamble: Whether to inject the document preamble as context.
    """

    section_number: int
    title: str
    retrieval_queries: tuple[RetrievalQuery, ...]
    extraction_prompt: str
    top_k: int = 15
    max_generation_tokens: int = 1500
    include_preamble: bool = False


# ---------------------------------------------------------------------------
# Report section extraction prompt (shared preamble for all sections)
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM_PROMPT: str = """\
You are a leveraged finance analyst extracting specific data from a credit \
agreement. You must write in plain text only -- no markdown formatting \
(no **, no ##, no `, no ---, no ```). Use numbered lists (1., 2., 3.) \
or dashes (-) for structure. Write section labels in CAPS on their own line.

RULES:
1. Extract ONLY from the provided context. Never supplement with general \
knowledge, market conventions, or assumptions.
2. Cite the Section number (e.g. Section 7.06(a)) for every factual claim. \
Every dollar amount, ratio, percentage, and date must have a citation.
3. State dollar amounts, ratios, and percentages exactly as written in the \
document. Do not round or reformat.
4. STRICT OMISSION RULE: If a field or category is not in the context, \
SILENTLY SKIP IT. Do not write "NOT FOUND", "Not identified", "not \
included in the provided context", or any variation. Simply do not mention \
it. The reader will infer absence from omission. The only exception: if \
the ENTIRE extraction task has zero relevant data, write one sentence: \
"Not identified in the provided context."
5. BE CONCISE. Write like a senior IB analyst briefing a colleague -- short \
bullet points, not paragraphs. Summarize provisions in practical business \
terms. Focus on MATERIAL items: dollar-amount baskets, ratio tests, key \
conditions. Skip boilerplate, ordinary-course, and de minimis baskets \
(e.g. trade payables, statutory liens, workers comp, UCC filings). \
Aim for the shortest output that captures all material economics.

7. USE TABLES where data has a natural tabular structure (e.g. pricing \
grids, amortization schedules, covenant step-downs, basket lists with \
dollar amounts). Format tables as: header row, dash separator, data rows, \
with columns separated by " | ". Keep tables compact.

INLINE CITATIONS:
Each context excerpt is labeled [Source 1], [Source 2], etc. When you make \
a specific factual claim (dollar amounts, ratios, percentages, dates, \
covenant tests), place the corresponding source number in brackets \
immediately after the claim, e.g. [1], [2]. Reuse the same number when \
the same source supports multiple claims. Do NOT let citations make your \
response longer -- keep the same concise bullet-point style.
"""


def get_extraction_system_prompt() -> str:
    """Return the shared system prompt for all report section extractions."""
    return _EXTRACTION_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Section templates
# ---------------------------------------------------------------------------


SECTION_01_TRANSACTION_OVERVIEW = ReportSectionTemplate(
    section_number=1,
    title="Transaction Overview",
    include_preamble=True,
    top_k=10,
    max_generation_tokens=800,
    retrieval_queries=(
        RetrievalQuery("borrower sponsor purpose closing date credit agreement"),
        RetrievalQuery("recitals whereas borrower holdings"),
    ),
    extraction_prompt="""\
Extract the following fields. Skip any not in the context.

BORROWER: Legal entity name
PARENT / HOLDINGS: Entity name
SPONSOR: Private equity owner
PURPOSE: One sentence on purpose of facilities
CLOSING DATE: Date
FACILITY SIZES: Total commitment amount, split by facility if applicable

Keep each field to one line. Cite Section and page.""",
)


SECTION_02_FACILITY_AND_PRICING = ReportSectionTemplate(
    section_number=2,
    title="Facility Summary and Pricing",
    top_k=20,
    max_generation_tokens=2000,
    retrieval_queries=(
        RetrievalQuery(
            "revolving credit facility term loan commitment amount maturity",
            section_filter="facility_terms",
        ),
        RetrievalQuery(
            "amortization repayment schedule mandatory prepayment",
            section_filter="facility_terms",
        ),
        # Unfiltered: pricing info often lives in definitions ("Applicable Rate")
        # and schedules (Schedule 1.1A) rather than facility_terms sections
        RetrievalQuery(
            "Applicable Rate Applicable Margin SOFR spread ABR spread pricing grid",
        ),
        RetrievalQuery(
            "commitment fee letter of credit fee OID original issue discount floor",
            section_filter="facility_terms",
        ),
    ),
    extraction_prompt="""\
For EACH credit facility, extract structure and pricing together. Skip \
fields not in context.

FACILITY TYPE: (Revolving, Term Loan A/B, Delayed Draw, etc.)
COMMITMENT / PRINCIPAL: Dollar amount
MATURITY DATE:
SOFR SPREAD / ABR SPREAD: Initial rates
SOFR FLOOR / ABR FLOOR:
AMORTIZATION: Brief summary
MANDATORY PREPAYMENT: ECF sweep %, asset sale %, step-downs
VOLUNTARY PREPAYMENT: Call protection, soft call
COMMITMENT FEE / LC FEE / OID:

If there is a leverage-based pricing grid, list tiers concisely: \
[Leverage Range] -> [SOFR] / [ABR]. Note which leverage definition is used.

List each facility separately. Keep it concise -- bullet points, not \
paragraphs. Cite Section numbers and page numbers.

Do not include incremental facilities in this section -- those belong \
in the debt capacity section
""",
)


SECTION_03_BANK_GROUP = ReportSectionTemplate(
    section_number=3,
    title="Bank Group",
    top_k=10,
    max_generation_tokens=600,
    include_preamble=True,
    retrieval_queries=(
        RetrievalQuery("administrative agent collateral agent arranger bookrunner"),
        RetrievalQuery("lender commitment schedule syndication"),
    ),
    extraction_prompt="""\
Extract agent roles and bank group. Skip roles not in context.

ADMINISTRATIVE AGENT:
COLLATERAL AGENT: (if different from admin agent)
LEAD ARRANGERS / BOOKRUNNERS:

If lender commitments are listed, note total number of lenders and \
aggregate facility size. Keep it brief. Cite sections.""",
)


SECTION_04_FINANCIAL_COVENANTS = ReportSectionTemplate(
    section_number=4,
    title="Financial Covenants",
    top_k=18,
    max_generation_tokens=1200,
    retrieval_queries=(
        RetrievalQuery(
            "financial covenant maintenance covenant leverage ratio",
            section_filter="financial_covenants",
        ),
        RetrievalQuery(
            "interest coverage ratio fixed charge coverage ratio",
            section_filter="financial_covenants",
        ),
        RetrievalQuery(
            "equity cure right financial covenant testing",
            section_filter="financial_covenants",
        ),
        # Unfiltered: leverage/coverage ratio definitions contain test levels
        RetrievalQuery(
            "Consolidated EBITDA Total Net Leverage Ratio Fixed Charge Coverage",
        ),
    ),
    extraction_prompt="""\
Extract MAINTENANCE covenants only. Do NOT include incurrence-only tests \
(those belong in the debt capacity section).

For each maintenance covenant:
COVENANT TYPE: (e.g. Maximum Total Net Leverage, Minimum Interest Coverage)
TEST LEVELS: List step-downs/step-ups by period
TESTING: Frequency, which facilities, springing conditions

EQUITY CURE RIGHTS: If present, summarize in 2-3 bullet points (number \
of cures, limits, key conditions).

If covenant-lite, state that in one sentence.

Keep it concise. Cite Section numbers.""",
)


SECTION_05_DEBT_CAPACITY = ReportSectionTemplate(
    section_number=5,
    title="Negative Covenants -- Debt Capacity",
    top_k=20,
    max_generation_tokens=2000,
    retrieval_queries=(
        RetrievalQuery(
            "indebtedness limitation on indebtedness incurrence",
            section_filter="negative_covenants",
        ),
        RetrievalQuery(
            "incremental term loan incremental revolving incremental equivalent debt",
            section_filter="negative_covenants",
        ),
        RetrievalQuery(
            "ratio debt incurrence test permitted indebtedness",
            section_filter="negative_covenants",
        ),
        # Unfiltered: key definitions contain basket amounts and grower formulas
        RetrievalQuery(
            "Permitted Indebtedness Available Incremental Amount Fixed Incremental Amount",
        ),
    ),
    extraction_prompt="""\
Extract the debt capacity framework. ONLY include baskets with a stated \
dollar amount, ratio test, or grower formula. Skip ordinary-course, \
boilerplate, and immaterial baskets (trade payables, statutory items, \
intercompany without caps, deferred payments, swap agreements, etc.).

INCREMENTAL FACILITIES: Fixed amount, ratio capacity, MFN terms.

INCREMENTAL EQUIVALENT DEBT: If permitted, capacity and lien priority.

MATERIAL DEBT BASKETS: List only the economically significant baskets \
(general basket, ratio basket, capital leases, acquired debt, refinancing \
debt) with dollar amount or ratio test and Section reference. Use one \
bullet per basket.

Note grower mechanisms (greater of $X and Y% of metric).

Keep this section tight -- aim for one line per basket. Cite Section refs.""",
)


SECTION_06_LIENS = ReportSectionTemplate(
    section_number=6,
    title="Negative Covenants -- Liens",
    top_k=15,
    max_generation_tokens=800,
    retrieval_queries=(
        RetrievalQuery(
            "liens limitation on liens permitted liens",
            section_filter="negative_covenants",
        ),
        # Unfiltered: "Permitted Liens" definition often contains the basket list
        RetrievalQuery(
            "Permitted Liens general lien basket",
        ),
    ),
    extraction_prompt="""\
Extract the Liens covenant. Keep it short.

GENERAL PROHIBITION: One sentence.

MATERIAL PERMITTED LIENS: List ONLY baskets with a dollar amount, ratio \
test, or grower formula. Skip statutory liens, tax liens, easements, \
UCC filings, judgment liens, workers comp, and other ordinary-course items.

One bullet per basket with amount and Section reference.""",
)


SECTION_07_RESTRICTED_PAYMENTS = ReportSectionTemplate(
    section_number=7,
    title="Negative Covenants -- Restricted Payments",
    top_k=18,
    max_generation_tokens=1000,
    retrieval_queries=(
        RetrievalQuery(
            "restricted payments dividends distributions repurchases",
            section_filter="negative_covenants",
        ),
        RetrievalQuery(
            "available amount builder basket cumulative credit",
            section_filter="negative_covenants",
        ),
        # Unfiltered: "Available Amount" and "Restricted Payment" definitions
        RetrievalQuery(
            "Available Amount Cumulative Credit builder basket definition",
        ),
    ),
    extraction_prompt="""\
Extract the Restricted Payments covenant. Keep it concise.

GENERAL PROHIBITION: One sentence.

KEY RP BASKETS: List only material baskets with dollar amounts, ratio \
tests, or builder mechanics. For each, note amount/formula, key conditions, \
and Section reference. Skip intercompany, tax, and other routine baskets \
unless they have notable dollar caps. One bullet per basket.""",
)


SECTION_08_INVESTMENTS_AND_ASSET_SALES = ReportSectionTemplate(
    section_number=8,
    title="Negative Covenants -- Investments and Asset Sales",
    top_k=15,
    max_generation_tokens=1000,
    retrieval_queries=(
        RetrievalQuery(
            "investments permitted investments unrestricted subsidiary",
            section_filter="negative_covenants",
        ),
        RetrievalQuery(
            "asset sales dispositions mandatory prepayment reinvestment",
            section_filter="negative_covenants",
        ),
        # Unfiltered: "Permitted Investments" and "Permitted Acquisitions" definitions
        RetrievalQuery(
            "Permitted Investments Permitted Acquisitions asset sale definition",
        ),
    ),
    extraction_prompt="""\
Extract material items only. Skip ordinary-course and immaterial baskets.

INVESTMENTS: List only baskets with dollar amounts or ratio tests. One \
bullet per basket with amount and Section reference.

ASSET SALES: Summarize thresholds, mandatory prepayment %, leverage \
step-downs, reinvestment period. Keep it brief.

Cite Section references.""",
)


SECTION_09_EVENTS_OF_DEFAULT = ReportSectionTemplate(
    section_number=9,
    title="Events of Default and Amendments",
    top_k=15,
    max_generation_tokens=1000,
    retrieval_queries=(
        RetrievalQuery(
            "events of default cross-default acceleration",
            section_filter="events_of_default",
        ),
        RetrievalQuery(
            "change of control put option",
            section_filter="events_of_default",
        ),
        # Unfiltered: "Required Lenders" and "Change of Control" definitions
        RetrievalQuery(
            "Required Lenders amendment waiver voting threshold Change of Control",
        ),
    ),
    extraction_prompt="""\
Extract ONLY provisions actually present in the context.

EVENTS OF DEFAULT:
- Payment default (grace period)
- Covenant default (cure period)
- Cross-default threshold
- Change of control definition and trigger
- Bankruptcy / insolvency
- Judgment default threshold

AMENDMENT PROVISIONS:
- Required Lenders definition (% threshold)
- Unanimous lender consent items
- Supermajority items if any

Keep each item to 1-2 bullet points. Cite Section references.""",
)


SECTION_10_OTHER_PROVISIONS = ReportSectionTemplate(
    section_number=10,
    title="Other Notable Provisions",
    top_k=12,
    max_generation_tokens=800,
    retrieval_queries=(
        RetrievalQuery("affirmative covenants financial statements reporting"),
        RetrievalQuery("EBITDA add-back adjustment definition consolidated"),
        RetrievalQuery("yank-a-bank defaulting lender replacement"),
    ),
    extraction_prompt="""\
Extract ONLY provisions actually present in the context. Skip entire \
categories if not found.

Possible items to look for (include only if found):
- Reporting requirements (delivery deadlines, compliance certificates)
- EBITDA add-back caps (cost savings, synergies, run-rate)
- Yank-a-bank provisions
- Defaulting lender provisions
- Any other notable or unusual provisions

Keep each item to 1-2 bullet points. Cite Section references.""",
)


# ---------------------------------------------------------------------------
# Ordered list of all sections
# ---------------------------------------------------------------------------

ALL_REPORT_SECTIONS: tuple[ReportSectionTemplate, ...] = (
    SECTION_01_TRANSACTION_OVERVIEW,
    SECTION_02_FACILITY_AND_PRICING,
    SECTION_03_BANK_GROUP,
    SECTION_04_FINANCIAL_COVENANTS,
    SECTION_05_DEBT_CAPACITY,
    SECTION_06_LIENS,
    SECTION_07_RESTRICTED_PAYMENTS,
    SECTION_08_INVESTMENTS_AND_ASSET_SALES,
    SECTION_09_EVENTS_OF_DEFAULT,
    SECTION_10_OTHER_PROVISIONS,
)
