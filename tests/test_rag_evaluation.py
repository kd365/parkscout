"""
RAG Evaluation Test Suite for ParkScout

Uses LLM-as-Judge (Claude) to evaluate RAG quality on park-related queries.
Tests run with mock context/answers so they do NOT require Ollama or ChromaDB.

Run with: pytest tests/test_rag_evaluation.py -v -m evaluation
"""

import pytest
from unittest.mock import patch, MagicMock

from api.services.rag_evaluator import (
    evaluate_faithfulness,
    evaluate_relevance,
    evaluate_context_precision,
    run_evaluation,
    clear_cache,
    _parse_score,
)


# ============================================================
# TEST CASES - parks-related queries with mock data
# ============================================================

EVAL_TEST_CASES = [
    {
        "id": "playground",
        "question": "Which parks have playgrounds for toddlers?",
        "context_docs": [
            "Burke Lake Park: Features a large playground with toddler area, "
            "swings, climbing structures. Also has a carousel, mini-train, and "
            "fishing pier. Restrooms available. Best for: families with young children.",
            "Clemyjontri Park: Fully accessible playground designed for children "
            "of all abilities. Includes swings, slides, and a carousel. Restrooms "
            "on site. Best for: toddlers, children with disabilities.",
        ],
        "answer": (
            "For toddlers, I recommend Clemyjontri Park which has a fully accessible "
            "playground designed for children of all abilities with swings and slides. "
            "Burke Lake Park is another great option with a dedicated toddler area "
            "in its playground, plus a carousel and mini-train."
        ),
        "thresholds": {"faithfulness": 0.7, "relevance": 0.7, "context_precision": 0.7},
    },
    {
        "id": "dog_friendly",
        "question": "Where can I take my dog off-leash?",
        "context_docs": [
            "South Run District Park: Off-leash dog area, trails, rec center. "
            "Dog area is fenced with water stations. Best for: dog owners, runners.",
            "Baron Cameron Park: Fenced off-leash dog park, sports fields, "
            "playground. Dog area separated into large and small dog sections. "
            "Best for: dog owners, sports enthusiasts.",
        ],
        "answer": (
            "There are two great off-leash options in Fairfax County. South Run "
            "District Park has a fenced off-leash dog area with water stations. "
            "Baron Cameron Park also has a fenced dog park with separate sections "
            "for large and small dogs."
        ),
        "thresholds": {"faithfulness": 0.7, "relevance": 0.7, "context_precision": 0.7},
    },
    {
        "id": "weather_aware",
        "question": "What parks are good to visit on a rainy day?",
        "context_docs": [
            "Spring Hill Recreation Center: Indoor pool, gym, community rooms. "
            "Open year-round. Best for: rainy days, winter activities.",
            "Burke Lake Park: Outdoor trails, fishing pier, playground, carousel. "
            "Mostly outdoor activities. Best for: sunny day outings.",
        ],
        "answer": (
            "On a rainy day, I suggest Spring Hill Recreation Center which offers "
            "indoor facilities including a pool, gym, and community rooms that are "
            "open year-round. Burke Lake Park is mostly outdoors, so it is better "
            "suited for clear weather."
        ),
        "thresholds": {"faithfulness": 0.7, "relevance": 0.7, "context_precision": 0.6},
    },
    {
        "id": "hiking_trails",
        "question": "What are the best parks for hiking?",
        "context_docs": [
            "Great Falls Park: 15 miles of hiking trails with views of the "
            "Potomac River and waterfalls. Trails range from easy to difficult. "
            "Restrooms at visitor center. Best for: hiking, nature photography.",
            "Huntley Meadows Park: Boardwalk trail through wetlands, 1.5 miles. "
            "Wildlife observation areas. Best for: birdwatching, easy walks.",
        ],
        "answer": (
            "For hiking, Great Falls Park is outstanding with 15 miles of trails "
            "ranging from easy to difficult, featuring views of the Potomac River "
            "and waterfalls. For an easier option, Huntley Meadows Park has a "
            "1.5-mile boardwalk trail through wetlands with wildlife viewing."
        ),
        "thresholds": {"faithfulness": 0.7, "relevance": 0.7, "context_precision": 0.7},
    },
    {
        "id": "picnic_birthday",
        "question": "Where can I host an outdoor birthday party with a picnic area?",
        "context_docs": [
            "Lake Fairfax Park: Picnic shelters available for reservation, "
            "water park, carousel, campground. Shelters accommodate 20-50 people. "
            "Restrooms and parking nearby. Best for: birthday parties, group events.",
            "Lake Accotink Park: Picnic areas, boat rentals, mini golf, carousel. "
            "Shelters can be reserved for parties. Best for: family gatherings.",
        ],
        "answer": (
            "For a birthday party, Lake Fairfax Park is an excellent choice with "
            "reservable picnic shelters that accommodate 20-50 people, plus a water "
            "park and carousel for entertainment. Lake Accotink Park is another "
            "option with picnic areas and party shelter reservations, along with "
            "mini golf and boat rentals."
        ),
        "thresholds": {"faithfulness": 0.7, "relevance": 0.7, "context_precision": 0.7},
    },
]


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture(autouse=True)
def clear_eval_cache():
    """Clear the evaluation cache before each test."""
    clear_cache()
    yield
    clear_cache()


