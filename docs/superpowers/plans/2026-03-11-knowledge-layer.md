# Leveraged Finance Knowledge Layer — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a three-layer intelligence system that lets the credit analyzer handle complex leveraged finance queries — named provisions (J.Crew, Serta, Chewy), synonym/jargon translation (freebie basket = free and clear), multi-step analytical questions, and cross-document reasoning — by combining a curated domain concept registry with conditional LLM-powered query decomposition.

**Architecture:** Layer 1 (deterministic concept registry + synonym expansion) runs on every query at zero LLM cost. Layer 2 (retrieval quality gate) checks whether initial results are sufficient. Layer 3 (LLM query decomposer) fires only when the gate detects insufficient results, decomposing complex queries into targeted sub-queries. The UI shows real-time status indicators so users understand what's happening during multi-step analysis.

**Tech Stack:** Python 3.11+, YAML (concept/synonym data), existing HybridRetriever + RRF pipeline, Anthropic Claude API (for Layer 3 decomposition), Streamlit (UI status), pytest (tests).

---

## Chunk 1: Domain Knowledge Data + Registry Module

### Task 1: Create the Leveraged Finance Concept Registry (Data)

**Files:**
- Create: `credit_analyzer/knowledge/__init__.py`
- Create: `credit_analyzer/knowledge/concepts.yaml`
- Create: `credit_analyzer/knowledge/synonyms.yaml`

The concept registry is a YAML file mapping leveraged finance concepts to their aliases (trigger phrases users might type), search terms (what to actually retrieve from the document), and a short description (injected into the LLM prompt for context).

The synonym dictionary is a separate YAML file mapping common jargon variations to canonical terms, extending the existing `_TERM_ALIASES` dict in `query_expansion.py` and `LEGAL_SYNONYMS` in `query_helpers.py`.

- [ ] **Step 1: Create the knowledge package**

```python
# credit_analyzer/knowledge/__init__.py
"""Leveraged finance domain knowledge: concept registry and synonym maps."""
```

- [ ] **Step 2: Create concepts.yaml**

