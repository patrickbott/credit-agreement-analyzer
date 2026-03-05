"""Lightweight demo brief generation built on top of the Q&A engine."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from credit_analyzer.generation.qa_engine import QAEngine
from credit_analyzer.generation.response_parser import ConfidenceLevel, SourceCitation
from credit_analyzer.llm.base import LLMProvider
from credit_analyzer.ui.workflows import ProcessedDocument

BriefProgressCallback = Callable[[str, float], None]


@dataclass(frozen=True)
class BriefPrompt:
    """A reusable prompt in the demo brief."""

    title: str
    question: str
    helper_text: str


@dataclass(frozen=True)
class BriefSection:
    """A rendered section in the demo brief."""

    title: str
    helper_text: str
    question: str
    answer: str
    confidence: ConfidenceLevel
    sources: list[SourceCitation]


@dataclass(frozen=True)
class SuggestedQuestion:
    """A labeled quick action for the Ask Questions tab."""

    label: str
    prompt: str | None


DEFAULT_BRIEF_PROMPTS: tuple[BriefPrompt, ...] = (
    BriefPrompt(
        title="Deal Snapshot",
        question=(
            "Summarize the borrower, administrative agent, and committed facilities "
            "in 3 concise bullets."
        ),
        helper_text="Parties and facilities.",
    ),
    BriefPrompt(
        title="Pricing",
        question=(
            "Summarize the key pricing mechanics, including the interest rate "
            "framework, applicable margin, fees, and any pricing grid."
        ),
        helper_text="Rates, margins, and fees.",
    ),
    BriefPrompt(
        title="Financial Covenants",
        question=(
            "Summarize any financial maintenance covenant levels, step-downs, "
            "testing periods, and stated consequences of non-compliance."
        ),
        helper_text="Thresholds and testing.",
    ),
    BriefPrompt(
        title="Restricted Payments",
        question=(
            "Summarize the restricted payments framework, including baskets, "
            "builder capacity, and key conditions."
        ),
        helper_text="Capacity and conditions.",
    ),
    BriefPrompt(
        title="Incremental Debt",
        question=(
            "How much incremental debt may be incurred, and what are the main "
            "ratio-based, fixed amount, or free-and-clear components?"
        ),
        helper_text="Incremental capacity.",
    ),
)

SUGGESTED_QUESTIONS: tuple[SuggestedQuestion, ...] = (
    SuggestedQuestion(
        label="Describe the credit facilities",
        prompt=(
            "Describe the credit facilities, including the facility amounts, "
            "pricing/margin/interest rate, maturity, facility types, borrower, "
            "guarantors or obligors."
        ),
    ),
    SuggestedQuestion(
        label="Summarize all key credit provisions",
        prompt=(
            "Provide a structured summary of the key credit provisions in this agreement. "
            "Cover: (1) facility types, sizes, and maturity; (2) pricing and applicable margins; "
            "(3) financial maintenance covenants and any equity cure rights; "
            "(4) key negative covenants including debt capacity, liens, and restricted payments; "
            "(5) events of default. Cite section references for each item."
        ),
    ),
    SuggestedQuestion(
        label="What are the maintenance covenants?",
        prompt=(
            "What are the maintenance covenants, including the test levels, "
            "step-downs, testing cadence, applicable entities, and any cure rights?"
        ),
    ),
    SuggestedQuestion(
        label="How much incremental debt can the borrower incur?",
        prompt=(
            "How much incremental debt can the borrower incur, including any fixed "
            "amount baskets, ratio-based capacity, free-and-clear capacity, and key conditions?"
        ),
    ),
    SuggestedQuestion(
        label="Describe the restricted payments basket",
        prompt=(
            "Describe the restricted payments basket, including starter baskets, "
            "builder or available amount capacity, grower concepts, and the main conditions."
        ),
    ),
    SuggestedQuestion(
        label="What banks are involved in this facility?",
        prompt=(
            "What banks are involved in this facility? Identify the administrative "
            "agent, arrangers, bookrunners, lenders, issuing banks, and any lender "
            "group or facility allocations if available. If allocations are not stated, say so clearly."
        ),
    ),
)


def build_demo_brief(
    document: ProcessedDocument,
    provider: LLMProvider,
    *,
    prompts: Sequence[BriefPrompt] = DEFAULT_BRIEF_PROMPTS,
    progress_callback: BriefProgressCallback | None = None,
) -> list[BriefSection]:
    """Generate a concise demo brief from a processed document.

    A single QAEngine is created for the full run so that preamble context
    is injected consistently and engine setup overhead is paid once.
    """
    sections: list[BriefSection] = []

    qa_engine = QAEngine(document.retriever, provider)
    if document.preamble_text is not None:
        qa_engine.set_preamble(
            document.preamble_text,
            page_numbers=document.preamble_page_numbers,
        )

    for index, prompt in enumerate(prompts, start=1):
        _progress(
            progress_callback,
            f"Generating {prompt.title.lower()}...",
            index / max(len(prompts), 1),
        )
        response = qa_engine.ask(prompt.question, document.document_id)
        sections.append(
            BriefSection(
                title=prompt.title,
                helper_text=prompt.helper_text,
                question=prompt.question,
                answer=response.answer,
                confidence=response.confidence,
                sources=response.sources,
            )
        )

    _progress(progress_callback, "Demo brief ready.", 1.0)
    return sections


def _progress(
    callback: BriefProgressCallback | None,
    label: str,
    progress: float,
) -> None:
    """Fire the progress callback if one was provided."""
    if callback is not None:
        callback(label, progress)