def _make_mock_llm_response(score: float):
    """Create a mock LLM response object returning the given score."""
    mock_response = MagicMock()
    mock_response.content = str(score)
    return mock_response


# ============================================================
# UNIT TESTS - score parsing
# ============================================================

class TestScoreParsing:
    """Test the score extraction logic."""

    def test_parse_plain_number(self):
        assert _parse_score("0.85") == 0.85

    def test_parse_number_with_text(self):
        assert _parse_score("The score is 0.9 based on analysis.") == 0.9

    def test_parse_returns_zero_for_garbage(self):
        assert _parse_score("no numbers here") == 0.0

    def test_parse_ignores_out_of_range(self):
        assert _parse_score("Score: 1.5") == 0.0

    def test_parse_handles_one(self):
        assert _parse_score("1.0") == 1.0

    def test_parse_handles_zero(self):
        assert _parse_score("0.0") == 0.0


# ============================================================
# MOCK-BASED EVALUATION TESTS (no real API calls)
# ============================================================

@pytest.mark.evaluation
class TestEvaluationWithMocks:
    """Test evaluation functions with mocked LLM responses.

    These tests verify the evaluation logic works correctly
    without making real API calls.
    """

    @pytest.mark.parametrize("case", EVAL_TEST_CASES, ids=[c["id"] for c in EVAL_TEST_CASES])
    def test_faithfulness_mock(self, case):
        """Each test case should get a faithfulness score via mocked judge."""
        mock_response = _make_mock_llm_response(0.85)
        with patch("api.services.rag_evaluator._get_judge_llm") as mock_llm:
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_response
            mock_llm.return_value.__or__ = lambda self, other: mock_chain
            # Patch the chain directly via prompt | llm
            with patch("api.services.rag_evaluator.ChatPromptTemplate") as mock_prompt:
                mock_prompt.from_messages.return_value.__or__ = MagicMock(
                    return_value=mock_chain
                )
                context = "\n\n---\n\n".join(case["context_docs"])
                score = evaluate_faithfulness(case["question"], context, case["answer"])
                assert 0.0 <= score <= 1.0

    @pytest.mark.parametrize("case", EVAL_TEST_CASES, ids=[c["id"] for c in EVAL_TEST_CASES])
    def test_relevance_mock(self, case):
        """Each test case should get a relevance score via mocked judge."""
        mock_response = _make_mock_llm_response(0.90)
        with patch("api.services.rag_evaluator._get_judge_llm"):
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_response
            with patch("api.services.rag_evaluator.ChatPromptTemplate") as mock_prompt:
                mock_prompt.from_messages.return_value.__or__ = MagicMock(
                    return_value=mock_chain
                )
                score = evaluate_relevance(case["question"], case["answer"])
                assert 0.0 <= score <= 1.0

    @pytest.mark.parametrize("case", EVAL_TEST_CASES, ids=[c["id"] for c in EVAL_TEST_CASES])
    def test_context_precision_mock(self, case):
        """Each test case should get a context precision score via mocked judge."""
        mock_response = _make_mock_llm_response(0.80)
        with patch("api.services.rag_evaluator._get_judge_llm"):
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_response
            with patch("api.services.rag_evaluator.ChatPromptTemplate") as mock_prompt:
                mock_prompt.from_messages.return_value.__or__ = MagicMock(
                    return_value=mock_chain
                )
                context = "\n\n---\n\n".join(case["context_docs"])
                score = evaluate_context_precision(case["question"], context)
                assert 0.0 <= score <= 1.0

    def test_run_evaluation_mock(self):
        """run_evaluation should return all three metrics plus average."""
        mock_response = _make_mock_llm_response(0.85)
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response

        with patch("api.services.rag_evaluator._get_judge_llm"):
            with patch("api.services.rag_evaluator.ChatPromptTemplate") as mock_prompt:
                mock_prompt.from_messages.return_value.__or__ = MagicMock(
                    return_value=mock_chain
                )
                case = EVAL_TEST_CASES[0]
                result = run_evaluation(
                    case["question"], case["context_docs"], case["answer"]
                )

                assert "faithfulness" in result
                assert "relevance" in result
                assert "context_precision" in result
                assert "average" in result
                assert "question" in result
                assert 0.0 <= result["average"] <= 1.0


