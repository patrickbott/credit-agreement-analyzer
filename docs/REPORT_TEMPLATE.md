# Report Template Specification

This document defines the structure, retrieval strategy, and extraction prompts for each section of the automated credit agreement report.

---

## General Report Instructions

- Maximum ~10 pages when rendered
- Each section should be concise but complete — extract specific data points, don't paraphrase the agreement
- If information for a section is not found, clearly state: "NOT IDENTIFIED — This information was not found in the analyzed sections of the agreement."
- All dollar amounts should include exact figures as stated in the agreement
- All ratio tests should include exact thresholds
- Cite the relevant Article/Section number for every data point

---

## Section 1: Transaction Overview

### Retrieval Strategy
- Query: "borrower sponsor purpose closing date credit agreement"
- Section filter: `facility_terms`, `conditions`, first few pages (preamble)
- Additional query: "recitals whereas borrower"

### Extraction Prompt
```
Extract the following from the provided text. If a field is not found, write "NOT FOUND".

- Borrower (legal entity name):
- Parent / Holdings entity (if any):
- Sponsor / Private Equity owner (if mentioned):
- Purpose of the credit facilities:
- Closing date / Effective date:
- Governing law / Jurisdiction:

Cite the specific section or page where each item is found.
```

### Notes
- Borrower info is usually in the preamble (first 1-2 pages) or recitals
- Sponsor may not be named explicitly — might need to infer from defined terms like "Sponsor"

---

## Section 2: Facility Summary

### Retrieval Strategy
- Query 1: "revolving credit facility term loan commitment amount maturity"
- Query 2: "amortization repayment schedule mandatory prepayment"
- Query 3: "delayed draw incremental facility accordion"
- Section filter: `facility_terms`

### Extraction Prompt
```
Extract details for EACH credit facility described in the agreement. For each facility, provide:

- Facility type (e.g., Revolving Credit Facility, Term Loan A, Term Loan B, Delayed Draw):
- Commitment amount / Principal amount:
- Maturity date:
- Amortization schedule (if applicable — quarterly amounts or annual percentages):
- Mandatory prepayment provisions (excess cash flow sweep percentage and step-downs, asset sale proceeds, etc.):
- Voluntary prepayment terms (any call protection, prepayment premiums, soft call periods):
- Incremental facility capacity (if described here):

If multiple facilities exist, list each one separately.
If a field is not found, write "NOT FOUND".
Cite Article/Section numbers for each data point.
```

---

## Section 3: Pricing

### Retrieval Strategy
- Query 1: "applicable rate applicable margin SOFR spread ABR spread"
- Query 2: "pricing grid leverage step-down"
- Query 3: "commitment fee letter of credit fee ticking fee"
- Query 4: "original issue discount OID floor SOFR floor"
- Section filter: `facility_terms`
- Special: retrieve any tables detected in the facility terms sections

### Extraction Prompt
```
Extract the complete pricing terms for each facility:

For each facility:
- Applicable SOFR / Term SOFR spread:
- Applicable ABR / Base Rate spread:
- SOFR floor (if any):
- Commitment fee (for revolvers):
- Letter of credit fee:
- Ticking fee (for delayed draw, if applicable):
- OID / Upfront fee:

If there is a leverage-based pricing grid with step-downs:
- List each pricing level as a row: [Leverage Ratio Range] → [SOFR Spread] / [ABR Spread] / [Commitment Fee]
- Note which leverage ratio definition is used (e.g., First Lien Net Leverage Ratio, Total Net Leverage Ratio)

If pricing is fixed (no step-downs), state "Fixed pricing — no leverage-based adjustments."
Cite Article/Section numbers. If a table is provided, reference it directly.
```

---

## Section 4: Bank Group

### Retrieval Strategy
- Query 1: "administrative agent collateral agent arranger bookrunner"
- Query 2: "lender commitment schedule"
- Section filter: None (this info can be in preamble, signature pages, or schedules)
- Additional: search for chunks tagged from schedules/exhibits

### Extraction Prompt
```
Extract the bank group and agent roles:

- Administrative Agent:
- Collateral Agent (if different):
- Lead Arrangers / Bookrunners:
- Syndication Agent(s) (if any):
- Documentation Agent(s) (if any):

If a commitment schedule is available listing individual lender commitments, summarize:
- Total number of lenders
- Top 3-5 lenders by commitment size (name and amount)

If individual commitments are not available, note "Individual lender commitments not identified."
Cite relevant sections, schedules, or pages.
```

---

## Section 5: Financial Covenants

### Retrieval Strategy
- Query 1: "financial covenant maintenance covenant leverage ratio"
- Query 2: "interest coverage ratio fixed charge coverage ratio"
- Query 3: "maximum total leverage first lien leverage senior secured"
- Query 4: "equity cure right financial covenant testing"
- Section filter: `financial_covenants`