```yaml
# credit_analyzer/knowledge/concepts.yaml
#
# Leveraged Finance Concept Registry
#
# Each concept maps a well-known deal/market term to:
#   aliases:      Trigger phrases users might type (matched case-insensitively)
#   search_terms: Phrases to search for in the actual document text
#   description:  Brief explanation injected into LLM context when concept is matched
#   sections:     Optional list of section_types most likely to contain this concept

concepts:

  j_crew_provision:
    aliases:
      - "j.crew"
      - "j crew"
      - "jcrew"
      - "j-crew"
      - "trap door"
      - "trap-door"
      - "trapdoor"
      - "ip stripping"
      - "ip transfer provision"
    search_terms:
      - "intellectual property"
      - "unrestricted subsidiary"
      - "transfer"
      - "designation"
      - "material assets"
      - "excluded assets"
    description: >
      J.Crew provisions (also called trap-door provisions) allow a borrower to
      transfer valuable intellectual property or other material assets to an
      unrestricted subsidiary, moving them beyond the reach of secured lenders.
      Named after the 2017 J.Crew transaction where the borrower transferred its
      IP to an unrestricted subsidiary and used it as collateral for new financing.
    sections:
      - negative_covenants
      - definitions

  serta_provision:
    aliases:
      - "serta"
      - "uptier"
      - "up-tier"
      - "priming"
      - "anti-serta"
      - "serta protection"
      - "uptier protection"
    search_terms:
      - "uptier"
      - "priming"
      - "subordinat"
      - "open market purchase"
      - "lien priority"
      - "junior lien"
      - "pari passu"
      - "sacred right"
    description: >
      Serta provisions relate to uptier/priming transactions where a borrower
      issues new super-priority debt that primes existing lenders. Named after the
      Serta Simmons 2020 transaction. Anti-Serta protections are lender
      safeguards requiring pro rata treatment or sacred-right protections against
      subordination without individual lender consent.
    sections:
      - negative_covenants
      - miscellaneous

  chewy_provision:
    aliases:
      - "chewy"
      - "petsmart"
      - "dividend recapture"
      - "unrestricted subsidiary ipo"
    search_terms:
      - "unrestricted subsidiary"
      - "initial public offering"
      - "equity issuance"
      - "redesignation"
      - "restricted payment"
      - "dividend"
      - "distribution"
    description: >
      Chewy provisions allow a borrower to designate a subsidiary as
      unrestricted, IPO that subsidiary, and then capture the IPO proceeds.
      Named after the PetSmart/Chewy transaction where the borrower IPO'd
      Chewy as an unrestricted subsidiary. Protections may require redesignation
      tests or restrict proceeds from unrestricted subsidiary equity issuances.
    sections:
      - negative_covenants
      - definitions

  freebie_basket:
    aliases:
      - "freebie"
      - "free and clear"
      - "free-and-clear"
      - "gratis basket"
      - "no-proceeds basket"
      - "freebie incremental"
    search_terms:
      - "free and clear"
      - "without compliance"
      - "without satisfying"
      - "without giving effect"
      - "incremental"
      - "Fixed Incremental Amount"
    description: >
      A freebie basket (or free-and-clear basket) allows the borrower to incur
      incremental debt up to a fixed dollar amount without needing to satisfy any
      leverage ratio test. The amount is available regardless of the borrower's
      financial condition.
    sections:
      - negative_covenants
      - definitions

  mfn_provision:
    aliases:
      - "mfn"
      - "most favored nation"
      - "most-favored-nation"
      - "mfn sunset"
      - "yield protection"
      - "mfn protection"
    search_terms:
      - "most favored nation"
      - "yield protection"
      - "margin ratchet"
      - "incremental"
      - "spread"
      - "interest rate protection"
    description: >
      Most Favored Nation (MFN) provisions protect existing lenders by requiring
      that if incremental term loans are issued at a higher yield, the margin on
      existing term loans is increased to within a specified threshold (typically
      50 bps). MFN sunsets specify when this protection expires (commonly 6-18
      months after closing).
    sections:
      - facility_terms
      - negative_covenants

  ahydo:
    aliases:
      - "ahydo"
      - "applicable high yield discount obligation"
      - "oid limitation"
    search_terms:
      - "applicable high yield discount obligation"
      - "AHYDO"
      - "original issue discount"
      - "OID"
      - "yield"
    description: >
      AHYDO (Applicable High Yield Discount Obligation) refers to IRS rules
      limiting the amount of original issue discount (OID) on high yield debt.
      Credit agreements often include AHYDO savings clauses that allow the
      borrower to make mandatory redemptions to avoid AHYDO classification.
    sections:
      - facility_terms
      - definitions

  builder_basket:
    aliases:
      - "builder basket"
      - "builder"
      - "cumulative credit"
      - "available amount"
      - "grower basket"
      - "growing basket"
      - "starter amount"
    search_terms:
      - "Available Amount"
      - "Cumulative Credit"
      - "builder"
      - "retained excess cash flow"
      - "50%"
      - "Consolidated Net Income"
    description: >
      A builder basket (or Available Amount / Cumulative Credit) allows the
      borrower to accumulate capacity for restricted payments, investments, and
      debt prepayments based on retained earnings, typically starting from a
      fixed amount and growing by 50% of Consolidated Net Income and other
      specified credits. Grower baskets use a formula of the greater of a
      fixed dollar amount and a percentage of a financial metric (e.g.,
      Total Assets or EBITDA).
    sections:
      - negative_covenants
      - definitions

  covenant_lite:
    aliases:
      - "cov-lite"
      - "cov lite"
      - "covenant lite"
      - "covenant-lite"
      - "no maintenance covenant"
      - "no financial covenant"
      - "incurrence only"
    search_terms:
      - "financial covenant"
      - "maintenance covenant"
      - "incurrence"
      - "springing"
      - "Total Net Leverage Ratio"
    description: >
      Covenant-lite (cov-lite) refers to term loan facilities that lack
      maintenance financial covenants, relying only on incurrence-based tests.
      A springing financial covenant activates only when a revolving facility is
      drawn above a threshold (typically 35-40%).
    sections:
      - financial_covenants
      - facility_terms

  ecf_sweep:
    aliases:
      - "ecf sweep"
      - "excess cash flow"
      - "cash sweep"
      - "ecf"
      - "cash flow sweep"
    search_terms:
      - "Excess Cash Flow"
      - "mandatory prepayment"
      - "sweep"
      - "step-down"
      - "net of"
    description: >
      Excess Cash Flow (ECF) sweeps require mandatory prepayment of a percentage
      of excess cash flow, typically with step-downs based on leverage ratio
      (e.g., 50% above 3.0x, 25% between 2.5x-3.0x, 0% below 2.5x). Key
      terms include the ECF definition itself, permitted deductions, and any
      voluntary prepayment credits.
    sections:
      - facility_terms
      - definitions

  portability:
    aliases:
      - "portability"
      - "portable"
      - "change of control portability"
      - "coc portability"
    search_terms:
      - "portability"
      - "Change of Control"
      - "change of control"
      - "Permitted Holder"
      - "leverage"
    description: >
      Portability provisions allow a change of control to occur without
      triggering a mandatory prepayment or event of default, provided certain
      conditions are met (typically a leverage ratio test). This lets the
      borrower be acquired without refinancing the existing credit facility.
    sections:
      - events_of_default
      - definitions

  yank_a_bank:
    aliases:
      - "yank-a-bank"
      - "yank a bank"
      - "yankbank"
      - "replacement lender"
      - "defaulting lender"
    search_terms:
      - "yank-a-bank"
      - "replacement"
      - "Defaulting Lender"
      - "non-consenting lender"
      - "assignment"
      - "remove"
    description: >
      Yank-a-bank provisions allow the borrower to replace a lender that
      refuses to consent to an amendment or waiver, or that has defaulted on
      its funding obligations. The borrower can force assignment of the
      non-consenting or defaulting lender's position to a replacement lender.
    sections:
      - miscellaneous
      - agents

  snooze_you_lose:
    aliases:
      - "snooze you lose"
      - "snooze-you-lose"
      - "deemed consent"
      - "non-responsive lender"
    search_terms:
      - "deemed consent"
      - "snooze"
      - "non-responsive"
      - "failure to respond"
      - "business days"
    description: >
      Snooze-you-lose provisions deem a lender to have consented to an
      amendment or waiver if it fails to respond within a specified period
      (typically 10 business days). Prevents holdout lenders from blocking
      amendments through inaction.
    sections:
      - miscellaneous

  ebitda_addbacks:
    aliases:
      - "ebitda addback"
      - "ebitda add-back"
      - "addback"
      - "add-back"
      - "cost savings"
      - "synergies"
      - "run-rate"
      - "pro forma adjustment"
    search_terms:
      - "add back"
      - "addback"
      - "cost savings"
      - "synergies"
      - "run-rate"
      - "pro forma"
      - "Consolidated EBITDA"
      - "restructuring"
    description: >
      EBITDA addbacks allow the borrower to adjust Consolidated EBITDA upward
      for projected cost savings, synergies, and other non-recurring items.
      Key terms include caps on addbacks (often 15-25% of EBITDA), realization
      periods (12-24 months), and types of permitted adjustments.
    sections:
      - definitions

  equity_cure:
    aliases:
      - "equity cure"
      - "cure right"
      - "equity contribution"
      - "equity cure right"
    search_terms:
      - "equity cure"
      - "cure"
      - "equity contribution"
      - "Specified Equity Contribution"
      - "financial covenant"
    description: >
      Equity cure rights allow the borrower (or its sponsor) to inject equity
      to cure a financial covenant default. Key terms include the number of
      permitted cures (typically 2 per year, 5 lifetime), minimum/maximum cure
      amounts, and whether the cure is applied to increase EBITDA, reduce debt,
      or both.
    sections:
      - financial_covenants

  asset_sale_mandatory_prepayment:
    aliases:
      - "asset sale sweep"
      - "asset disposition"
      - "reinvestment"
      - "reinvestment period"
      - "net cash proceeds"
    search_terms:
      - "asset sale"
      - "disposition"
      - "Net Cash Proceeds"
      - "mandatory prepayment"
      - "reinvestment"
      - "365"
      - "Reinvestment Period"
    description: >
      Asset sale mandatory prepayment provisions require the borrower to prepay
      debt with net cash proceeds from asset sales, subject to reinvestment
      rights (typically 12-18 months to reinvest, with a 6-month extension).
      Step-downs may reduce the prepayment percentage at lower leverage levels.
    sections:
      - facility_terms

  incremental_facility:
    aliases:
      - "incremental"
      - "accordion"
      - "incremental term loan"
      - "incremental equivalent"
      - "incremental revolving"
    search_terms:
      - "incremental"
      - "Incremental Term Loan"
      - "Incremental Equivalent"
      - "accordion"
      - "Available Incremental Amount"
      - "Fixed Incremental Amount"
      - "ratio"
    description: >
      Incremental facility provisions allow the borrower to add additional
      debt capacity (term loans or revolving commitments) under the existing
      credit agreement. Key terms include the fixed dollar basket, ratio-based
      capacity, MFN protections, and incremental equivalent debt (debt incurred
      outside the credit agreement but with similar terms).
    sections:
      - negative_covenants
      - facility_terms
      - definitions

  restricted_payment:
    aliases:
      - "restricted payment"
      - "dividend"
      - "distribution"
      - "share repurchase"
      - "buyback"
      - "rp basket"
    search_terms:
      - "Restricted Payment"
      - "dividend"
      - "distribution"
      - "repurchase"
      - "redemption"
      - "Available Amount"
    description: >
      Restricted payment covenants limit the borrower's ability to pay
      dividends, make distributions, repurchase equity, or make other
      payments to equity holders. Key baskets include the general RP basket,
      Available Amount/builder basket, ratio-conditioned basket, and
      specific carve-outs for tax distributions and management fees.
    sections:
      - negative_covenants
      - definitions

  permitted_acquisition:
    aliases:
      - "permitted acquisition"
      - "acquisition basket"
      - "acquisition"
      - "tuck-in"
    search_terms:
      - "Permitted Acquisition"
      - "acquisition"
      - "investment"
      - "purchase"
      - "similar business"
      - "material adverse effect"
    description: >
      Permitted acquisition provisions define the conditions under which
      the borrower may make acquisitions, typically requiring that the target
      be in a similar line of business, no event of default exists, pro forma
      compliance with financial covenants (if any), and the acquisition
      satisfies specified size thresholds or leverage tests.
    sections:
      - negative_covenants
      - definitions

  springing_covenant:
    aliases:
      - "springing"
      - "springing covenant"
      - "springing financial covenant"
      - "revolver test"
      - "utilization trigger"
    search_terms:
      - "springing"
      - "utilization"
      - "drawn"
      - "revolving"
      - "Total Net Leverage Ratio"
      - "35%"
      - "40%"
    description: >
      A springing financial covenant only activates when the revolving credit
      facility utilization exceeds a specified threshold (typically 35-40% of
      total revolving commitments, excluding undrawn letters of credit up to a
      threshold). Common in cov-lite structures where the term loan has no
      maintenance covenants.
    sections:
      - financial_covenants

  margin_ratchet:
    aliases:
      - "margin ratchet"
      - "pricing grid"
      - "step-down"
      - "step down"
      - "leverage-based pricing"
    search_terms:
      - "Applicable Rate"
      - "Applicable Margin"
      - "pricing grid"
      - "step-down"
      - "Total Net Leverage Ratio"
      - "Level"
      - "Tier"
    description: >
      A margin ratchet (or pricing grid) adjusts the interest rate spread
      based on a leverage ratio. As the borrower deleverages, the spread
      steps down; as leverage increases, the spread steps up. Key terms
      include the applicable ratio, number of tiers, and spread at each level.
    sections:
      - facility_terms
      - definitions
```