# ============================================================
# LIVE EVALUATION TESTS (require ANTHROPIC_API_KEY)
# ============================================================

@pytest.mark.evaluation
class TestLiveEvaluation:
    """Run actual LLM-as-Judge evaluations against test cases.

    These tests call the Claude API and require ANTHROPIC_API_KEY.
    Skip automatically if the key is not set.
    """

    @pytest.fixture(autouse=True)
    def skip_without_api_key(self):
        import os
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set - skipping live evaluation")

    @pytest.mark.parametrize("case", EVAL_TEST_CASES, ids=[c["id"] for c in EVAL_TEST_CASES])
    def test_individual_case_scores(self, case):
        """Each test case should meet its individual quality thresholds."""
        result = run_evaluation(
            case["question"], case["context_docs"], case["answer"]
        )

        thresholds = case["thresholds"]
        assert result["faithfulness"] >= thresholds["faithfulness"], (
            f"Faithfulness {result['faithfulness']:.2f} < {thresholds['faithfulness']} "
            f"for case '{case['id']}'"
        )
        assert result["relevance"] >= thresholds["relevance"], (
            f"Relevance {result['relevance']:.2f} < {thresholds['relevance']} "
            f"for case '{case['id']}'"
        )
        assert result["context_precision"] >= thresholds["context_precision"], (
            f"Context precision {result['context_precision']:.2f} < "
            f"{thresholds['context_precision']} for case '{case['id']}'"
        )

    def test_average_scores_meet_minimum_thresholds(self):
        """Overall average across all test cases should meet minimum quality bar.

        Minimum thresholds:
        - Faithfulness average >= 0.7
        - Relevance average >= 0.7
        - Context precision average >= 0.6
        """
        all_results = []
        for case in EVAL_TEST_CASES:
            result = run_evaluation(
                case["question"], case["context_docs"], case["answer"]
            )
            all_results.append(result)

        n = len(all_results)
        avg_faithfulness = sum(r["faithfulness"] for r in all_results) / n
        avg_relevance = sum(r["relevance"] for r in all_results) / n
        avg_context_precision = sum(r["context_precision"] for r in all_results) / n

        print("\n--- RAG Evaluation Summary ---")
        print(f"  Faithfulness avg:      {avg_faithfulness:.3f} (threshold: 0.7)")
        print(f"  Relevance avg:         {avg_relevance:.3f} (threshold: 0.7)")
        print(f"  Context Precision avg: {avg_context_precision:.3f} (threshold: 0.6)")

        assert avg_faithfulness >= 0.7, (
            f"Average faithfulness {avg_faithfulness:.3f} < 0.7"
        )
        assert avg_relevance >= 0.7, (
            f"Average relevance {avg_relevance:.3f} < 0.7"
        )
        assert avg_context_precision >= 0.6, (
            f"Average context precision {avg_context_precision:.3f} < 0.6"
        )


# ============================================================
# CACHING TESTS
# ============================================================

@pytest.mark.evaluation
class TestEvaluationCaching:
    """Verify that the caching mechanism works correctly."""

    def test_cache_returns_same_result(self):
        """Calling the same evaluation twice should use the cache."""
        mock_response = _make_mock_llm_response(0.75)
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response

        with patch("api.services.rag_evaluator._get_judge_llm"):
            with patch("api.services.rag_evaluator.ChatPromptTemplate") as mock_prompt:
                mock_prompt.from_messages.return_value.__or__ = MagicMock(
                    return_value=mock_chain
                )
                score1 = evaluate_relevance("test question", "test answer")
                score2 = evaluate_relevance("test question", "test answer")

                assert score1 == score2
                # The chain should only have been invoked once (second call uses cache)
                assert mock_chain.invoke.call_count == 1

    def test_clear_cache_works(self):
        """clear_cache should reset the cache."""
        mock_response = _make_mock_llm_response(0.75)
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response

        with patch("api.services.rag_evaluator._get_judge_llm"):
            with patch("api.services.rag_evaluator.ChatPromptTemplate") as mock_prompt:
                mock_prompt.from_messages.return_value.__or__ = MagicMock(
                    return_value=mock_chain
                )
                evaluate_relevance("test question", "test answer")
                clear_cache()
                evaluate_relevance("test question", "test answer")

                # Should invoke twice since cache was cleared
                assert mock_chain.invoke.call_count == 2


# ============================================================
# RUN CONFIGURATION
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "evaluation"])
