"""Conversational Q&A engine for credit agreement analysis.

Wires the hybrid retriever to the LLM provider, managing context
assembly, conversation history, response parsing, and source citations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from credit_analyzer.config import (
    QA_MAX_CONTEXT_CHUNKS,
    QA_MAX_GENERATION_TOKENS,
    QA_MAX_HISTORY_TURNS,
    QA_SECTION_TYPES_EXCLUDE,
)
from credit_analyzer.generation.prompts import (
    QA_SYSTEM_PROMPT,
    REFORMULATION_SYSTEM_PROMPT,
    ConversationTurn,
    build_context_prompt,
    build_reformulation_prompt,
)
from credit_analyzer.generation.response_parser import (
    ConfidenceLevel,
    SourceCitation,
    citations_from_chunks,
    enrich_citations,
    extract_answer_body,
    parse_confidence,
    parse_sources_from_llm,
)
from credit_analyzer.llm.base import LLMProvider, LLMResponse
from credit_analyzer.retrieval.hybrid_retriever import (
    HybridChunk,
    HybridRetriever,
    RetrievalResult,
)

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

    def ask(self, question: str, document_id: str) -> QAResponse:
        """Ask a question about a specific credit agreement.

        If conversation history exists, the question may be reformulated
        to produce a better retrieval query (e.g. resolving pronouns or
        implicit references to prior answers).

        Args:
            question: The user's question.
            document_id: The document collection to query against.

        Returns:
            A QAResponse with the answer, citations, and confidence.
        """
        retrieval_query = self._maybe_reformulate(question)

        result: RetrievalResult = self._retriever.retrieve(
            query=retrieval_query,
            document_id=document_id,
            top_k=self._max_chunks,
            section_types_exclude=self._section_types_exclude,
        )

        recent_history = self._history[-self._max_history :]

        user_prompt = build_context_prompt(
            chunks=result.chunks,
            definitions=result.injected_definitions,
            history=recent_history,
            question=question,
        )

        llm_response: LLMResponse = self._llm.complete(
            system_prompt=QA_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=self._max_gen_tokens,
        )

        raw_text = llm_response.text
        answer_body = extract_answer_body(raw_text)
        confidence = parse_confidence(raw_text)
        raw_citations = parse_sources_from_llm(raw_text)
        citations = enrich_citations(raw_citations, result.chunks)

        if not citations:
            citations = citations_from_chunks(result.chunks)

        self._history.append(
            ConversationTurn(question=question, answer=answer_body)
        )

        return QAResponse(
            answer=answer_body,
            sources=citations,
            confidence=confidence,
            retrieved_chunks=result.chunks,
            llm_response=llm_response,
        )

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