- [ ] **Step 3: Create synonyms.yaml**

```yaml
# credit_analyzer/knowledge/synonyms.yaml
#
# Leveraged Finance Synonym Dictionary
#
# Maps informal/alternative terms to canonical forms. Used for query expansion
# and sibling filtering. Extends the existing LEGAL_SYNONYMS and _TERM_ALIASES.
#
# Format: canonical_term -> list of synonyms (all matched case-insensitively)

synonyms:

  # Facility terms
  applicable_margin:
    canonical: "Applicable Margin"
    alternatives:
      - "applicable rate"
      - "interest rate spread"
      - "sofr spread"
      - "abr spread"
      - "pricing"
      - "margin"
      - "spread"

  term_loan:
    canonical: "Term Loan"
    alternatives:
      - "term facility"
      - "TLB"
      - "TLA"
      - "term loan B"
      - "term loan A"
      - "first lien term loan"

  revolving_facility:
    canonical: "Revolving Credit Facility"
    alternatives:
      - "revolver"
      - "RCF"
      - "revolving commitment"
      - "revolving loan"

  # Financial metrics
  ebitda:
    canonical: "Consolidated EBITDA"
    alternatives:
      - "ebitda"
      - "adjusted ebitda"
      - "pro forma ebitda"

  leverage_ratio:
    canonical: "Total Net Leverage Ratio"
    alternatives:
      - "leverage ratio"
      - "leverage test"
      - "net leverage"
      - "total leverage"
      - "debt to ebitda"
      - "debt/ebitda"

  interest_coverage:
    canonical: "Fixed Charge Coverage Ratio"
    alternatives:
      - "interest coverage"
      - "coverage ratio"
      - "FCCR"
      - "ICR"
      - "debt service coverage"

  excess_cash_flow:
    canonical: "Excess Cash Flow"
    alternatives:
      - "ECF"
      - "cash sweep"
      - "cash flow sweep"

  # Covenant terms
  indebtedness:
    canonical: "Indebtedness"
    alternatives:
      - "debt"
      - "borrowing"
      - "obligation"
      - "funded debt"

  lien:
    canonical: "Lien"
    alternatives:
      - "security interest"
      - "encumbrance"
      - "pledge"
      - "mortgage"
      - "charge"

  restricted_payment:
    canonical: "Restricted Payment"
    alternatives:
      - "dividend"
      - "distribution"
      - "share repurchase"
      - "buyback"
      - "equity distribution"

  investment:
    canonical: "Investment"
    alternatives:
      - "acquisition"
      - "purchase"
      - "capital contribution"
      - "equity interest"

  # Structural terms
  unrestricted_subsidiary:
    canonical: "Unrestricted Subsidiary"
    alternatives:
      - "excluded subsidiary"
      - "non-guarantor subsidiary"
      - "designated subsidiary"

  permitted_holder:
    canonical: "Permitted Holder"
    alternatives:
      - "sponsor"
      - "private equity sponsor"
      - "PE sponsor"
      - "controlling shareholder"

  material_adverse_effect:
    canonical: "Material Adverse Effect"
    alternatives:
      - "MAE"
      - "material adverse change"
      - "MAC"

  # Rates
  sofr:
    canonical: "SOFR"
    alternatives:
      - "Adjusted Term SOFR"
      - "Term SOFR"
      - "secured overnight financing rate"

  base_rate:
    canonical: "Alternate Base Rate"
    alternatives:
      - "ABR"
      - "base rate"
      - "prime rate"

  # Amendment terms
  required_lenders:
    canonical: "Required Lenders"
    alternatives:
      - "majority lenders"
      - "requisite lenders"
      - "voting threshold"
```

- [ ] **Step 4: Commit data files**

```bash
git add credit_analyzer/knowledge/__init__.py credit_analyzer/knowledge/concepts.yaml credit_analyzer/knowledge/synonyms.yaml
git commit -m "feat: add leveraged finance concept registry and synonym dictionary"
```

### Task 2: Registry Module (Python loader + matcher)

**Files:**
- Create: `credit_analyzer/knowledge/registry.py`
- Test: `tests/test_knowledge_registry.py`

- [ ] **Step 1: Write tests for the registry**

