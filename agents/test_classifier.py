"""Test script for PARA Classification Agent.

Run this to verify the classifier works before integrating into the API.
"""

from classifier import classify_item, batch_classify_items


def test_single_classification():
    """Test single item classification."""
    print("=" * 60)
    print("Testing PARA Classification Agent")
    print("=" * 60)

    test_cases = [
        {
            "title": "Launch marketing campaign for Q1",
            "description": "Create and execute a comprehensive marketing campaign. Target 10k new users. Deadline: March 31st.",
            "expected": "project"
        },
        {
            "title": "Health and fitness",
            "description": "Maintain regular exercise routine, eat healthy, track weight and vitals.",
            "expected": "area"
        },
        {
            "title": "Python best practices collection",
            "description": "Curated list of Python coding standards, design patterns, and useful libraries.",
            "expected": "resource"
        },
        {
            "title": "Old client website project",
            "description": "Website for ClientCo. Completed in 2023. No longer active.",
            "expected": "archive"
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test['title']}")
        print(f"   Expected: {test['expected']}")

        result = classify_item(test["title"], test["description"])

        print(f"   Classified as: {result['para_type']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reasoning: {result['reasoning']}")
        print(f"   Next actions: {', '.join(result['suggested_next_actions'][:2])}")

        if result.get('estimated_duration_weeks'):
            print(f"   Estimated duration: {result['estimated_duration_weeks']} weeks")

        print(f"   Cost: ${result['usage']['cost_usd']:.6f}")

        # Check if classification matches expectation
        match = "✓" if result['para_type'] == test['expected'] else "✗"
        print(f"   {match} {'CORRECT' if match == '✓' else 'INCORRECT'}")

    print("\n" + "=" * 60)


def test_batch_classification():
    """Test batch classification."""
    print("\nTesting Batch Classification")
    print("=" * 60)

    items = [
        {
            "id": "1",
            "title": "Write quarterly report",
            "description": "Due next Friday"
        },
        {
            "id": "2",
            "title": "Team management",
            "description": "Oversee team of 5 developers"
        },
        {
            "id": "3",
            "title": "JavaScript frameworks comparison",
            "description": "Research notes on React vs Vue vs Svelte"
        }
    ]

    results = batch_classify_items(items)

    for result in results:
        print(f"\n- {result['original_title']}")
        print(f"  Type: {result['classification']['para_type']}")
        print(f"  Confidence: {result['classification']['confidence']:.2f}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # NOTE: Requires ANTHROPIC_API_KEY in .env
    test_single_classification()
    # test_batch_classification()  # Uncomment to test batch processing
