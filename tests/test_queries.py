"""
Manual test queries for validating RAG responses.

Run this to see actual responses for common use cases.
Usage: python tests/test_queries.py
"""
import sys
import time
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

from main import get_retriever, create_chain

# Test queries representing different user personas/needs
TEST_QUERIES = [
    # Mom with toddler use case
    {
        "query": "I have a 3 year old, where can we go that has a playground and restrooms?",
        "expected_mentions": ["playground", "restroom"],
        "persona": "Mom with toddler"
    },
    {
        "query": "Which parks have a carousel my kids would love?",
        "expected_mentions": ["carousel"],
        "persona": "Family seeking attractions"
    },
    # Dog owner use case
    {
        "query": "Where can I take my dog off-leash?",
        "expected_mentions": ["dog"],
        "persona": "Dog owner"
    },
    # Active recreation
    {
        "query": "I want to go hiking with nice trails",
        "expected_mentions": ["trail"],
        "persona": "Hiker"
    },
    {
        "query": "Parks with fishing near me",
        "expected_mentions": ["fish"],
        "persona": "Fishing enthusiast"
    },
    # Sports
    {
        "query": "Where can I play tennis or pickleball?",
        "expected_mentions": ["tennis", "pickleball"],
        "persona": "Tennis/Pickleball player"
    },
    # Special needs
    {
        "query": "Accessible playground for children with disabilities",
        "expected_mentions": ["accessible", "inclusive", "playground"],
        "persona": "Parent of child with disability"
    },
    # Water activities
    {
        "query": "Where can we go swimming or to a splash pad?",
        "expected_mentions": ["swim", "water", "splash"],
        "persona": "Summer fun seeker"
    },
]


def run_test_queries():
    """Run all test queries and evaluate responses."""
    print("=" * 60)
    print("  Parks Finder RAG - Test Query Suite")
    print("=" * 60)

    # Initialize chain once
    print("\nInitializing RAG chain...")
    retriever = get_retriever()
    chain = create_chain(retriever)
    print("Ready!\n")

    results = []

    for i, test in enumerate(TEST_QUERIES, 1):
        print(f"\n{'─' * 60}")
        print(f"Test {i}/{len(TEST_QUERIES)}: {test['persona']}")
        print(f"Query: {test['query']}")
        print(f"{'─' * 60}")

        start = time.time()
        try:
            response = chain.invoke(test['query'])
            elapsed = time.time() - start

            # Check for expected mentions
            response_lower = response.lower()
            found = [term for term in test['expected_mentions']
                    if term.lower() in response_lower]
            missing = [term for term in test['expected_mentions']
                      if term.lower() not in response_lower]

            # Determine pass/fail
            passed = len(found) > 0

            print(f"\nResponse ({elapsed:.1f}s):")
            print(f"{response[:500]}{'...' if len(response) > 500 else ''}")

            print(f"\n✓ Found: {found}" if found else "")
            print(f"✗ Missing: {missing}" if missing else "")
            print(f"\nResult: {'PASS ✓' if passed else 'FAIL ✗'}")

            results.append({
                "query": test['query'],
                "persona": test['persona'],
                "passed": passed,
                "time": elapsed,
                "found": found,
                "missing": missing
            })

        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            results.append({
                "query": test['query'],
                "persona": test['persona'],
                "passed": False,
                "error": str(e)
            })

    # Summary
    print(f"\n{'=' * 60}")
    print("  SUMMARY")
    print(f"{'=' * 60}")

    passed = sum(1 for r in results if r.get('passed'))
    total = len(results)
    avg_time = sum(r.get('time', 0) for r in results) / total

    print(f"\nPassed: {passed}/{total} ({100*passed/total:.0f}%)")
    print(f"Avg response time: {avg_time:.1f}s")

    print("\nResults by persona:")
    for r in results:
        status = "✓" if r.get('passed') else "✗"
        print(f"  {status} {r['persona']}")

    return results


if __name__ == "__main__":
    run_test_queries()
