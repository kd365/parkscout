"""
RAG System Testing Suite for Parks Finder

Tests cover:
1. Data quality - verify parks loaded correctly
2. Retrieval accuracy - right parks returned for queries
3. Response quality - LLM gives useful answers
4. Performance - response times acceptable
5. Edge cases - handles unusual inputs gracefully
"""
import json
import time
import pytest
from pathlib import Path

# Test configuration
DATA_FILE = Path(__file__).parent.parent / "source_data/fairfax_parks.json"
DB_PATH = Path(__file__).parent.parent / "db/chroma_parks"

# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture(scope="module")
def parks_data():
    """Load parks JSON data."""
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

@pytest.fixture(scope="module")
def rag_chain():
    """Initialize the RAG chain (reused across tests)."""
    from langchain_chroma import Chroma
    from langchain_ollama import OllamaEmbeddings, OllamaLLM
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser

    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    chroma_db = Chroma(persist_directory=str(DB_PATH), embedding_function=embeddings)
    retriever = chroma_db.as_retriever()

    llm = OllamaLLM(model="llama3.2:1b")
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a Fairfax County parks guide. Recommend parks based on the data provided."),
        ("user", "Parks data:\n{context}\n\nQuestion: {question}")
    ])

    def format_docs(docs):
        return "\n\n---\n\n".join(doc.page_content for doc in docs)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain

@pytest.fixture(scope="module")
def retriever_only():
    """Just the retriever without LLM (for faster tests)."""
    from langchain_chroma import Chroma
    from langchain_ollama import OllamaEmbeddings

    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    chroma_db = Chroma(persist_directory=str(DB_PATH), embedding_function=embeddings)
    return chroma_db.as_retriever()


# ============================================================
# 1. DATA QUALITY TESTS
# ============================================================

class TestDataQuality:
    """Verify the parks data is complete and well-formed."""

    def test_parks_file_exists(self):
        """Data file should exist."""
        assert DATA_FILE.exists(), f"Parks data not found at {DATA_FILE}"

    def test_parks_count_minimum(self, parks_data):
        """Should have a reasonable number of parks."""
        assert len(parks_data) >= 50, f"Only {len(parks_data)} parks - expected 50+"

    def test_required_fields_present(self, parks_data):
        """Each park should have required fields."""
        required = ["park_name", "amenities", "best_for"]
        for park in parks_data[:10]:  # Sample first 10
            for field in required:
                assert field in park, f"Park missing {field}: {park.get('park_name', 'Unknown')}"

    def test_amenities_structure(self, parks_data):
        """Amenities should have expected subfields."""
        amenity_fields = ["playground", "restrooms", "trails", "dog_friendly"]
        for park in parks_data[:10]:
            amenities = park.get("amenities", {})
            for field in amenity_fields:
                assert field in amenities, f"Missing amenities.{field} in {park['park_name']}"

    def test_no_empty_park_names(self, parks_data):
        """All parks should have names."""
        for park in parks_data:
            assert park.get("park_name"), "Found park with empty name"

    def test_database_exists(self):
        """ChromaDB should exist after ingest."""
        assert DB_PATH.exists(), f"ChromaDB not found at {DB_PATH}"


# ============================================================
# 2. RETRIEVAL ACCURACY TESTS
# ============================================================

class TestRetrievalAccuracy:
    """Test that the right parks are retrieved for queries."""

    def test_playground_query_returns_parks_with_playgrounds(self, retriever_only):
        """Query about playgrounds should return parks that have them."""
        docs = retriever_only.invoke("parks with playgrounds for kids")
        assert len(docs) > 0, "No results for playground query"

        # At least one result should mention playground
        contents = [doc.page_content.lower() for doc in docs]
        has_playground = any("playground" in c for c in contents)
        assert has_playground, "Playground query didn't return parks with playgrounds"

    def test_dog_park_query(self, retriever_only):
        """Query about dogs should return dog-friendly parks."""
        docs = retriever_only.invoke("where can I take my dog off leash")
        assert len(docs) > 0, "No results for dog park query"

        contents = [doc.page_content.lower() for doc in docs]
        has_dog = any("dog" in c for c in contents)
        assert has_dog, "Dog query didn't return dog-friendly parks"

    def test_carousel_query(self, retriever_only):
        """Query about carousel should return parks with carousels."""
        docs = retriever_only.invoke("parks with carousel")
        assert len(docs) > 0, "No results for carousel query"

        contents = [doc.page_content.lower() for doc in docs]
        has_carousel = any("carousel" in c for c in contents)
        assert has_carousel, "Carousel query didn't return parks with carousels"

    def test_fishing_query(self, retriever_only):
        """Query about fishing should return appropriate parks."""
        docs = retriever_only.invoke("where can I go fishing")
        assert len(docs) > 0, "No results for fishing query"

        contents = [doc.page_content.lower() for doc in docs]
        has_fishing = any("fishing" in c or "fish" in c for c in contents)
        assert has_fishing, "Fishing query didn't return fishing parks"

    def test_retriever_returns_multiple_results(self, retriever_only):
        """Retriever should return multiple relevant results."""
        docs = retriever_only.invoke("family friendly parks")
        assert len(docs) >= 2, f"Expected 2+ results, got {len(docs)}"