### Extraction Prompt
```
Extract ALL financial maintenance covenants. For each covenant:

- Covenant type (e.g., Maximum Total Net Leverage Ratio, Minimum Interest Coverage Ratio, Maximum First Lien Net Leverage Ratio):
- Test level(s) — list ALL step-downs/step-ups by period:
  Format: [Period/Quarter] → [Test Level]
- Testing frequency (quarterly, annual):
- Which facilities are subject to this covenant (e.g., revolver-only, all facilities):
- Any springing/triggering conditions (e.g., covenant only tested when revolver utilization exceeds X%):
- Definition of the key ratio components (briefly — e.g., how is EBITDA defined for covenant purposes):

Equity Cure Rights (if any):
- Number of cure rights permitted:
- Maximum cures in consecutive quarters:
- Maximum cures over life of facility:
- Any limitations on cure amount or source:

If this is a COVENANT-LITE deal with NO financial maintenance covenants, clearly state:
"COVENANT-LITE: No financial maintenance covenants identified. [Specify if there are incurrence-based financial tests only.]"

Cite Article/Section numbers for every data point.
```

---

## Section 6: Negative Covenants — Debt Capacity

### Retrieval Strategy
- Query 1: "indebtedness limitation on indebtedness incurrence"
- Query 2: "incremental term loan incremental revolving facility incremental equivalent debt"
- Query 3: "ratio debt incurrence test permitted indebtedness"
- Query 4: "general debt basket fixed dollar amount"
- Query 5: "credit agreement refinancing indebtedness"
- Section filter: `negative_covenants`
- Also retrieve relevant definitions: "Incremental Cap Amount", "Incremental Equivalent Debt", "Permitted Indebtedness"

### Extraction Prompt
```
This section is critical. Extract the COMPLETE debt capacity framework, covering every way the Borrower can incur additional debt.

INCREMENTAL FACILITIES:
- Incremental term loan / revolver capacity:
  - Fixed dollar amount (if any):
  - Ratio-based capacity (what ratio test, what level must be met):
  - Is unused ratio capacity available if fixed amount is used first? (free-and-clear / fungibility):
  - MFN (Most Favored Nation) protection — spread differential cap, sunset period:
  - Maturity / weighted average life restrictions relative to existing facilities:
  - Any other conditions (e.g., no event of default, pro forma compliance):

INCREMENTAL EQUIVALENT DEBT (or similar non-bank debt capacity):
- Does the agreement permit incremental equivalent debt / permitted pari passu or junior lien debt outside the credit agreement?
- Dollar amount / ratio capacity (shared with or separate from incremental facility capacity):
- Lien priority permitted (pari passu, junior, unsecured):
- Key conditions and restrictions:

GENERAL DEBT BASKETS (from the Indebtedness negative covenant):
- General / freebie basket (fixed dollar amount):
- Ratio debt basket (what ratio, what level):
- Capital lease / purchase money debt basket:
- Acquired / assumed debt in acquisitions:
- Intercompany debt:
- Any grower mechanism (e.g., greater of $X and Y% of Total Assets or EBITDA):
- Credit agreement refinancing debt:
- Any other material debt carve-outs with their dollar amounts or ratio tests:

For EACH basket, note:
- The dollar amount or ratio test
- Whether it is subject to a cap or grows with the business
- Any restrictions on lien priority or maturity
- The specific Section/subsection reference (e.g., Section 7.03(b)(iv))

If debt baskets reference defined terms for their amounts (e.g., "the greater of $X and Y% of Consolidated Total Assets"), extract the full formula.
```

### Notes
This is the most important section for the user's workflow (advising on debt capacity). It may require the most retrieval queries and the longest LLM output. Consider splitting into sub-sections if output exceeds model's comfortable generation length.

---

## Section 7: Negative Covenants — Liens, Restricted Payments, Investments, Asset Sales

### Retrieval Strategy
For each sub-topic, run separate retrieval:

**Liens:**
- Query: "liens limitation on liens permitted liens"
- Section filter: `negative_covenants`

**Restricted Payments:**
- Query: "restricted payments dividends distributions repurchases"
- Section filter: `negative_covenants`
- Also retrieve definitions: "Available Amount", "builder basket", "Cumulative Credit"

**Investments:**
- Query: "investments permitted investments"
- Section filter: `negative_covenants`

**Asset Sales:**
- Query: "asset sales dispositions mandatory prepayment reinvestment"
- Section filter: `negative_covenants`

### Extraction Prompt (Liens)
```
Extract the Liens covenant structure:

- General prohibition description (brief):
- Permitted Liens — list each material basket:
  - General / freebie lien basket (dollar amount):
  - Ratio-based lien basket (if any):
  - Capital lease / purchase money liens:
  - Any grower baskets:
  - Other material carve-outs with amounts:

For each basket, note the dollar amount or formula and the Section reference.
```

### Extraction Prompt (Restricted Payments)
```
Extract the Restricted Payments covenant structure:

- General prohibition description (brief):
- Key RP baskets:
  - General / freebie RP basket (dollar amount):
  - Builder basket / Available Amount basket:
    - Starter amount:
    - Builder components (e.g., 50% of Consolidated Net Income, equity contribution credits):
    - Conditions for usage (ratio test level, no default):
  - Ratio-based RP basket (if separate from builder):
  - Tax distributions:
  - Management/sponsor fees:
  - Any other material RP carve-outs with amounts:

For each basket, note the dollar amount or formula, any conditions, and the Section reference.
```

