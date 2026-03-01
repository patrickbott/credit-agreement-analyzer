"""Report section definitions, retrieval strategies, and extraction prompts.

Encodes the structure from ``docs/REPORT_TEMPLATE.md`` as typed Python
objects.  Each ``ReportSectionTemplate`` defines:
- retrieval queries (multiple per section for comprehensive coverage),
- section_type filters for targeted retrieval,
- the extraction prompt sent to the LLM, and
- optional flags for special handling (e.g. sub-section splitting).

Prompts are tuned for Claude Sonnet: structured output with explicit
field labels, strict citation requirements, and clear NOT FOUND markers.
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
4. If a field is not in the context, write "NOT FOUND" for that field. Do \
not guess or infer.
5. Write like a senior IB analyst briefing a colleague. Concise, precise, \
no legal boilerplate. Summarize provisions in practical business terms, \
not verbatim legal language.

At the end of your response, on separate lines:
Confidence: HIGH | MEDIUM | LOW
Sources: Section X.XX (pp. XX-XX), Section Y.YY (pp. YY-YY)
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
Extract the following fields. Write NOT FOUND for any field absent from \
the context.

BORROWER: Legal entity name
PARENT / HOLDINGS: Entity name (if any)
SPONSOR: Private equity owner (if named or defined)
PURPOSE: Purpose of the credit facilities
CLOSING DATE: Effective date of the agreement
GOVERNING LAW: Jurisdiction

Cite the Section or page for each field.""",
)


SECTION_02_FACILITY_SUMMARY = ReportSectionTemplate(
    section_number=2,
    title="Facility Summary",
    top_k=15,
    max_generation_tokens=1500,
    retrieval_queries=(
        RetrievalQuery(
            "revolving credit facility term loan commitment amount maturity",
            section_filter="facility_terms",
        ),
        RetrievalQuery(
            "amortization repayment schedule mandatory prepayment",
            section_filter="facility_terms",
        ),
        RetrievalQuery(
            "delayed draw incremental facility accordion",
            section_filter="facility_terms",
        ),
    ),
    extraction_prompt="""\
For EACH credit facility in the agreement, extract:

FACILITY TYPE: (Revolving, Term Loan A, Term Loan B, Delayed Draw, etc.)
COMMITMENT / PRINCIPAL: Dollar amount
MATURITY DATE:
AMORTIZATION: Quarterly amounts or annual percentages (if applicable)
MANDATORY PREPAYMENT: Excess cash flow sweep %, asset sale proceeds %, \
step-downs by leverage level
VOLUNTARY PREPAYMENT: Call protection, prepayment premiums, soft call periods
INCREMENTAL CAPACITY: (if described in facility terms)

List each facility separately. Cite Section numbers for every data point. \
Write NOT FOUND for any field absent from the context.""",
)


SECTION_03_PRICING = ReportSectionTemplate(
    section_number=3,
    title="Pricing",
    top_k=15,
    max_generation_tokens=1500,
    retrieval_queries=(
        RetrievalQuery(
            "applicable rate applicable margin SOFR spread ABR spread",
            section_filter="facility_terms",
        ),
        RetrievalQuery(
            "pricing grid leverage step-down",
            section_filter="facility_terms",
        ),
        RetrievalQuery(
            "commitment fee letter of credit fee ticking fee OID floor",
            section_filter="facility_terms",
        ),
    ),
    extraction_prompt="""\
For each facility, extract the complete pricing terms:

SOFR / TERM SOFR SPREAD:
ABR / BASE RATE SPREAD:
SOFR FLOOR:
COMMITMENT FEE: (for revolvers)
LC FEE:
TICKING FEE: (for delayed draw, if applicable)
OID / UPFRONT FEE:

If there is a leverage-based pricing grid:
- List each tier: [Leverage Range] -> [SOFR Spread] / [ABR Spread] / \
[Commitment Fee]
- Note which leverage definition is used (e.g. First Lien Net Leverage Ratio)

If pricing is fixed, state "Fixed pricing -- no leverage-based grid."

Cite Section numbers. Write NOT FOUND for absent fields.""",
)


