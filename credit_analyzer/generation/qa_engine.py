"""Conversational Q&A engine for credit agreement analysis.

Wires the hybrid retriever to the LLM provider, managing context
assembly, conversation history, response parsing, and source citations.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Generator, Sequence
from dataclasses import dataclass, field

from credit_analyzer.config import (
    QA_MAX_CONTEXT_CHUNKS,
    QA_MAX_GENERATION_TOKENS,
    QA_MAX_HISTORY_TURNS,
    QA_SECTION_TYPES_EXCLUDE,
)
from credit_analyzer.generation.prompts import (
    CITE_SOURCES_ADDENDUM,
    COMMENTARY_ADDENDUM,
    CONCISE_ADDENDUM,
    DEEP_ANALYSIS_ADDENDUM,
    QA_SYSTEM_PROMPT,
    REFORMULATION_SYSTEM_PROMPT,
    ConversationTurn,
    build_context_prompt,
    build_reformulation_prompt,
)
from credit_analyzer.generation.query_expansion import (
    expand_query as _expand_query,
)
from credit_analyzer.generation.query_expansion import (
    extract_needs_context as _extract_needs_context,
)
from credit_analyzer.generation.query_expansion import (
    merge_retrieval_results as _merge_retrieval_results,
)
from credit_analyzer.generation.query_expansion import (
    retrieve_multi_query as _retrieve_multi_query,
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
        cite_sources: bool = False,
        commentary: bool = False,
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
        if cite_sources:
            system_prompt += CITE_SOURCES_ADDENDUM
        if commentary:
            system_prompt += COMMENTARY_ADDENDUM

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
                _, follow_up = _extract_needs_context(raw_text)
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
        cite_sources: bool = False,
        commentary: bool = False,
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
        if cite_sources:
            system_prompt += CITE_SOURCES_ADDENDUM
        if commentary:
            system_prompt += COMMENTARY_ADDENDUM

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
        start = time.perf_counter()
        for token in self._llm.stream_complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=self._max_gen_tokens,
        ):
            full_text_parts.append(token)
            yield token
        duration = time.perf_counter() - start

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
        except Exception:  # Intentionally broad: best-effort reformulation must not crash Q&A
            logger.warning(
                "Reformulation failed, using original question",
                exc_info=True,
            )

        return question


# ---------------------------------------------------------------------------
# Multi-document comparison
# ---------------------------------------------------------------------------


@dataclass
class ComparisonResponse:
    """Result of a cross-document comparison query.

    Attributes:
        question: The original user question.
        per_document_answers: Mapping of document_id -> extracted answer text.
        per_document_chunks: Mapping of document_id -> retrieved chunks.
        synthesis: The synthesized comparison table/text.
        document_names: Mapping of document_id -> display name.
    """

    question: str
    per_document_answers: dict[str, str]
    per_document_chunks: dict[str, list[HybridChunk]]
    synthesis: str
    document_names: dict[str, str]


def compare(
    question: str,
    retrievers: dict[str, HybridRetriever],
    document_names: dict[str, str],
    llm: LLMProvider,
    *,
    preambles: dict[str, str | None] | None = None,
    max_context_chunks: int = QA_MAX_CONTEXT_CHUNKS,
    max_generation_tokens: int = QA_MAX_GENERATION_TOKENS,
    section_types_exclude: tuple[str, ...] = QA_SECTION_TYPES_EXCLUDE,
) -> ComparisonResponse:
    """Compare provisions across multiple documents.

    Fans the question out to each document's retriever, gets a per-document
    extraction answer from the LLM, then synthesizes a comparison table.
    """
    from concurrent.futures import ThreadPoolExecutor

    from credit_analyzer.generation.prompts import (
        COMPARISON_EXTRACTION_PROMPT,
        COMPARISON_SYNTHESIS_PROMPT,
    )

    preambles = preambles or {}

    # Phase 1: Retrieve from all documents in parallel
    queries = _expand_query(question)
    per_doc_results: dict[str, RetrievalResult] = {}

    def _retrieve_for_doc(doc_id: str) -> tuple[str, RetrievalResult]:
        retriever = retrievers[doc_id]
        result = _retrieve_multi_query(
            retriever, queries, doc_id,
            top_k=max_context_chunks,
            section_types_exclude=section_types_exclude,
        )
        return doc_id, result

    with ThreadPoolExecutor(max_workers=len(retrievers)) as pool:
        for doc_id, result in pool.map(
            _retrieve_for_doc, list(retrievers.keys()),
        ):
            per_doc_results[doc_id] = result

    # Phase 2: Extract answer per document (parallel LLM calls)
    per_doc_answers: dict[str, str] = {}
    per_doc_chunks: dict[str, list[HybridChunk]] = {}

    def _extract_for_doc(doc_id: str) -> tuple[str, str, list[HybridChunk]]:
        result = per_doc_results[doc_id]
        doc_name = document_names.get(doc_id, doc_id)
        preamble = preambles.get(doc_id)

        user_prompt, _ = build_context_prompt(
            chunks=result.chunks,
            definitions=result.injected_definitions,
            history=[],
            question=question,
            preamble_text=preamble,
        )

        system_prompt = COMPARISON_EXTRACTION_PROMPT.format(
            document_name=doc_name,
        )

        resp = llm.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=max_generation_tokens,
        )
        return doc_id, resp.text.strip(), result.chunks

    with ThreadPoolExecutor(max_workers=len(per_doc_results)) as pool:
        for doc_id, answer, chunks in pool.map(
            _extract_for_doc, list(per_doc_results.keys()),
        ):
            per_doc_answers[doc_id] = answer
            per_doc_chunks[doc_id] = chunks

    # Phase 3: Synthesize comparison
    synthesis_parts: list[str] = []
    for doc_id, answer in per_doc_answers.items():
        doc_name = document_names.get(doc_id, doc_id)
        synthesis_parts.append(f"=== {doc_name} ===\n{answer}")

    synthesis_user_prompt = (
        f"QUESTION: {question}\n\n"
        + "\n\n".join(synthesis_parts)
    )

    synthesis_resp = llm.complete(
        system_prompt=COMPARISON_SYNTHESIS_PROMPT,
        user_prompt=synthesis_user_prompt,
        temperature=0.0,
        max_tokens=max_generation_tokens,
    )

    return ComparisonResponse(
        question=question,
        per_document_answers=per_doc_answers,
        per_document_chunks=per_doc_chunks,
        synthesis=synthesis_resp.text.strip(),
        document_names=dict(document_names),
    )