# ============================================================
# 3. RESPONSE QUALITY TESTS (require LLM)
# ============================================================

class TestResponseQuality:
    """Test that LLM responses are helpful and accurate."""

    @pytest.mark.slow
    def test_response_mentions_park_names(self, rag_chain):
        """Response should mention actual park names."""
        response = rag_chain.invoke("What parks have playgrounds?")
        assert len(response) > 50, "Response too short"
        # Should mention "Park" somewhere
        assert "park" in response.lower(), "Response doesn't mention any parks"

    @pytest.mark.slow
    def test_response_compares_multiple_parks(self, rag_chain):
        """System prompt asks to compare at least 2 parks."""
        response = rag_chain.invoke("Where should I take my toddler?")
        # Look for comparison language or multiple park mentions
        words = response.lower()
        has_comparison = any(w in words for w in ["also", "another", "alternatively", "both", "either"])
        assert has_comparison or words.count("park") >= 2, "Response doesn't compare multiple parks"

    @pytest.mark.slow
    def test_response_includes_amenities(self, rag_chain):
        """Response should mention relevant amenities."""
        response = rag_chain.invoke("Parks with trails for hiking")
        assert "trail" in response.lower(), "Response doesn't mention trails"


# ============================================================
# 4. PERFORMANCE TESTS
# ============================================================

class TestPerformance:
    """Test response times are acceptable."""

    def test_retrieval_speed(self, retriever_only):
        """Retrieval should be fast (under 2 seconds)."""
        start = time.time()
        docs = retriever_only.invoke("playground for kids")
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Retrieval took {elapsed:.1f}s - too slow"

    @pytest.mark.slow
    def test_full_chain_speed(self, rag_chain):
        """Full RAG chain should complete in reasonable time."""
        start = time.time()
        response = rag_chain.invoke("parks with water activities")
        elapsed = time.time() - start
        # LLM inference takes time, allow up to 30 seconds
        assert elapsed < 30.0, f"Full chain took {elapsed:.1f}s - too slow"
        print(f"\nFull chain response time: {elapsed:.1f}s")


# ============================================================
# 5. EDGE CASE TESTS
# ============================================================

class TestEdgeCases:
    """Test handling of unusual inputs."""

    def test_empty_query(self, retriever_only):
        """Should handle empty query gracefully."""
        try:
            docs = retriever_only.invoke("")
            # Either returns results or empty list, but shouldn't crash
            assert isinstance(docs, list)
        except Exception as e:
            pytest.fail(f"Empty query caused error: {e}")

    def test_very_long_query(self, retriever_only):
        """Should handle very long queries."""
        long_query = "playground " * 100
        docs = retriever_only.invoke(long_query)
        assert isinstance(docs, list)

    def test_special_characters(self, retriever_only):
        """Should handle special characters in query."""
        docs = retriever_only.invoke("parks & playgrounds (for kids!)")
        assert isinstance(docs, list)

    def test_nonexistent_amenity(self, retriever_only):
        """Query for non-existent amenity should still return results."""
        docs = retriever_only.invoke("parks with roller coasters")
        # Should return something (maybe not relevant, but not crash)
        assert isinstance(docs, list)


# ============================================================
# RUN CONFIGURATION
# ============================================================

if __name__ == "__main__":
    # Run with: pytest tests/test_rag.py -v
    # Run fast tests only: pytest tests/test_rag.py -v -m "not slow"
    pytest.main([__file__, "-v"])