SECTION_04_BANK_GROUP = ReportSectionTemplate(
    section_number=4,
    title="Bank Group",
    top_k=10,
    max_generation_tokens=800,
    include_preamble=True,
    retrieval_queries=(
        RetrievalQuery("administrative agent collateral agent arranger bookrunner"),
        RetrievalQuery("lender commitment schedule syndication"),
    ),
    extraction_prompt="""\
Extract the bank group and agent roles:

ADMINISTRATIVE AGENT:
COLLATERAL AGENT: (if different)
LEAD ARRANGERS / BOOKRUNNERS:
SYNDICATION AGENT(S):
DOCUMENTATION AGENT(S):

If a commitment schedule lists individual lender commitments, summarize:
- Total number of lenders
- Top 3-5 lenders by commitment size (name and amount)

If individual commitments are not available, write "Individual lender \
commitments not identified."

Cite relevant sections, schedules, or pages.""",
)


SECTION_05_FINANCIAL_COVENANTS = ReportSectionTemplate(
    section_number=5,
    title="Financial Covenants",
    top_k=18,
    max_generation_tokens=2000,
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
        RetrievalQuery(
            "maximum total leverage first lien leverage senior secured",
            section_filter="financial_covenants",
        ),
    ),
    extraction_prompt="""\
Extract ALL financial maintenance covenants. For each:

COVENANT TYPE: (e.g. Maximum Total Net Leverage, Minimum Interest Coverage)
TEST LEVELS: List ALL step-downs/step-ups by period:
  [Period/Quarter] -> [Test Level]
TESTING FREQUENCY: (quarterly, annual)
FACILITIES TESTED: (revolver-only, all facilities)
SPRINGING CONDITIONS: (e.g. only tested when revolver > X% drawn)
RATIO DEFINITION: Brief note on how EBITDA is defined for covenant purposes

EQUITY CURE RIGHTS (if any):
- Number of cures permitted
- Max consecutive quarters
- Max over life of facility
- Limitations on cure amount or source

If COVENANT-LITE with no financial maintenance covenants, state:
"COVENANT-LITE: No financial maintenance covenants. [Note if incurrence \
tests exist.]"

Cite Section numbers for every data point.""",
)


SECTION_06_DEBT_CAPACITY = ReportSectionTemplate(
    section_number=6,
    title="Negative Covenants -- Debt Capacity",
    top_k=20,
    max_generation_tokens=2500,
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
        RetrievalQuery(
            "general debt basket fixed dollar amount",
            section_filter="negative_covenants",
        ),
        RetrievalQuery(
            "credit agreement refinancing indebtedness",
            section_filter="negative_covenants",
        ),
    ),
    extraction_prompt="""\
This is the most important section. Extract the COMPLETE debt capacity \
framework.

INCREMENTAL FACILITIES:
- Fixed dollar amount:
- Ratio-based capacity (which ratio, what level):
- Free-and-clear / fungibility (unused ratio capacity if fixed used first):
- MFN protection (spread cap, sunset period):
- Maturity / WAL restrictions vs existing:
- Other conditions (no default, pro forma compliance):

INCREMENTAL EQUIVALENT DEBT:
- Permitted? (yes/no)
- Dollar / ratio capacity (shared with or separate from incremental):
- Lien priority permitted (pari passu, junior, unsecured):
- Key conditions:

GENERAL DEBT BASKETS (from Indebtedness negative covenant):
- General / freebie basket ($):
- Ratio debt basket (which ratio, what level):
- Capital lease / purchase money:
- Acquired / assumed debt in acquisitions:
- Intercompany debt:
- Grower mechanism (greater of $X and Y% of Total Assets/EBITDA):
- Credit agreement refinancing debt:
- Other material carve-outs with amounts:

For EACH basket note:
1. Dollar amount or ratio test
2. Whether capped or grows with the business
3. Lien priority or maturity restrictions
4. Section/subsection reference (e.g. Section 7.03(b)(iv))

If baskets use defined terms for amounts, extract the full formula.""",
)


SECTION_07_LIENS = ReportSectionTemplate(
    section_number=7,
    title="Negative Covenants -- Liens",
    top_k=15,
    max_generation_tokens=1200,
    retrieval_queries=(
        RetrievalQuery(
            "liens limitation on liens permitted liens",
            section_filter="negative_covenants",
        ),
    ),
    extraction_prompt="""\
Extract the Liens covenant structure:

GENERAL PROHIBITION: (one sentence summary)

PERMITTED LIENS -- list each material basket:
- General / freebie lien basket ($):
- Ratio-based lien basket (if any):
- Capital lease / purchase money liens:
- Grower baskets:
- Other material carve-outs with amounts:

For each basket, note the dollar amount or formula and the Section reference.""",
)