### Extraction Prompt (Investments)
```
Extract the Investments covenant structure:

- General prohibition description (brief):
- Key investment baskets:
  - General / freebie basket (dollar amount):
  - Ratio-based investment basket:
  - Investments in unrestricted subsidiaries:
  - Investments funded with Available Amount / builder basket:
  - Any grower baskets:
  - Other material carve-outs with amounts:

For each basket, note the dollar amount or formula and the Section reference.
```

### Extraction Prompt (Asset Sales)
```
Extract the Asset Sales / Dispositions covenant:

- General prohibition description (brief):
- Permitted dispositions thresholds:
  - De minimis / freebie threshold:
  - Annual or aggregate cap:
  - Fair market value requirements:
- Mandatory prepayment from asset sale proceeds:
  - Percentage of Net Cash Proceeds required to prepay:
  - Step-downs based on leverage (if any):
  - Reinvestment rights — period allowed, conditions:
- Section references for each item.
```

---

## Section 8: Affirmative Covenants

### Retrieval Strategy
- Query 1: "financial statements reporting requirements annual quarterly"
- Query 2: "compliance certificate officer's certificate"
- Query 3: "insurance maintenance of properties"
- Section filter: `affirmative_covenants`

### Extraction Prompt
```
Summarize the key affirmative covenants:

REPORTING REQUIREMENTS:
- Annual financial statements — delivery deadline (days after fiscal year end), audit requirement:
- Quarterly financial statements — delivery deadline (days after fiscal quarter end):
- Compliance certificates — delivery timing, what they must certify:
- Any other material reporting (budgets, projections, collateral reports):

OTHER KEY AFFIRMATIVE COVENANTS (briefly note any notable provisions):
- Maintenance of insurance:
- Maintenance of properties:
- Payment of taxes:
- Collateral-related obligations (if material):
- Additional guarantor / collateral requirements (e.g., after-acquired property):
- Any notable or unusual affirmative covenants:

Cite Section references. Keep this section concise — focus on the most relevant items.
```

---

## Section 9: Events of Default

### Retrieval Strategy
- Query: "events of default cross-default cross-acceleration"
- Section filter: `events_of_default`

### Extraction Prompt
```
Summarize the Events of Default provisions:

List each Event of Default with:
- Trigger description (brief):
- Cure period (if any — number of days):
- Whether it's a "springing" or automatic event of default:

Key items to capture:
- Payment default (cure period):
- Financial covenant default (cure period, relationship to equity cure if applicable):
- Cross-default / cross-acceleration (threshold amount):
- Judgment default (threshold amount):
- Change of control (key trigger conditions):
- ERISA-related defaults (threshold):
- Material misrepresentation:
- Bankruptcy / insolvency (voluntary vs. involuntary, cure period for involuntary):

Cite Section references for each event of default.
```

---

## Section 10: Other Notable Provisions

### Retrieval Strategy
- Query 1: "AHYDO savings clause catch-up payment"
- Query 2: "yank-a-bank replacement lender"
- Query 3: "most favored nation MFN sunset"
- Query 4: "pro rata sharing assignment participation"
- Query 5: "amendment waiver required lenders"
- Section filter: None (these can be scattered throughout)

### Extraction Prompt
```
Extract any notable or market-relevant provisions. Only include items that are FOUND in the agreement — do not speculate. For each item found, provide a brief description and Section reference.

Look for:
- AHYDO savings clause:
- Yank-a-bank / replacement lender provisions:
- MFN (Most Favored Nation) — already covered in debt section but note sunset period here if not above:
- Amendment / waiver thresholds (what percentage of lenders required for various amendments):
- Defaulting lender provisions:
- Bail-in provisions:
- "Serta" / "Chewy" style provisions or anti-Serta protections:
- SaaS / recurring revenue add-backs to EBITDA (note uncapped vs. capped):
- Unrestricted subsidiary designation capacity:
- Applicable premium / make-whole provisions:
- Any other unusual or notable provisions:

For items NOT found, simply omit them — do not list "NOT FOUND" for optional items in this section.
```

---

## Assembly Instructions

1. Generate each section sequentially (Sections 1-10)
2. For Section 6 (Debt Capacity) and Section 7 (Other Negative Covenants), consider splitting the LLM call into sub-sections if the prompt + context exceeds comfortable context window size
3. Assemble all sections into a single markdown document with:
   - Title: "Credit Agreement Analysis: [Borrower Name]"
   - Date generated
   - Disclaimer: "This report is auto-generated and should be verified against the source document."
4. Each section separated by `---` horizontal rule
5. Confidence badges rendered as bold text: **[HIGH CONFIDENCE]**, **[MEDIUM CONFIDENCE]**, **[LOW CONFIDENCE]**
6. Sections where information was not found rendered with clear notice: *"NOT IDENTIFIED — This information was not found in the analyzed sections of the agreement. This may indicate a covenant-lite structure or non-standard document organization. Please verify manually."*