```python
# tests/test_knowledge_registry.py
"""Tests for the leveraged finance knowledge registry."""

from __future__ import annotations

from credit_analyzer.knowledge.registry import (
    ConceptMatch,
    DomainRegistry,
)


class TestDomainRegistry:
    """Tests for loading and querying the concept registry."""

    def setup_method(self) -> None:
        self.registry = DomainRegistry()

    def test_loads_concepts(self) -> None:
        """Registry loads concepts from YAML."""
        assert len(self.registry.concepts) > 10

    def test_loads_synonyms(self) -> None:
        """Registry loads synonym groups from YAML."""
        assert len(self.registry.synonym_groups) > 10

    def test_match_concept_exact_alias(self) -> None:
        """Exact alias match returns the concept."""
        matches = self.registry.match_concepts("Are there any J.Crew provisions?")
        assert len(matches) >= 1
        assert any(m.concept_id == "j_crew_provision" for m in matches)

    def test_match_concept_case_insensitive(self) -> None:
        """Alias matching is case-insensitive."""
        matches = self.registry.match_concepts("does this have SERTA protections")
        assert any(m.concept_id == "serta_provision" for m in matches)

    def test_match_concept_multiple(self) -> None:
        """Multiple concepts can match in a single query."""
        matches = self.registry.match_concepts(
            "What about J.Crew and Serta provisions?"
        )
        ids = {m.concept_id for m in matches}
        assert "j_crew_provision" in ids
        assert "serta_provision" in ids

    def test_no_match_simple_query(self) -> None:
        """Simple queries without concept aliases return no matches."""
        matches = self.registry.match_concepts("What is the SOFR spread?")
        # This should NOT match a named provision concept
        named_provisions = {
            m.concept_id for m in matches
            if m.concept_id in ("j_crew_provision", "serta_provision", "chewy_provision")
        }
        assert len(named_provisions) == 0

    def test_concept_has_search_terms(self) -> None:
        """Matched concepts provide search terms for retrieval."""
        matches = self.registry.match_concepts("any trap-door provisions?")
        assert len(matches) >= 1
        m = next(m for m in matches if m.concept_id == "j_crew_provision")
        assert len(m.search_terms) > 0
        assert "intellectual property" in m.search_terms

    def test_concept_has_description(self) -> None:
        """Matched concepts include a description for LLM context."""
        matches = self.registry.match_concepts("freebie basket")
        m = next(m for m in matches if m.concept_id == "freebie_basket")
        assert "free-and-clear" in m.description.lower() or "free and clear" in m.description.lower()

    def test_expand_synonyms(self) -> None:
        """Synonym expansion returns canonical + alternatives."""
        expanded = self.registry.expand_synonyms("what is the revolver commitment")
        # Should find revolving_facility synonym group
        assert "Revolving Credit Facility" in expanded or "revolving commitment" in expanded

    def test_expand_synonyms_no_match(self) -> None:
        """Queries with no synonym matches return empty."""
        expanded = self.registry.expand_synonyms("tell me about the weather")
        assert len(expanded) == 0

    def test_get_concept_context(self) -> None:
        """get_concept_context returns formatted string for LLM injection."""
        matches = self.registry.match_concepts("J.Crew provisions")
        context = self.registry.get_concept_context(matches)
        assert "J.Crew" in context or "j_crew" in context
        assert "intellectual property" in context.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_knowledge_registry.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement the registry module**

```python
# credit_analyzer/knowledge/registry.py
"""Domain knowledge registry for leveraged finance concepts and synonyms.

Loads curated YAML data files and provides fast lookup for concept alias
matching and synonym expansion during query processing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # pyright: ignore[reportMissingTypeStubs]

_KNOWLEDGE_DIR = Path(__file__).parent


@dataclass(frozen=True)
class ConceptMatch:
    """A matched domain concept with its retrieval metadata."""

    concept_id: str
    matched_alias: str
    search_terms: list[str]
    description: str
    sections: list[str]


@dataclass
class _ConceptEntry:
    """Internal representation of a concept from YAML."""

    concept_id: str
    aliases: list[str]
    search_terms: list[str]
    description: str
    sections: list[str]
    # Pre-compiled pattern for fast matching
    pattern: re.Pattern[str]


@dataclass
class _SynonymGroup:
    """A group of synonymous terms."""

    canonical: str
    alternatives: list[str]


class DomainRegistry:
    """Registry of leveraged finance concepts and synonyms.

    Loads from YAML on construction and provides fast alias matching
    and synonym expansion for query preprocessing.
    """

    def __init__(
        self,
        concepts_path: Path | None = None,
        synonyms_path: Path | None = None,
    ) -> None:
        self._concepts: list[_ConceptEntry] = []
        self._synonym_groups: list[_SynonymGroup] = []

        concepts_file = concepts_path or _KNOWLEDGE_DIR / "concepts.yaml"
        synonyms_file = synonyms_path or _KNOWLEDGE_DIR / "synonyms.yaml"

        if concepts_file.exists():
            self._load_concepts(concepts_file)
        if synonyms_file.exists():
            self._load_synonyms(synonyms_file)

    @property
    def concepts(self) -> list[_ConceptEntry]:
        return self._concepts

    @property
    def synonym_groups(self) -> list[_SynonymGroup]:
        return self._synonym_groups

    def _load_concepts(self, path: Path) -> None:
        """Load concept entries from YAML and pre-compile alias patterns."""
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        for concept_id, entry in (data.get("concepts") or {}).items():
            aliases: list[str] = entry.get("aliases", [])
            if not aliases:
                continue

            # Build regex: sort aliases longest-first to prefer longer matches
            sorted_aliases = sorted(aliases, key=len, reverse=True)
            escaped = [re.escape(a) for a in sorted_aliases]
            pattern = re.compile(
                r"\b(?:" + "|".join(escaped) + r")\b",
                re.IGNORECASE,
            )

            self._concepts.append(_ConceptEntry(
                concept_id=concept_id,
                aliases=aliases,
                search_terms=entry.get("search_terms", []),
                description=entry.get("description", "").strip(),
                sections=entry.get("sections", []),
                pattern=pattern,
            ))

    def _load_synonyms(self, path: Path) -> None:
        """Load synonym groups from YAML."""
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        for _group_id, entry in (data.get("synonyms") or {}).items():
            canonical = entry.get("canonical", "")
            alternatives = entry.get("alternatives", [])
            if canonical and alternatives:
                self._synonym_groups.append(
                    _SynonymGroup(canonical=canonical, alternatives=alternatives)
                )

    def match_concepts(self, query: str) -> list[ConceptMatch]:
        """Find all domain concepts whose aliases appear in the query.

        Returns a list of ConceptMatch objects with retrieval metadata.
        Matching is case-insensitive and uses word boundaries.
        """
        matches: list[ConceptMatch] = []
        for concept in self._concepts:
            m = concept.pattern.search(query)
            if m:
                matches.append(ConceptMatch(
                    concept_id=concept.concept_id,
                    matched_alias=m.group(0),
                    search_terms=concept.search_terms,
                    description=concept.description,
                    sections=concept.sections,
                ))
        return matches

    def expand_synonyms(self, query: str) -> list[str]:
        """Find synonym expansions relevant to the query.

        Returns a list of canonical and alternative terms that could
        be used to broaden retrieval.
        """
        query_lower = query.lower()
        expansions: list[str] = []
        for group in self._synonym_groups:
            # Check if canonical or any alternative appears in the query
            all_terms = [group.canonical.lower()] + [
                a.lower() for a in group.alternatives
            ]
            for term in all_terms:
                if len(term) >= 3 and term in query_lower:
                    # Add all terms from the group that are NOT already in the query
                    for t in [group.canonical] + group.alternatives:
                        if t.lower() not in query_lower:
                            expansions.append(t)
                    break
        return expansions

    def get_concept_context(self, matches: list[ConceptMatch]) -> str:
        """Format matched concepts as context text for LLM injection.

        Returns a string to append to the system prompt or user prompt
        giving the LLM domain context about what the user is asking about.
        """
        if not matches:
            return ""
        parts: list[str] = ["=== DOMAIN CONCEPT CONTEXT ==="]
        for m in matches:
            parts.append(
                f'CONCEPT: {m.concept_id.replace("_", " ").title()}\n'
                f"DESCRIPTION: {m.description}\n"
                f'LOOK FOR: {", ".join(m.search_terms)}'
            )
        return "\n\n".join(parts)
```

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_knowledge_registry.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add credit_analyzer/knowledge/registry.py tests/test_knowledge_registry.py
git commit -m "feat: add domain registry module with concept matching and synonym expansion"
```

---

## Chunk 2: Concept-Aware Query Expansion + Quality Gate

### Task 3: Wire Registry into Query Expansion

**Files:**
- Modify: `credit_analyzer/generation/query_expansion.py`
- Test: `tests/test_query_expansion.py` (create)

Modify `expand_query()` to consult the domain registry. When concept aliases are detected, inject the concept's search terms as additional retrieval queries. Also use synonym expansion to broaden coverage.

- [ ] **Step 1: Write tests for concept-aware expansion**

```python
# tests/test_query_expansion.py
"""Tests for concept-aware query expansion."""

from __future__ import annotations

from credit_analyzer.generation.query_expansion import expand_query


class TestConceptAwareExpansion:
    """Tests that concept registry integration works in expand_query."""

    def test_j_crew_expands_to_search_terms(self) -> None:
        """A J.Crew query should produce retrieval queries with concept search terms."""
        queries = expand_query("Are there any J.Crew provisions?")
        all_text = " ".join(queries).lower()
        assert "intellectual property" in all_text or "unrestricted subsidiary" in all_text

    def test_serta_expands_to_search_terms(self) -> None:
        queries = expand_query("Does this document have Serta protections?")
        all_text = " ".join(queries).lower()
        assert "uptier" in all_text or "priming" in all_text or "subordinat" in all_text

    def test_freebie_expands(self) -> None:
        queries = expand_query("What is the freebie basket?")
        all_text = " ".join(queries).lower()
        assert "free and clear" in all_text or "incremental" in all_text

    def test_simple_query_unchanged(self) -> None:
        """Simple queries that don't match concepts still work normally."""
        queries = expand_query("What is the SOFR spread?")
        assert queries[0] == "What is the SOFR spread?"
        assert len(queries) >= 1

    def test_original_query_always_first(self) -> None:
        """The original query is always the first in the list."""
        queries = expand_query("Any J.Crew provisions?")
        assert queries[0] == "Any J.Crew provisions?"

    def test_max_queries_respected(self) -> None:
        """Expansion should not produce an excessive number of queries."""
        queries = expand_query("J.Crew and Serta and Chewy provisions?")
        assert len(queries) <= 6  # reasonable cap