SECTION_08_RESTRICTED_PAYMENTS = ReportSectionTemplate(
    section_number=8,
    title="Negative Covenants -- Restricted Payments",
    top_k=18,
    max_generation_tokens=1800,
    retrieval_queries=(
        RetrievalQuery(
            "restricted payments dividends distributions repurchases",
            section_filter="negative_covenants",
        ),
        RetrievalQuery(
            "available amount builder basket cumulative credit",
            section_filter="negative_covenants",
        ),
    ),
    extraction_prompt="""\
Extract the Restricted Payments covenant:

GENERAL PROHIBITION: (one sentence summary)

KEY RP BASKETS:
- General / freebie basket ($):
- Builder basket / Available Amount:
  - Starter amount:
  - Builder components (e.g. 50% CNI, equity contribution credits):
  - Conditions for usage (ratio test, no default):
- Ratio-based RP basket (if separate from builder):
- Tax distributions:
- Management / sponsor fees:
- Other material RP carve-outs with amounts:

For each basket, note dollar amount/formula, conditions, and Section ref.""",
)


SECTION_09_INVESTMENTS_AND_ASSET_SALES = ReportSectionTemplate(
    section_number=9,
    title="Negative Covenants -- Investments and Asset Sales",
    top_k=15,
    max_generation_tokens=1500,
    retrieval_queries=(
        RetrievalQuery(
            "investments permitted investments unrestricted subsidiary",
            section_filter="negative_covenants",
        ),
        RetrievalQuery(
            "asset sales dispositions mandatory prepayment reinvestment",
            section_filter="negative_covenants",
        ),
    ),
    extraction_prompt="""\
INVESTMENTS:
- General / freebie basket ($):
- Ratio-based investment basket:
- Investments in unrestricted subsidiaries:
- Investments funded with Available Amount / builder:
- Grower baskets:
- Other material carve-outs with amounts:

ASSET SALES / DISPOSITIONS:
- De minimis / freebie threshold:
- Annual or aggregate cap:
- Fair market value requirements:
- Mandatory prepayment from net proceeds:
  - Percentage of Net Cash Proceeds:
  - Step-downs by leverage:
  - Reinvestment period and conditions:

Cite Section references for each item.""",
)


SECTION_10_OTHER_PROVISIONS = ReportSectionTemplate(
    section_number=10,
    title="Other Notable Provisions",
    top_k=12,
    max_generation_tokens=1200,
    retrieval_queries=(
        RetrievalQuery("affirmative covenants financial statements reporting"),
        RetrievalQuery("events of default cross-default change of control"),
        RetrievalQuery("amendment waiver required lenders AHYDO yank-a-bank"),
    ),
    extraction_prompt="""\
Extract any of the following provisions that are FOUND. Omit items not \
in the context -- do not write NOT FOUND for optional items here.

REPORTING REQUIREMENTS:
- Annual financial statements (delivery deadline, audit requirement):
- Quarterly financial statements (delivery deadline):
- Compliance certificate timing:

KEY EVENTS OF DEFAULT:
- Payment default (cure period):
- Financial covenant default (cure period):
- Cross-default threshold:
- Change of control triggers:
- Bankruptcy (voluntary vs involuntary, cure period):

OTHER NOTABLE ITEMS (only if found):
- AHYDO savings clause
- Yank-a-bank provisions
- Amendment thresholds (% of lenders for various types)
- Defaulting lender provisions
- Anti-Serta protections
- EBITDA add-backs (uncapped vs capped)
- Unrestricted subsidiary designation capacity
- Make-whole / applicable premium

Cite Section references for each item found.""",
)


# ---------------------------------------------------------------------------
# Ordered list of all sections
# ---------------------------------------------------------------------------

ALL_REPORT_SECTIONS: tuple[ReportSectionTemplate, ...] = (
    SECTION_01_TRANSACTION_OVERVIEW,
    SECTION_02_FACILITY_SUMMARY,
    SECTION_03_PRICING,
    SECTION_04_BANK_GROUP,
    SECTION_05_FINANCIAL_COVENANTS,
    SECTION_06_DEBT_CAPACITY,
    SECTION_07_LIENS,
    SECTION_08_RESTRICTED_PAYMENTS,
    SECTION_09_INVESTMENTS_AND_ASSET_SALES,
    SECTION_10_OTHER_PROVISIONS,
)
