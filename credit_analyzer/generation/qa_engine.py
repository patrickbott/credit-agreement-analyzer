"""Conversational Q&A engine for credit agreement analysis.

Wires the hybrid retriever to the LLM provider, managing context
assembly, conversation history, response parsing, and source citations.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Generator, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from credit_analyzer.config import (
    QA_MAX_CONTEXT_CHUNKS,
    QA_MAX_GENERATION_TOKENS,
    QA_MAX_HISTORY_TURNS,
    QA_SECTION_TYPES_EXCLUDE,
)
from credit_analyzer.generation.prompts import (
    CONCISE_ADDENDUM,
    DEEP_ANALYSIS_ADDENDUM,
    QA_SYSTEM_PROMPT,
    REFORMULATION_SYSTEM_PROMPT,
    ConversationTurn,
    build_context_prompt,
    build_reformulation_prompt,
)
from credit_analyzer.generation.response_parser import (
    ConfidenceLevel,
    InlineCitation,
    SourceCitation,
    build_citations_from_chunks,
    citations_from_chunks,
    extract_answer_body,
    parse_confidence,
)
from credit_analyzer.llm.base import LLMProvider, LLMResponse
from credit_analyzer.retrieval.hybrid_retriever import (
    HybridChunk,
    HybridRetriever,
    RetrievalResult,
    merge_multi_query_results,
)
from credit_analyzer.utils.text_cleaning import strip_markdown as _strip_markdown

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------


@dataclass
class QAResponse:
    """Response from the Q&A engine.

    Attributes:
        answer: The generated answer text.
        sources: Parsed source citations from the LLM response.
        confidence: Assessed confidence level.
        retrieved_chunks: The raw retrieved chunks (for debugging / UI).
        llm_response: The raw LLM response metadata.
    """

    answer: str
    sources: list[SourceCitation]
    confidence: ConfidenceLevel
    retrieved_chunks: list[HybridChunk]
    llm_response: LLMResponse
    inline_citations: list[InlineCitation] = field(default_factory=lambda: list[InlineCitation]())
    retrieval_rounds: int = 1


_DEEP_ANALYSIS_MAX_ROUNDS = 3
_NEEDS_CONTEXT_RE = re.compile(
    r"<needs_context>(.*?)</needs_context>", re.DOTALL,
)


def _extract_needs_context(text: str) -> tuple[str, str | None]:
    """Strip any <needs_context> tag and return (cleaned_text, follow_up_query).

    Returns the text with the tag removed and the follow-up query if found,
    or None if no tag is present.
    """
    match = _NEEDS_CONTEXT_RE.search(text)
    if match is None:
        return text, None
    cleaned = text[:match.start()].rstrip() + text[match.end():]
    return cleaned.strip(), match.group(1).strip()


def _merge_retrieval_results(
    existing: RetrievalResult,
    new: RetrievalResult,
    top_k: int,
) -> RetrievalResult:
    """Merge new retrieval results into existing, deduplicating by chunk ID."""
    seen_ids = {hc.chunk.chunk_id for hc in existing.chunks}
    merged_chunks = list(existing.chunks)
    for hc in new.chunks:
        if hc.chunk.chunk_id not in seen_ids and len(merged_chunks) < top_k:
            seen_ids.add(hc.chunk.chunk_id)
            merged_chunks.append(hc)
    merged_defs = {**existing.injected_definitions, **new.injected_definitions}
    return RetrievalResult(chunks=merged_chunks, injected_definitions=merged_defs)


# ---------------------------------------------------------------------------
# Multi-query retrieval helpers
# ---------------------------------------------------------------------------


def _expand_query(question: str) -> list[str]:
    """Generate additional retrieval queries from a question.

    Uses rule-based expansion to create complementary queries that search
    different aspects of the same question. This is cheaper than LLM-based
    expansion and catches cases where key terms appear in definitions,
    schedules, or different section types.

    Returns 1-3 queries (always includes the original).
    """
    queries = [question]
    question_lower = question.lower()

    # Extract key noun phrases that might be defined terms
    # Look for capitalized multi-word phrases (common in credit agreements)
    defined_term_pattern = re.compile(
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
    )
    terms = defined_term_pattern.findall(question)

    # Also catch fully capitalized terms like "SOFR" or "ABR"
    upper_terms = re.findall(r'\b([A-Z]{2,})\b', question)

    # Also detect common credit agreement terms in lowercase questions.
    # Maps lowercase phrases to their canonical defined-term form.
    _TERM_ALIASES: dict[str, str] = {
        "applicable margin": "Applicable Margin",
        "applicable rate": "Applicable Rate",
        "sofr spread": "Applicable Margin SOFR spread",
        "interest rate": "Applicable Rate interest rate",
        "pricing grid": "Applicable Rate pricing grid",
        "base rate": "Alternate Base Rate",
        "abr": "Alternate Base Rate ABR",
        "commitment fee": "Commitment Fee",
        "lc fee": "Letter of Credit Fee",
        "leverage ratio": "Total Net Leverage Ratio",
        "coverage ratio": "Fixed Charge Coverage Ratio",
        "ebitda": "Consolidated EBITDA",
        "consolidated ebitda": "Consolidated EBITDA",
        "available amount": "Available Amount",
        "permitted investments": "Permitted Investments",
        "permitted liens": "Permitted Liens",
        "permitted indebtedness": "Permitted Indebtedness",
        "change of control": "Change of Control",
        "required lenders": "Required Lenders",
        "net income": "Consolidated Net Income",
        "excess cash flow": "Excess Cash Flow",
    }
    alias_terms: list[str] = []
    for alias, canonical in _TERM_ALIASES.items():
        if alias in question_lower:
            alias_terms.append(canonical)

    # Build a definitions-focused query if we found potential defined terms
    all_terms = terms + upper_terms + alias_terms
    if all_terms:
        def_query = "definition " + " ".join(all_terms[:3])
        queries.append(def_query)

    # Build a broader structural query using key financial terms
    financial_keywords = {
        "margin", "spread", "rate", "pricing", "interest", "sofr", "libor",
        "abr", "floor", "grid", "step-down", "step-up",
        "leverage", "ratio", "covenant", "test", "threshold",
        "basket", "cap", "amount", "limit",
        "maturity", "amortization", "prepayment", "sweep",
        "dividend", "distribution", "restricted payment",
        "lien", "collateral", "security",
        "incremental", "accordion", "facility",
    }
    matched_keywords = [kw for kw in financial_keywords if kw in question_lower]

    if matched_keywords and len(queries) < 3:
        # Add a query that targets the likely section type
        broad_query = question + " " + " ".join(matched_keywords[:3])
        if broad_query != question:
            queries.append(broad_query)

    return queries[:3]  # Cap at 3 queries


def _retrieve_multi_query(
    retriever: HybridRetriever,
    queries: list[str],
    document_id: str,
    top_k: int,
    section_types_exclude: tuple[str, ...] | None = None,
) -> RetrievalResult:
    """Run multiple retrieval queries and merge results via round-robin.

    Uses round-robin interleaving so every query contributes proportionally,
    preventing dominant queries from crowding out niche results.
    """
    per_query_results: list[list[HybridChunk]] = []
    per_query_definitions: list[dict[str, str]] = []

    def _run(q: str) -> RetrievalResult:
        return retriever.retrieve(
            query=q,
            document_id=document_id,
            top_k=top_k,
            section_types_exclude=section_types_exclude,
        )

    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        results = list(pool.map(_run, queries))

    for result in results:
        per_query_results.append(result.chunks)
        per_query_definitions.append(result.injected_definitions)

    return merge_multi_query_results(
        per_query_results, per_query_definitions, top_k,
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class QAEngine:
    """Conversational Q&A engine for credit agreement analysis.

    Wires the hybrid retriever to the LLM provider, maintaining
    conversation history for follow-up questions and reformulating
    queries when context is needed from prior turns.
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        llm: LLMProvider,
        *,
        max_history_turns: int = QA_MAX_HISTORY_TURNS,
        max_context_chunks: int = QA_MAX_CONTEXT_CHUNKS,
        max_generation_tokens: int = QA_MAX_GENERATION_TOKENS,
        section_types_exclude: tuple[str, ...] = QA_SECTION_TYPES_EXCLUDE,
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._max_history = max_history_turns
        self._max_chunks = max_context_chunks
        self._max_gen_tokens = max_generation_tokens
        self._section_types_exclude = section_types_exclude
        self._history: list[ConversationTurn] = []
        self._preamble_text: str | None = None
        self._preamble_page_numbers: list[int] | None = None

    def set_preamble(
        self,
        text: str,
        page_numbers: Sequence[int] | None = None,
    ) -> None:
        """Set the preamble text to always inject as context.

        The preamble (recitals, title page) contains headline terms like
        borrower name, facility sizes, agent, and date.  It is injected
        into every query's context since it is typically < 1 page and
        relevant to most questions.

        Args:
            text: The preamble text from the document.
            page_numbers: Optional page numbers spanned by the preamble.
        """
        self._preamble_text = text.strip() if text.strip() else None
        self._preamble_page_numbers = list(page_numbers) if page_numbers else None

    def ask(
        self,
        question: str,
        document_id: str,
        *,
        deep_analysis: bool = False,
        concise: bool = False,
    ) -> QAResponse:
        """Ask a question about a specific credit agreement.

        If conversation history exists, the question may be reformulated
        to produce a better retrieval query (e.g. resolving pronouns or
        implicit references to prior answers).

        Args:
            question: The user's question.
            document_id: The document collection to query against.
            deep_analysis: When True, perform up to 3 retrieval rounds,
                re-retrieving when the LLM signals insufficient context.
            concise: When True, instruct the LLM to give shorter, more
                focused answers.

        Returns:
            A QAResponse with the answer, citations, and confidence.
        """
        retrieval_query = self._maybe_reformulate(question)

        queries = _expand_query(retrieval_query)
        result: RetrievalResult = _retrieve_multi_query(
            self._retriever,
            queries,
            document_id,
            top_k=self._max_chunks,
            section_types_exclude=self._section_types_exclude,
        )

        system_prompt = QA_SYSTEM_PROMPT
        if concise:
            system_prompt += CONCISE_ADDENDUM
        if deep_analysis:
            system_prompt += DEEP_ANALYSIS_ADDENDUM

        recent_history = self._history[-self._max_history :]
        retrieval_rounds = 1

        user_prompt, numbered_chunks = build_context_prompt(
            chunks=result.chunks,
            definitions=result.injected_definitions,
            history=recent_history,
            question=question,
            preamble_text=self._preamble_text,
            preamble_page_numbers=self._preamble_page_numbers,
        )

        llm_response: LLMResponse = self._llm.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=self._max_gen_tokens,
        )

        # Deep analysis: check for <needs_context> and re-retrieve
        if deep_analysis:
            raw_text = llm_response.text
            while retrieval_rounds < _DEEP_ANALYSIS_MAX_ROUNDS:
                cleaned, follow_up = _extract_needs_context(raw_text)
                if follow_up is None:
                    break
                logger.info(
                    "Deep analysis round %d: re-retrieving for '%s'",
                    retrieval_rounds + 1, follow_up,
                )
                follow_up_queries = _expand_query(follow_up)
                new_result = _retrieve_multi_query(
                    self._retriever,
                    follow_up_queries,
                    document_id,
                    top_k=self._max_chunks,
                    section_types_exclude=self._section_types_exclude,
                )
                result = _merge_retrieval_results(
                    result, new_result, self._max_chunks * 2,
                )
                retrieval_rounds += 1
                user_prompt, numbered_chunks = build_context_prompt(
                    chunks=result.chunks,
                    definitions=result.injected_definitions,
                    history=recent_history,
                    question=question,
                    preamble_text=self._preamble_text,
                    preamble_page_numbers=self._preamble_page_numbers,
                )
                # On the final allowed round, drop the addendum to force a
                # complete answer without another <needs_context> tag.
                final_prompt = system_prompt
                if retrieval_rounds >= _DEEP_ANALYSIS_MAX_ROUNDS:
                    final_prompt = QA_SYSTEM_PROMPT
                llm_response = self._llm.complete(
                    system_prompt=final_prompt,
                    user_prompt=user_prompt,
                    temperature=0.0,
                    max_tokens=self._max_gen_tokens,
                )
                raw_text = llm_response.text

        raw_text = llm_response.text
        # Strip any remaining <needs_context> tag from the final response
        raw_text, _ = _extract_needs_context(raw_text)
        answer_body = _strip_markdown(extract_answer_body(raw_text))
        confidence = parse_confidence(raw_text)
        citations = citations_from_chunks(result.chunks)
        inline_citations, answer_body = build_citations_from_chunks(
            answer_body, numbered_chunks,
        )

        self._history.append(
            ConversationTurn(question=question, answer=answer_body)
        )

        return QAResponse(
            answer=answer_body,
            sources=citations,
            confidence=confidence,
            retrieved_chunks=result.chunks,
            llm_response=llm_response,
            inline_citations=inline_citations,
            retrieval_rounds=retrieval_rounds,
        )

    def ask_stream(
        self,
        question: str,
        document_id: str,
        *,
        deep_analysis: bool = False,
        concise: bool = False,
    ) -> Generator[str | QAResponse, None, None]:
        """Stream an answer, yielding tokens then the final QAResponse.

        Yields str tokens as they arrive from the LLM, then yields a
        final QAResponse object with parsed citations and confidence.
        Callers should check isinstance() to distinguish tokens from
        the final response.

        When ``deep_analysis`` is True, preliminary retrieval rounds run
        synchronously (non-streamed) before the final answer is streamed.
        """
        retrieval_query = self._maybe_reformulate(question)

        queries = _expand_query(retrieval_query)
        result: RetrievalResult = _retrieve_multi_query(
            self._retriever,
            queries,
            document_id,
            top_k=self._max_chunks,
            section_types_exclude=self._section_types_exclude,
        )

        system_prompt = QA_SYSTEM_PROMPT
        if concise:
            system_prompt += CONCISE_ADDENDUM
        if deep_analysis:
            system_prompt += DEEP_ANALYSIS_ADDENDUM

        recent_history = self._history[-self._max_history:]
        retrieval_rounds = 1

        # Deep analysis: run non-streamed preliminary rounds to gather context
        if deep_analysis:
            while retrieval_rounds < _DEEP_ANALYSIS_MAX_ROUNDS:
                user_prompt, _numbered = build_context_prompt(
                    chunks=result.chunks,
                    definitions=result.injected_definitions,
                    history=recent_history,
                    question=question,
                    preamble_text=self._preamble_text,
                    preamble_page_numbers=self._preamble_page_numbers,
                )
                preliminary = self._llm.complete(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.0,
                    max_tokens=self._max_gen_tokens,
                )
                _, follow_up = _extract_needs_context(preliminary.text)
                if follow_up is None:
                    # First round was sufficient — stream the final answer
                    # with the same context (no addendum needed).
                    break
                logger.info(
                    "Deep analysis round %d: re-retrieving for '%s'",
                    retrieval_rounds + 1, follow_up,
                )
                follow_up_queries = _expand_query(follow_up)
                new_result = _retrieve_multi_query(
                    self._retriever,
                    follow_up_queries,
                    document_id,
                    top_k=self._max_chunks,
                    section_types_exclude=self._section_types_exclude,
                )
                result = _merge_retrieval_results(
                    result, new_result, self._max_chunks * 2,
                )
                retrieval_rounds += 1

        # Build final prompt (without addendum so the answer is clean)
        user_prompt, numbered_chunks = build_context_prompt(
            chunks=result.chunks,
            definitions=result.injected_definitions,
            history=recent_history,
            question=question,
            preamble_text=self._preamble_text,
            preamble_page_numbers=self._preamble_page_numbers,
        )

        # Stream tokens from LLM
        full_text_parts: list[str] = []
        start = __import__("time").perf_counter()
        for token in self._llm.stream_complete(
            system_prompt=QA_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=self._max_gen_tokens,
        ):
            full_text_parts.append(token)
            yield token
        duration = __import__("time").perf_counter() - start

        raw_text = "".join(full_text_parts)
        # Strip any lingering <needs_context> tag
        raw_text, _ = _extract_needs_context(raw_text)
        answer_body = _strip_markdown(extract_answer_body(raw_text))
        confidence = parse_confidence(raw_text)
        citations = citations_from_chunks(result.chunks)
        inline_citations, answer_body = build_citations_from_chunks(
            answer_body, numbered_chunks,
        )

        self._history.append(
            ConversationTurn(question=question, answer=answer_body)
        )

        yield QAResponse(
            answer=answer_body,
            sources=citations,
            confidence=confidence,
            retrieved_chunks=result.chunks,
            llm_response=LLMResponse(
                text=raw_text,
                tokens_used=0,
                model=self._llm.model_name(),
                duration_seconds=duration,
            ),
            inline_citations=inline_citations,
            retrieval_rounds=retrieval_rounds,
        )

    def add_history_turn(self, question: str, answer: str) -> None:
        """Append a historical turn to the conversation memory."""
        self._history.append(ConversationTurn(question=question, answer=answer))

    def clear_history(self) -> None:
        """Clear conversation history to start a fresh Q&A session."""
        self._history.clear()

    @property
    def history_length(self) -> int:
        """Return the number of conversation turns stored."""
        return len(self._history)

    def _maybe_reformulate(self, question: str) -> str:
        """Reformulate a follow-up question using conversation history.

        If there is no history, returns the question unchanged. Otherwise,
        asks the LLM to produce a standalone search query.

        Args:
            question: The user's raw question.

        Returns:
            A standalone retrieval query.
        """
        if not self._history:
            return question

        recent = self._history[-self._max_history :]
        user_prompt = build_reformulation_prompt(recent, question)

        try:
            resp = self._llm.complete(
                system_prompt=REFORMULATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
                max_tokens=100,
            )
            reformulated = resp.text.strip()
            if reformulated and len(reformulated) < 500:
                logger.debug(
                    "Reformulated '%s' -> '%s'", question, reformulated
                )
                return reformulated
        except Exception:
            logger.warning(
                "Reformulation failed, using original question",
                exc_info=True,
            )

        return question