class TestExpandQueryBaseline:
    """Ensure existing expansion behavior is preserved."""

    def test_defined_term_expansion(self) -> None:
        """Capitalized terms still generate definition-focused queries."""
        queries = expand_query("What is the Total Net Leverage Ratio?")
        all_text = " ".join(queries).lower()
        assert "definition" in all_text or "total net leverage ratio" in all_text

    def test_financial_keyword_expansion(self) -> None:
        """Financial keywords still broaden the query."""
        queries = expand_query("What is the leverage covenant test?")
        assert len(queries) >= 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_query_expansion.py -v`
Expected: concept-aware tests FAIL

- [ ] **Step 3: Modify expand_query to use registry**

In `credit_analyzer/generation/query_expansion.py`, add concept matching and synonym expansion to the existing `expand_query()` function. Key changes:

1. Import and lazily initialize `DomainRegistry`
2. Check for concept alias matches before existing expansion logic
3. When concepts match, generate search-term-based queries (up to 2 additional)
4. When synonyms match, append canonical forms to the query
5. Increase the query cap from 3 to 5 for concept-matched queries
6. Return `ConceptMatch` list alongside queries via a new `expand_query_with_concepts()` function (the old `expand_query` still works for backward compat)

Modify the existing `expand_query` function body and add a new `expand_query_with_concepts` function:

```python
# At module level, add lazy registry singleton
_registry: DomainRegistry | None = None

def _get_registry() -> DomainRegistry:
    global _registry
    if _registry is None:
        from credit_analyzer.knowledge.registry import DomainRegistry
        _registry = DomainRegistry()
    return _registry
```

The modified `expand_query` function should:
1. Run concept matching first via `_get_registry().match_concepts(question)`
2. If concepts matched, build queries from search terms (combine 3-4 search terms per query)
3. Then run existing alias/keyword expansion logic
4. Cap at 5 queries total (was 3) when concepts are matched, 3 otherwise

The new `expand_query_with_concepts` function returns both the queries and the matched concepts for downstream use (LLM context injection, UI status).

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_query_expansion.py tests/test_qa_engine.py -v`
Expected: All PASS (new + existing)

- [ ] **Step 5: Commit**

```bash
git add credit_analyzer/generation/query_expansion.py tests/test_query_expansion.py
git commit -m "feat: wire domain concept registry into query expansion"
```

### Task 4: Retrieval Quality Gate

**Files:**
- Create: `credit_analyzer/retrieval/quality_gate.py`
- Test: `tests/test_quality_gate.py`

A lightweight heuristic that checks whether retrieval results are likely sufficient to answer the query. If insufficient, it signals that the query should be escalated to the LLM decomposer (Layer 3).

- [ ] **Step 1: Write tests**

```python
# tests/test_quality_gate.py
"""Tests for the retrieval quality gate."""

from __future__ import annotations

from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.retrieval.hybrid_retriever import HybridChunk, RetrievalResult
from credit_analyzer.retrieval.quality_gate import (
    GateDecision,
    check_retrieval_quality,
)


def _make_chunk(
    score: float = 0.8,
    text: str = "The Borrower shall maintain a Total Leverage Ratio of 4.50:1.00.",
) -> HybridChunk:
    return HybridChunk(
        chunk=Chunk(
            chunk_id="c1", text=text, section_id="7.11",
            section_title="Financial Covenants", article_number=7,
            article_title="NEGATIVE COVENANTS", section_type="financial_covenants",
            chunk_type="text", page_numbers=[45], defined_terms_present=[],
            chunk_index=0, token_count=30,
        ),
        score=score,
        source="both",
    )


class TestRetrievalQualityGate:
    """Tests for the quality gate heuristic."""

    def test_high_score_chunks_sufficient(self) -> None:
        """High-scoring chunks pass the gate."""
        result = RetrievalResult(
            chunks=[_make_chunk(0.85), _make_chunk(0.75), _make_chunk(0.65)],
            injected_definitions={},
        )
        decision = check_retrieval_quality(result, "What is the leverage ratio?")
        assert decision == GateDecision.SUFFICIENT

    def test_low_score_chunks_insufficient(self) -> None:
        """All low-scoring chunks fail the gate."""
        result = RetrievalResult(
            chunks=[_make_chunk(0.18), _make_chunk(0.16), _make_chunk(0.15)],
            injected_definitions={},
        )
        decision = check_retrieval_quality(result, "Are there J.Crew provisions?")
        assert decision == GateDecision.INSUFFICIENT

    def test_empty_results_insufficient(self) -> None:
        """No chunks at all fails the gate."""
        result = RetrievalResult(chunks=[], injected_definitions={})
        decision = check_retrieval_quality(result, "anything")
        assert decision == GateDecision.INSUFFICIENT

    def test_no_term_overlap_insufficient(self) -> None:
        """Chunks that don't overlap with query terms fail the gate."""
        chunk = _make_chunk(
            score=0.5,
            text="Administrative Agent shall mean JPMorgan Chase Bank, N.A.",
        )
        result = RetrievalResult(chunks=[chunk], injected_definitions={})
        decision = check_retrieval_quality(
            result, "What are the restricted payment baskets?",
        )
        assert decision == GateDecision.INSUFFICIENT
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_quality_gate.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement quality gate**

```python
# credit_analyzer/retrieval/quality_gate.py
"""Retrieval quality gate — heuristic check for result sufficiency.

Determines whether retrieved chunks are likely sufficient to answer a
query, or whether the query should be escalated to the LLM decomposer
for more targeted retrieval.
"""

from __future__ import annotations

import enum
import re

from credit_analyzer.retrieval.hybrid_retriever import RetrievalResult

# Thresholds tuned for the credit analyzer's score distributions
_MIN_TOP_SCORE = 0.35          # Best chunk must score at least this
_MIN_MEAN_TOP3_SCORE = 0.25    # Mean of top-3 chunks must exceed this
_MIN_TERM_OVERLAP_RATIO = 0.3  # Fraction of query terms found in top chunks

_STOP_WORDS = frozenset({
    "what", "where", "when", "which", "how", "does", "this", "that",
    "there", "have", "been", "with", "from", "they", "their", "will",
    "would", "could", "should", "about", "into", "than", "then",
    "also", "just", "more", "some", "such", "only", "very", "most",
    "document", "agreement", "provision", "provisions", "section",
    "any", "are", "the", "and", "for", "not", "but",
})


