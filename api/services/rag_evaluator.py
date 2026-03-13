"""
RAG Evaluation Service for ParkScout

Uses Claude (via langchain-anthropic) as an LLM-as-Judge to evaluate
RAG pipeline quality across three metrics:
- Faithfulness: Does the answer match the retrieved context?
- Answer Relevance: Does the answer address the question?
- Context Precision: Did retrieval return the right documents?
"""

import hashlib
import os
from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate


# Simple dict-based cache to reduce API costs on repeated evaluations
_eval_cache: dict[str, float] = {}


def _cache_key(metric: str, *args: str) -> str:
    """Generate a cache key from the metric name and input strings."""
    combined = f"{metric}:{'||'.join(args)}"
    return hashlib.sha256(combined.encode()).hexdigest()


def _get_judge_llm() -> ChatAnthropic:
    """Initialize the judge LLM."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is required for RAG evaluation"
        )
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=api_key,
        temperature=0.0,
        max_tokens=256,
    )


def _parse_score(response_text: str) -> float:
    """Extract a float score from the judge LLM response.

    Expects the response to contain a number between 0.0 and 1.0.
    Falls back to 0.0 if parsing fails.
    """
    text = response_text.strip()
    # Try to find a decimal number in the response
    for token in text.replace("\n", " ").split():
        token = token.strip(".,;:()")
        try:
            score = float(token)
            if 0.0 <= score <= 1.0:
                return score
        except ValueError:
            continue
    return 0.0


def evaluate_faithfulness(question: str, context: str, answer: str) -> float:
    """Evaluate whether the answer is faithful to the retrieved context.

    Returns a score from 0.0 (hallucinated) to 1.0 (fully grounded in context).
    """
    key = _cache_key("faithfulness", question, context, answer)
    if key in _eval_cache:
        return _eval_cache[key]

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an evaluation judge. Score how faithful the answer is to the "
            "provided context. A faithful answer only contains information that can "
            "be found in or directly inferred from the context. "
            "Respond with ONLY a single decimal number between 0.0 and 1.0."
        )),
        ("user", (
            "Question: {question}\n\n"
            "Context:\n{context}\n\n"
            "Answer: {answer}\n\n"
            "Faithfulness score (0.0 to 1.0):"
        )),
    ])

    llm = _get_judge_llm()
    chain = prompt | llm
    result = chain.invoke({
        "question": question,
        "context": context,
        "answer": answer,
    })
    score = _parse_score(result.content)
    _eval_cache[key] = score
    return score


def evaluate_relevance(question: str, answer: str) -> float:
    """Evaluate whether the answer is relevant to the question asked.

    Returns a score from 0.0 (irrelevant) to 1.0 (directly addresses the question).
    """
    key = _cache_key("relevance", question, answer)
    if key in _eval_cache:
        return _eval_cache[key]

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an evaluation judge. Score how relevant the answer is to the "
            "question. A relevant answer directly addresses what was asked and "
            "provides useful information. "
            "Respond with ONLY a single decimal number between 0.0 and 1.0."
        )),
        ("user", (
            "Question: {question}\n\n"
            "Answer: {answer}\n\n"
            "Relevance score (0.0 to 1.0):"
        )),
    ])

    llm = _get_judge_llm()
    chain = prompt | llm
    result = chain.invoke({
        "question": question,
        "answer": answer,
    })
    score = _parse_score(result.content)
    _eval_cache[key] = score
    return score


def evaluate_context_precision(question: str, context: str) -> float:
    """Evaluate whether the retrieved context is relevant to the question.

    Returns a score from 0.0 (irrelevant context) to 1.0 (highly relevant context).
    """
    key = _cache_key("context_precision", question, context)
    if key in _eval_cache:
        return _eval_cache[key]

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an evaluation judge. Score how relevant the retrieved context "
            "documents are to the question. High precision means the retrieved "
            "documents contain information needed to answer the question. "
            "Respond with ONLY a single decimal number between 0.0 and 1.0."
        )),
        ("user", (
            "Question: {question}\n\n"
            "Retrieved Context:\n{context}\n\n"
            "Context precision score (0.0 to 1.0):"
        )),
    ])

    llm = _get_judge_llm()
    chain = prompt | llm
    result = chain.invoke({
        "question": question,
        "context": context,
    })
    score = _parse_score(result.content)
    _eval_cache[key] = score
    return score


def run_evaluation(
    question: str, context_docs: List[str], answer: str
) -> dict:
    """Run all three evaluation metrics and return a results dict.

    Args:
        question: The user's query.
        context_docs: List of retrieved context document strings.
        answer: The generated answer from the RAG pipeline.

    Returns:
        Dict with keys: faithfulness, relevance, context_precision, and
        an overall average score.
    """
    combined_context = "\n\n---\n\n".join(context_docs)

    faithfulness = evaluate_faithfulness(question, combined_context, answer)
    relevance = evaluate_relevance(question, answer)
    context_precision = evaluate_context_precision(question, combined_context)

    avg = round((faithfulness + relevance + context_precision) / 3, 4)

    return {
        "question": question,
        "faithfulness": faithfulness,
        "relevance": relevance,
        "context_precision": context_precision,
        "average": avg,
    }


def clear_cache() -> None:
    """Clear the evaluation cache."""
    _eval_cache.clear()