class GateDecision(enum.Enum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"


def check_retrieval_quality(
    result: RetrievalResult,
    query: str,
) -> GateDecision:
    """Check whether retrieval results are likely sufficient for the query.

    Uses a multi-signal heuristic:
    1. Score check: are the top chunks scoring high enough?
    2. Term overlap: do the retrieved chunks contain query-relevant terms?
    3. Chunk count: do we have a minimum number of chunks?

    Returns GateDecision.SUFFICIENT or GateDecision.INSUFFICIENT.
    """
    if not result.chunks:
        return GateDecision.INSUFFICIENT

    scores = sorted([hc.score for hc in result.chunks], reverse=True)

    # Signal 1: Top score too low
    if scores[0] < _MIN_TOP_SCORE:
        return GateDecision.INSUFFICIENT

    # Signal 2: Mean of top-3 too low
    top3 = scores[:3]
    if sum(top3) / len(top3) < _MIN_MEAN_TOP3_SCORE:
        return GateDecision.INSUFFICIENT

    # Signal 3: Query term overlap with retrieved text
    query_terms = _extract_query_terms(query)
    if query_terms:
        chunk_text = " ".join(
            hc.chunk.text.lower() for hc in result.chunks[:5]
        )
        found = sum(1 for t in query_terms if t in chunk_text)
        overlap_ratio = found / len(query_terms)
        if overlap_ratio < _MIN_TERM_OVERLAP_RATIO:
            return GateDecision.INSUFFICIENT

    return GateDecision.SUFFICIENT


def _extract_query_terms(query: str) -> list[str]:
    """Extract meaningful terms from a query for overlap checking."""
    words = re.findall(r"[a-zA-Z]{3,}", query.lower())
    return [w for w in words if w not in _STOP_WORDS]
```

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_quality_gate.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add credit_analyzer/retrieval/quality_gate.py tests/test_quality_gate.py
git commit -m "feat: add retrieval quality gate for escalation decisions"
```

---

## Chunk 3: LLM Query Decomposer + QAEngine Integration

### Task 5: LLM Query Decomposer (Layer 3)

**Files:**
- Create: `credit_analyzer/generation/query_decomposer.py`
- Test: `tests/test_query_decomposer.py`

When the quality gate flags insufficient results, this module asks the LLM to decompose the original query into targeted sub-queries. It receives concept context (from the registry) so the LLM understands domain terminology.

- [ ] **Step 1: Write tests**

```python
# tests/test_query_decomposer.py
"""Tests for the LLM query decomposer."""

from __future__ import annotations

from unittest.mock import MagicMock

from credit_analyzer.generation.query_decomposer import (
    DECOMPOSITION_SYSTEM_PROMPT,
    decompose_query,
    parse_sub_queries,
)
from credit_analyzer.llm.base import LLMResponse


class TestParseSubQueries:
    """Tests for parsing LLM decomposition output."""

    def test_parses_numbered_list(self) -> None:
        text = "1. What provisions allow IP transfer to unrestricted subsidiaries?\n2. Are there restrictions on designating unrestricted subsidiaries?"
        queries = parse_sub_queries(text)
        assert len(queries) == 2
        assert "IP transfer" in queries[0]
        assert "unrestricted subsidiaries" in queries[1]

    def test_parses_dashed_list(self) -> None:
        text = "- provisions for transferring intellectual property\n- unrestricted subsidiary designation conditions"
        queries = parse_sub_queries(text)
        assert len(queries) == 2

    def test_parses_plain_lines(self) -> None:
        text = "intellectual property transfer provisions\nunrestricted subsidiary restrictions"
        queries = parse_sub_queries(text)
        assert len(queries) == 2

    def test_filters_empty_lines(self) -> None:
        text = "1. query one\n\n2. query two\n\n"
        queries = parse_sub_queries(text)
        assert len(queries) == 2

    def test_caps_at_max(self) -> None:
        text = "\n".join(f"{i}. query {i}" for i in range(1, 15))
        queries = parse_sub_queries(text)
        assert len(queries) <= 5

    def test_returns_original_on_empty(self) -> None:
        """If parsing yields nothing, returns empty list."""
        queries = parse_sub_queries("")
        assert queries == []


class TestDecomposeQuery:
    """Tests for the full decomposition call."""

    def test_calls_llm_with_concept_context(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = LLMResponse(
            text="1. What are the IP transfer provisions?\n2. Can the borrower designate unrestricted subsidiaries?",
            tokens_used=30, model="test", duration_seconds=0.5,
        )
        concept_context = "CONCEPT: J.Crew Provision\nDESCRIPTION: IP transfer to unrestricted subs"
        queries = decompose_query(
            llm, "Are there J.Crew provisions?", concept_context=concept_context,
        )
        assert len(queries) >= 2
        # Verify concept context was passed to LLM
        call_kwargs = llm.complete.call_args.kwargs
        assert "J.Crew" in call_kwargs["user_prompt"] or "J.Crew" in call_kwargs.get("system_prompt", "")

    def test_returns_fallback_on_llm_error(self) -> None:
        llm = MagicMock()
        llm.complete.side_effect = RuntimeError("LLM down")
        queries = decompose_query(llm, "Are there J.Crew provisions?")
        # Should return fallback (original query)
        assert len(queries) >= 1
        assert "J.Crew" in queries[0]


class TestDecompositionPrompt:
    """Tests for the decomposition system prompt."""

    def test_prompt_exists_and_mentions_credit(self) -> None:
        assert len(DECOMPOSITION_SYSTEM_PROMPT) > 100
        assert "credit" in DECOMPOSITION_SYSTEM_PROMPT.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_query_decomposer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement query decomposer**

```python
# credit_analyzer/generation/query_decomposer.py
"""LLM-based query decomposition for complex leveraged finance questions.

When the retrieval quality gate detects insufficient results, this module
asks the LLM to decompose the original query into targeted sub-queries
that can each be run through the retrieval pipeline independently.
"""

from __future__ import annotations

import logging
import re

from credit_analyzer.llm.base import LLMProvider

logger = logging.getLogger(__name__)

DECOMPOSITION_SYSTEM_PROMPT: str = """\
You are a leveraged finance expert helping to search a credit agreement. \
A user has asked a question, but the initial search did not find relevant \
passages. Your job is to decompose the question into 2-5 specific, \
targeted search queries that will find the relevant provisions in the \
document.

RULES:
1. Each query should target a DIFFERENT aspect or section of the credit \
agreement.
2. Use the specific legal/financial terminology that would appear in the \
document text (not colloquial names).
3. If domain concept context is provided, use the suggested search terms.
4. Output ONLY the search queries, one per line, numbered 1-5.
5. Keep each query under 15 words.
6. Do NOT include explanations or commentary."""

_MAX_SUB_QUERIES = 5


def decompose_query(
    llm: LLMProvider,
    question: str,
    *,
    concept_context: str = "",
) -> list[str]:
    """Decompose a complex query into targeted sub-queries using the LLM.

    Args:
        llm: The LLM provider to use for decomposition.
        question: The original user question.
        concept_context: Optional domain concept context from the registry.

    Returns:
        A list of 2-5 sub-queries for retrieval. Falls back to the
        original question on error.
    """
    user_parts: list[str] = []
    if concept_context:
        user_parts.append(concept_context)
        user_parts.append("")
    user_parts.append(f"USER QUESTION: {question}")
    user_parts.append("")
    user_parts.append("Generate 2-5 targeted search queries:")
    user_prompt = "\n".join(user_parts)

    try:
        response = llm.complete(
            system_prompt=DECOMPOSITION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=200,
        )
        queries = parse_sub_queries(response.text)
        if queries:
            logger.info(
                "Decomposed query into %d sub-queries: %r",
                len(queries), queries,
            )
            return queries
    except Exception:
        logger.warning("Query decomposition failed, using original", exc_info=True)

    return [question]


def parse_sub_queries(text: str) -> list[str]:
    """Parse numbered/bulleted sub-queries from LLM output.

    Handles formats:
    - "1. query text"
    - "- query text"
    - plain lines

    Returns up to _MAX_SUB_QUERIES queries. Empty lines are skipped.
    """
    lines = text.strip().splitlines()
    queries: list[str] = []
    for line in lines:
        # Strip numbering and bullet markers
        cleaned = re.sub(r"^\s*(?:\d+[.)]\s*|-\s*|\*\s*)", "", line).strip()
        if cleaned and len(cleaned) > 5:
            queries.append(cleaned)
        if len(queries) >= _MAX_SUB_QUERIES:
            break
    return queries
```

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_query_decomposer.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add credit_analyzer/generation/query_decomposer.py tests/test_query_decomposer.py
git commit -m "feat: add LLM query decomposer for complex question handling"
```

### Task 6: Integrate Layers into QAEngine

**Files:**
- Modify: `credit_analyzer/generation/qa_engine.py`
- Modify: `tests/test_qa_engine.py`

Wire the three layers into the QAEngine's `ask()` and `ask_stream()` methods. The flow becomes:

1. Run concept matching + synonym expansion (Layer 1)
2. Expand and retrieve (existing flow, now concept-aware)
3. Run quality gate (Layer 2)
4. If insufficient AND concepts matched: run query decomposer (Layer 3)
5. Merge decomposed retrieval results into existing results
6. Generate answer with concept context injected into the user prompt

Add tracking fields to `QAResponse` so the UI can show what happened.

- [ ] **Step 1: Write tests for the new integration**

Add to `tests/test_qa_engine.py`:

```python
class TestQAEngineKnowledgeLayer:
    """Tests for the knowledge layer integration in QAEngine."""

    @staticmethod
    def _make_engine_with_low_scores() -> QAEngine:
        """Build a QAEngine that returns low-scoring chunks to trigger escalation."""
        retriever = MagicMock(spec=HybridRetriever)
        # Low scores will trigger the quality gate
        low_chunk = _make_hybrid_chunk(chunk_id="c1", score=0.18)
        retriever.retrieve.return_value = _make_retrieval_result(
            chunks=[low_chunk],
        )

        llm = MagicMock()
        # First call: decomposition, second call: answer
        llm.complete = MagicMock(
            side_effect=[
                LLMResponse(  # decomposition
                    text="1. intellectual property transfer provisions\n2. unrestricted subsidiary designation",
                    tokens_used=20, model="test", duration_seconds=0.3,
                ),
                _mock_llm_response(),  # final answer
            ]
        )
        return QAEngine(retriever=retriever, llm=llm)

    def test_concept_context_injected(self) -> None:
        """When concepts match, their context is added to the user prompt."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response())

        engine = QAEngine(retriever=retriever, llm=llm)
        resp = engine.ask("Are there any J.Crew provisions?", "doc1")

        user_prompt: str = llm.complete.call_args.kwargs["user_prompt"]
        assert "DOMAIN CONCEPT CONTEXT" in user_prompt or "J.Crew" in user_prompt

    def test_response_tracks_concepts_matched(self) -> None:
        """QAResponse includes which concepts were matched."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response())

        engine = QAEngine(retriever=retriever, llm=llm)
        resp = engine.ask("Are there J.Crew provisions?", "doc1")

        assert hasattr(resp, "concepts_matched")
        assert len(resp.concepts_matched) >= 1

    def test_response_tracks_escalated(self) -> None:
        """QAResponse indicates when query was escalated."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response())

        engine = QAEngine(retriever=retriever, llm=llm)
        resp = engine.ask("What is the SOFR spread?", "doc1")

        assert hasattr(resp, "escalated")
```

- [ ] **Step 2: Run tests to verify new ones fail**

Run: `.venv/Scripts/python -m pytest tests/test_qa_engine.py::TestQAEngineKnowledgeLayer -v`
Expected: FAIL

- [ ] **Step 3: Modify QAEngine**

Key changes to `qa_engine.py`:

1. Add `concepts_matched: list[str]` and `escalated: bool` fields to `QAResponse`
2. In `ask()` and `ask_stream()`, before retrieval:
   - Call `expand_query_with_concepts()` (new function from Task 3) instead of `_expand_query()`
   - Store matched concepts
3. After initial retrieval, run quality gate
4. If gate says INSUFFICIENT and concepts were matched:
   - Call `decompose_query()` with concept context
   - Run each sub-query through retrieval
   - Merge results with existing results
   - Set `escalated = True`
5. Inject concept context into user prompt via `build_context_prompt()` (or append to question)

The concept context is injected between the definitions section and the question section in the user prompt, so the LLM knows what the user is really asking about.

- [ ] **Step 4: Run all QA tests**

Run: `.venv/Scripts/python -m pytest tests/test_qa_engine.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add credit_analyzer/generation/qa_engine.py tests/test_qa_engine.py
git commit -m "feat: integrate knowledge layer into QAEngine with quality gate and escalation"
```

---

## Chunk 4: UI Status Indicators + Context Prompt Integration

### Task 7: UI Status Indicators During Escalation

**Files:**
- Modify: `credit_analyzer/ui/chat.py`
- Modify: `credit_analyzer/ui/ui_formatters.py`

Add real-time status updates during the Q&A flow so users understand why a complex query takes longer:

1. "Searching relevant sections..." (existing, unchanged for simple queries)
2. "Identified domain concept: J.Crew Provision — expanding search..." (when concepts matched)
3. "Results insufficient — decomposing into targeted queries..." (when escalating)
4. "Deep analysis: searching for [sub-query]..." (during decomposed retrieval)
5. "Composing answer..." (existing)

Also update the context strip to show concept matches and escalation status.

- [ ] **Step 1: Add status helper to ui_formatters.py**

Add a function `concept_status(concept_names: list[str]) -> str` that renders the concept-identified status message using the existing `stream_status` pattern.

```python
def concept_status(concept_names: list[str]) -> str:
    """Render status line for identified domain concepts."""
    names = ", ".join(concept_names[:3])
    return stream_status(f"Identified concept: {names} — expanding search...")

def escalation_status() -> str:
    """Render status line for query escalation."""
    return stream_status("Analyzing query — generating targeted searches...")

def decomposed_search_status(query: str) -> str:
    """Render status for a decomposed sub-query search."""
    truncated = query[:60] + "..." if len(query) > 60 else query
    return stream_status(f"Searching: {truncated}")
```

- [ ] **Step 2: Update context_strip to show concepts**

Modify `context_strip()` in `ui_formatters.py` to accept an optional `concepts: list[str] = None` parameter. When concepts are present, add a pill/badge showing which concepts were identified:

```python
def context_strip(
    confidence: str,
    chunk_count: int,
    sections_used: str,
    duration_seconds: float,
    *,
    retrieval_rounds: int = 1,
    concepts: list[str] | None = None,
    escalated: bool = False,
) -> str:
    # ... existing code ...
    concept_html = ""
    if concepts:
        names = ", ".join(c.replace("_", " ").title() for c in concepts[:3])
        concept_html = f'<span class="concept-badge">{safe_html(names)}</span><span>&middot;</span>'
    escalated_html = ""
    if escalated:
        escalated_html = f'<span>deep search</span><span>&middot;</span>'
    # Insert concept_html and escalated_html into the strip
```

- [ ] **Step 3: Wire status updates into chat.py**

In `run_pending_chat_question()`, modify the streaming flow:

1. After concept matching (before retrieval), if concepts found, update `status_placeholder` with `concept_status()`
2. After quality gate returns INSUFFICIENT, update with `escalation_status()`
3. During decomposed retrieval, update with `decomposed_search_status()` for each sub-query
4. Pass `concepts_matched` and `escalated` to `context_strip()`

This requires the QAEngine to yield status events during streaming. Add a new event type to `ask_stream()`:

```python
@dataclass
class QAStatusEvent:
    """Status event yielded during streaming for UI updates."""
    stage: str  # "concept_match", "escalation", "decomposed_search"
    detail: str  # human-readable detail
```

Modify `ask_stream()` to yield `QAStatusEvent` objects at key points, which `chat.py` renders via the status placeholder.

- [ ] **Step 4: Update context_strip call sites in chat.py**

Both in `run_pending_chat_question()` (live rendering) and `render_chat_message()` (historical), pass the new fields:

```python
st.markdown(
    context_strip(
        final_response.confidence, chunk_count,
        sections_used, duration,
        retrieval_rounds=rounds,
        concepts=final_response.concepts_matched,
        escalated=final_response.escalated,
    ),
    unsafe_allow_html=True,
)
```

- [ ] **Step 5: Add CSS for concept badge**

In `theme_css.py` (or wherever `.context-strip` styles live), add:

```css
.concept-badge {
    background: rgba(99, 102, 241, 0.12);
    color: #6366f1;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 0.75rem;
}
```

- [ ] **Step 6: Run the app manually to verify status flow**

Run: `streamlit run app.py`
Test with: "Are there any J.Crew provisions?" — verify:
- Status shows "Identified concept: J Crew Provision — expanding search..."
- If escalated, status shows "Analyzing query — generating targeted searches..."
- Context strip shows concept badge
- Answer includes concept-informed retrieval context

- [ ] **Step 7: Commit**

```bash
git add credit_analyzer/ui/chat.py credit_analyzer/ui/ui_formatters.py
git commit -m "feat: add UI status indicators for concept matching and query escalation"
```

### Task 8: Inject Concept Context into LLM Prompt

**Files:**
- Modify: `credit_analyzer/generation/prompts.py`

When domain concepts are matched, their description should be injected into the user prompt so the LLM understands the conceptual meaning of the query. This goes between the definitions section and the question.

- [ ] **Step 1: Modify build_context_prompt**

Add an optional `concept_context: str | None = None` parameter to `build_context_prompt()`:

```python
def build_context_prompt(
    chunks: Sequence[HybridChunk],
    definitions: dict[str, str],
    history: Sequence[ConversationTurn],
    question: str,
    preamble_text: str | None = None,
    preamble_page_numbers: Sequence[int] | None = None,
    concept_context: str | None = None,  # NEW
) -> tuple[str, list[HybridChunk]]:
```

After the definitions section and before the history section, insert:

```python
if concept_context:
    parts.append(f"\n{concept_context}")
```

This gives the LLM information like:
```
=== DOMAIN CONCEPT CONTEXT ===
CONCEPT: J Crew Provision
DESCRIPTION: J.Crew provisions allow a borrower to transfer valuable IP to unrestricted subsidiaries...
LOOK FOR: intellectual property, unrestricted subsidiary, transfer, designation
```

- [ ] **Step 2: Update all callers**

Update `qa_engine.py` calls to `build_context_prompt()` to pass `concept_context`.

- [ ] **Step 3: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_qa_engine.py tests/test_query_expansion.py tests/test_quality_gate.py tests/test_query_decomposer.py tests/test_knowledge_registry.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add credit_analyzer/generation/prompts.py credit_analyzer/generation/qa_engine.py
git commit -m "feat: inject domain concept context into LLM prompt for informed answers"
```

---

## Chunk 5: Full Integration Test + Lint/Type Check

### Task 9: Integration Test

**Files:**
- Create: `tests/test_knowledge_integration.py`

An end-to-end test that verifies the full flow: concept matching -> expanded retrieval -> quality gate -> escalation -> concept-informed answer.

- [ ] **Step 1: Write integration test**

```python
# tests/test_knowledge_integration.py
"""Integration tests for the knowledge layer end-to-end flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from credit_analyzer.generation.qa_engine import QAEngine, QAResponse
from credit_analyzer.generation.query_expansion import expand_query_with_concepts
from credit_analyzer.knowledge.registry import DomainRegistry
from credit_analyzer.llm.base import LLMResponse
from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.retrieval.hybrid_retriever import (
    HybridChunk,
    HybridRetriever,
    RetrievalResult,
)
from credit_analyzer.retrieval.quality_gate import GateDecision, check_retrieval_quality


def _make_chunk(text: str, score: float = 0.8) -> HybridChunk:
    return HybridChunk(
        chunk=Chunk(
            chunk_id="c1", text=text, section_id="7.01",
            section_title="Indebtedness", article_number=7,
            article_title="NEGATIVE COVENANTS", section_type="negative_covenants",
            chunk_type="text", page_numbers=[50], defined_terms_present=[],
            chunk_index=0, token_count=50,
        ),
        score=score,
        source="both",
    )


class TestKnowledgeLayerIntegration:
    """End-to-end tests for the knowledge layer."""

    def test_concept_expands_query(self) -> None:
        """Concept matching produces additional retrieval queries."""
        queries, concepts = expand_query_with_concepts(
            "Are there any J.Crew provisions in this agreement?"
        )
        assert len(queries) > 1
        assert len(concepts) >= 1
        assert concepts[0].concept_id == "j_crew_provision"
        # Should have search-term-based queries
        all_text = " ".join(queries).lower()
        assert "intellectual property" in all_text or "unrestricted subsidiary" in all_text

    def test_quality_gate_triggers_on_low_scores(self) -> None:
        """Quality gate correctly identifies insufficient retrieval."""
        result = RetrievalResult(
            chunks=[_make_chunk("unrelated administrative text", score=0.18)],
            injected_definitions={},
        )
        decision = check_retrieval_quality(result, "J.Crew provisions")
        assert decision == GateDecision.INSUFFICIENT

    def test_quality_gate_passes_on_good_results(self) -> None:
        """Quality gate passes when results are relevant."""
        result = RetrievalResult(
            chunks=[
                _make_chunk(
                    "transfer of intellectual property to unrestricted subsidiary",
                    score=0.75,
                ),
            ],
            injected_definitions={},
        )
        decision = check_retrieval_quality(result, "J.Crew provisions")
        assert decision == GateDecision.SUFFICIENT

    def test_full_qa_flow_with_concepts(self) -> None:
        """Full QA flow with concept matching produces an answer."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = RetrievalResult(
            chunks=[_make_chunk("IP transfer provision text", score=0.7)],
            injected_definitions={},
        )

        llm = MagicMock()
        llm.complete = MagicMock(return_value=LLMResponse(
            text="The agreement contains provisions addressing IP transfers.\n\nConfidence: MEDIUM",
            tokens_used=50, model="test", duration_seconds=1.0,
        ))

        engine = QAEngine(retriever=retriever, llm=llm)
        resp = engine.ask("Are there J.Crew provisions?", "doc1")

        assert isinstance(resp, QAResponse)
        assert resp.concepts_matched
        assert "j_crew_provision" in resp.concepts_matched

    def test_synonym_expansion_broadens_retrieval(self) -> None:
        """Synonym expansion adds canonical terms to retrieval."""
        registry = DomainRegistry()
        expanded = registry.expand_synonyms("what is the revolver")
        assert any("Revolving" in t for t in expanded) or any("revolving" in t for t in expanded)
```

- [ ] **Step 2: Run integration tests**

Run: `.venv/Scripts/python -m pytest tests/test_knowledge_integration.py -v`
Expected: All PASS

- [ ] **Step 3: Run full test suite**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: All PASS (no regressions)

- [ ] **Step 4: Run lint and type checks**

Run: `.venv/Scripts/python -m ruff check .`
Run: `.venv/Scripts/python -m pyright`
Fix any issues.

- [ ] **Step 5: Final commit**

```bash
git add tests/test_knowledge_integration.py
git commit -m "test: add integration tests for knowledge layer end-to-end flow"
```

- [ ] **Step 6: Run full test suite one more time**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: All PASS
